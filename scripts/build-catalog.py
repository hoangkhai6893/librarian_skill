#!/usr/bin/env python3
"""
Agent Hub — build-catalog.py
Scan library/ and build catalog.json with enriched metadata.

Usage:
    python3 scripts/build-catalog.py
    python3 scripts/build-catalog.py --verbose

Output:
    library/catalog.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent.resolve()
INDEX_ROOT   = SCRIPT_DIR.parent
LIBRARY      = INDEX_ROOT / "library"
CATALOG_FILE = LIBRARY / "catalog.json"
KEYWORDS_FILE = SCRIPT_DIR / "domain-keywords.json"

# ── Load keyword tables ───────────────────────────────────────────────────────

def load_keywords() -> dict:
    if not KEYWORDS_FILE.exists():
        print(f"[WARN] domain-keywords.json not found at {KEYWORDS_FILE}")
        return {"DOMAIN_KEYWORDS": {}, "TECH_KEYWORDS": {}, "PHASE_KEYWORDS": {}}
    with open(KEYWORDS_FILE, encoding="utf-8") as f:
        return json.load(f)


KW = load_keywords()
DOMAIN_KEYWORDS = KW.get("DOMAIN_KEYWORDS", {})
TECH_KEYWORDS   = KW.get("TECH_KEYWORDS", {})
PHASE_KEYWORDS  = KW.get("PHASE_KEYWORDS", {})

# ── Frontmatter parser ────────────────────────────────────────────────────────

def parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                fm = {}
            return fm, parts[2]
    return {}, text


# ── Metadata inference ────────────────────────────────────────────────────────

def _match_categories(primary: str, secondary: str, keyword_table: dict, top_n: int = 4) -> list[str]:
    """
    Score each category by keyword hits, preferring the curated primary text
    (name+description) over the noisier secondary text (body — full of code
    examples that mention unrelated languages/tools in passing). A category
    only counts from secondary text alone if it has >= 2 distinct keyword hits,
    to avoid a single incidental mention tagging the whole entry.
    """
    scored: list[tuple[str, int]] = []
    for category, keywords in keyword_table.items():
        primary_hits = sum(1 for kw in keywords if kw in primary)
        if primary_hits:
            scored.append((category, 100 + primary_hits))
            continue
        secondary_hits = sum(1 for kw in keywords if kw in secondary)
        if secondary_hits >= 2:
            scored.append((category, secondary_hits))
    scored.sort(key=lambda pair: -pair[1])
    return [category for category, _ in scored[:top_n]]


def infer_from_text(name: str, description: str, body: str) -> dict:
    """Infer domains, technologies, phases — weighted toward name+description."""
    primary   = f"{name} {description}".lower()
    secondary = body.lower()[:3000]  # cap at 3000 chars

    return {
        "domains":      _match_categories(primary, secondary, DOMAIN_KEYWORDS),
        "technologies": _match_categories(primary, secondary, TECH_KEYWORDS),
        "phases":       _match_categories(primary, secondary, PHASE_KEYWORDS),
    }


def infer_cost(path: Path) -> str:
    size = path.stat().st_size
    if size < 5_000:
        return "light"
    if size < 20_000:
        return "medium"
    return "heavy"


def infer_stability(fm: dict, body: str, source_stability: str = "stable") -> str:
    text = body.lower()
    for hint in ["experimental", "wip", "draft", "prototype", "poc"]:
        if hint in text:
            return "experimental"
    for hint in ["beta", "evolving", "preview"]:
        if hint in text:
            return "beta"
    return source_stability


def infer_complexity(fm: dict, body: str) -> str:
    text = body.lower()
    if any(w in text for w in ["advanced", "expert", "complex", "sophisticated"]):
        return "advanced"
    if any(w in text for w in ["simple", "beginner", "basic", "introductory"]):
        return "beginner"
    return "intermediate"


def infer_usage_pattern(fm: dict, name: str, body: str, entry_type: str) -> str:
    preamble_tier = fm.get("preamble-tier") or fm.get("preambleTier")
    if preamble_tier:
        return "always-on"
    name_lower = name.lower()
    body_lower = body.lower()
    if any(w in name_lower for w in ["plan", "brainstorm", "design", "architect", "writing"]):
        return "before-implementation"
    if any(w in name_lower for w in ["review", "verify", "check", "test", "qa"]):
        return "after-implementation"
    if "session start" in body_lower or "session hook" in body_lower:
        return "session-hook"
    if entry_type == "command":
        return "on-demand"
    return "during-implementation"


def extract_relevance_keywords(name: str, description: str, body: str,
                                 domains: list, technologies: list, phases: list) -> list:
    """
    Extract up to 60 relevance keywords, restricted to the controlled
    domain/tech/phase vocabularies (not free text from the body — that pulled
    in code-example tokens like "now"/"get"/"file1" that add noise, not signal).
    """
    words: set[str] = set()

    # Add matched keyword tokens from domain/tech/phase tables
    combined = f"{name} {description} {body[:2000]}".lower()
    for cat_dict in (DOMAIN_KEYWORDS, TECH_KEYWORDS, PHASE_KEYWORDS):
        for _, kw_list in cat_dict.items():
            for kw in kw_list:
                if kw in combined:
                    words.update(kw.split())

    # Add domain/tech/phase labels themselves
    words.update(domains)
    words.update(technologies)
    words.update(phases)

    return sorted(words)[:60]


# ── Source stability lookup ───────────────────────────────────────────────────

_HARDCODED_STABILITY = {
    "superpowers": "stable",
    "everything-claude-code": "stable",
    "gstack": "stable",
    "get-shit-done": "stable",
    "learn-claude-code": "stable",
    "openspec": "experimental",
}


def _load_source_stability() -> dict:
    """Merge hardcoded stability with values from skills-pool-registry.yaml."""
    stability = dict(_HARDCODED_STABILITY)
    registry_path = (SCRIPT_DIR.parent / "data" / "skills-pool-registry.yaml").resolve()
    if not registry_path.exists():
        return stability
    try:
        with open(registry_path, encoding="utf-8") as f:
            registry = yaml.safe_load(f) or {}
        for repo_name, entry in registry.items():
            if repo_name not in stability and isinstance(entry, dict):
                stability[repo_name] = entry.get("stability", "stable")
    except Exception:
        pass
    return stability


SOURCE_STABILITY = _load_source_stability()


# ── Scan library ─────────────────────────────────────────────────────────────

def scan_skills() -> list[dict]:
    """Scan library/skills/ and return list of entry dicts."""
    skills_dir = LIBRARY / "skills"
    if not skills_dir.exists():
        return []

    entries = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            print(f"  [WARN] {skill_dir.name}/ has no SKILL.md — skipping")
            continue

        entry_id = skill_dir.name
        entry = build_entry(entry_id, "skill", skill_file)
        entries.append(entry)

    return entries


def scan_agents() -> list[dict]:
    """Scan library/agents/ and return list of entry dicts."""
    agents_dir = LIBRARY / "agents"
    if not agents_dir.exists():
        return []

    entries = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        entry_id = agent_file.stem
        entry = build_entry(entry_id, "agent", agent_file)
        entries.append(entry)

    return entries


def build_entry(entry_id: str, entry_type: str, md_file: Path) -> dict:
    """Build a single catalog entry from a .md file."""
    fm, body = parse_frontmatter(md_file)

    name        = fm.get("name") or entry_id
    description = str(fm.get("description") or "").strip()
    tools       = fm.get("tools") or []
    model       = fm.get("model") or None

    # Load provenance
    prov_file = LIBRARY / "provenance" / f"{entry_id}.yaml"
    prov: dict = {}
    if prov_file.exists():
        try:
            with open(prov_file, encoding="utf-8") as f:
                prov = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            pass

    source         = prov.get("source_project", "unknown")
    source_path    = prov.get("source_path", md_file.relative_to(LIBRARY).as_posix())
    imported_at    = prov.get("imported_at", "")
    library_version = prov.get("library_version", "1.0")

    # Load enrichment (optional curator overrides)
    enrich_file = LIBRARY / "enrichment" / f"{entry_id}.yaml"
    enrich: dict = {}
    if enrich_file.exists():
        try:
            with open(enrich_file, encoding="utf-8") as f:
                enrich = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            pass

    # Infer metadata from content
    inferred       = infer_from_text(name, description, body)
    src_stability  = SOURCE_STABILITY.get(source, "stable")

    domains        = enrich.get("domains") or inferred["domains"] or ["workflow"]
    technologies   = enrich.get("technologies") or inferred["technologies"]
    phases         = enrich.get("phases") or inferred["phases"] or ["development"]
    cost           = infer_cost(md_file)
    stability      = infer_stability(fm, body, src_stability)
    complexity     = enrich.get("complexity") or infer_complexity(fm, body)
    usage_pattern  = enrich.get("usage_pattern") or infer_usage_pattern(fm, name, body, entry_type)
    project_types  = enrich.get("project_types") or ["any"]
    use_with       = enrich.get("use_with") or []
    conflicts_with = enrich.get("conflicts_with") or []
    curator_notes  = enrich.get("curator_notes") or ""

    keywords = extract_relevance_keywords(name, description, body, domains, technologies, phases)

    # Relative path within library (for publish-to-project.py)
    rel_path = md_file.relative_to(LIBRARY).as_posix()

    entry = {
        "id":              entry_id,
        "name":            name,
        "type":            entry_type,
        "source":          source,
        "source_path":     source_path,
        "library_version": library_version,
        "imported_at":     imported_at,
        "description":     description,
        "domains":         domains,
        "technologies":    technologies,
        "phases":          phases,
        "cost":            cost,
        "stability":       stability,
        "complexity":      complexity,
        "usage_pattern":   usage_pattern,
        "project_types":   project_types,
        "use_with":        use_with,
        "conflicts_with":  conflicts_with,
        "curator_notes":   curator_notes,
        "path":            rel_path,
        "keywords":        keywords,
    }

    # Agent-specific fields
    if entry_type == "agent":
        if tools:
            entry["tools"] = tools
        if model:
            entry["model"] = model

    return entry


# ── Load collections and stacks ───────────────────────────────────────────────

def load_collections() -> list[dict]:
    coll_dir = LIBRARY / "collections"
    if not coll_dir.exists():
        return []
    collections = []
    for f in sorted(coll_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data and isinstance(data, dict):
                collections.append(data)
        except yaml.YAMLError as e:
            print(f"  [WARN] Could not parse collection {f.name}: {e}")
    return collections


def load_stacks() -> list[dict]:
    stacks_dir = LIBRARY / "stacks"
    if not stacks_dir.exists():
        return []
    stacks = []
    for f in sorted(stacks_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if data and isinstance(data, dict):
                stacks.append(data)
        except yaml.YAMLError as e:
            print(f"  [WARN] Could not parse stack {f.name}: {e}")
    return stacks


# ── Build catalog ─────────────────────────────────────────────────────────────

def build_catalog(verbose: bool = False) -> dict:
    if not LIBRARY.exists():
        print(f"[ERROR] library/ directory not found: {LIBRARY}")
        sys.exit(2)

    print("Scanning library/skills/ ...")
    skill_entries = scan_skills()
    print(f"  Found {len(skill_entries)} skills")

    print("Scanning library/agents/ ...")
    agent_entries = scan_agents()
    print(f"  Found {len(agent_entries)} agents")

    all_entries = skill_entries + agent_entries

    # Check for duplicate IDs
    seen_ids: dict[str, int] = {}
    deduplicated = []
    for entry in all_entries:
        eid = entry["id"]
        if eid in seen_ids:
            seen_ids[eid] += 1
            new_id = f"{eid}-{seen_ids[eid]}"
            print(f"  [WARN] Duplicate ID '{eid}' — renamed to '{new_id}'")
            entry["id"] = new_id
        else:
            seen_ids[eid] = 1
        deduplicated.append(entry)

    all_entries = deduplicated

    # Load collections and stacks
    print("Loading collections/ ...")
    collections = load_collections()
    print(f"  Found {len(collections)} collections")

    print("Loading stacks/ ...")
    stacks = load_stacks()
    print(f"  Found {len(stacks)} stacks")

    # Build catalog
    catalog = {
        "version":      2,
        "builtAt":      datetime.now(timezone.utc).isoformat(),
        "totalEntries": len(all_entries),
        "entries":      all_entries,
        "collections":  collections,
        "stacks":       stacks,
    }

    # Write to disk
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] catalog.json written → {CATALOG_FILE}")
    print(f"     Entries: {len(all_entries)} "
          f"(skills: {len(skill_entries)}, agents: {len(agent_entries)})")
    print(f"     Collections: {len(collections)}  Stacks: {len(stacks)}")

    return catalog


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Build catalog.json from library/ directory."
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    build_catalog(verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
