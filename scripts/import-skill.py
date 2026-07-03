#!/usr/bin/env python3
"""
Agent Hub — import-skill.py
Import a single skill or agent from a source project into the curated library.

Usage:
    python3 scripts/import-skill.py --source superpowers --skill systematic-debugging
    python3 scripts/import-skill.py --source get-shit-done --skill gsd-debugger --type agent
    python3 scripts/import-skill.py --source superpowers --skill brainstorming --dry-run
    python3 scripts/import-skill.py --source superpowers --skill brainstorming --force
    python3 scripts/import-skill.py --source superpowers --skill foo bar baz
    python3 scripts/import-skill.py --source everything-claude-code --all --dry-run
    python3 scripts/import-skill.py --source ~/anywhere/my-project --all --dry-run
        (any unregistered directory is auto-detected + registered on the fly —
        it does not need to live inside Skills_Pool/)

Exit codes:
    0  success
    1  source project not found
    2  skill/agent not found in source
    3  name conflict (use --force to overwrite)
    4  invalid / missing frontmatter
    5  I/O error
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR    = Path(__file__).parent.resolve()
HUB_ROOT      = SCRIPT_DIR.parent.parent          # ~/Agent_Hub
INDEX_ROOT    = SCRIPT_DIR.parent                 # agent-hub-index/
POOL_ROOT     = HUB_ROOT / "Skills_Pool"
LIBRARY       = INDEX_ROOT / "library"
REGISTRY_FILE = INDEX_ROOT / "data" / "skills-pool-registry.yaml"

# Subdirectories safe to copy alongside SKILL.md
SAFE_COPY_DIRS = {"references", "examples", "docs", "assets", "evals", "prompts"}

# ── Source project definitions ────────────────────────────────────────────────

# Base hardcoded sources (original six projects, all under Skills_Pool/)
_BASE_SOURCES = {
    "superpowers": {
        "root": POOL_ROOT / "superpowers",
        "skill_patterns": ["skills/{name}/SKILL.md"],
        "agent_patterns": ["agents/{name}.md"],
        "stability": "stable",
    },
    "everything-claude-code": {
        "root": POOL_ROOT / "everything-claude-code",
        "skill_patterns": ["skills/{name}/SKILL.md"],
        "agent_patterns": ["agents/{name}.md"],
        "stability": "stable",
    },
    "gstack": {
        "root": POOL_ROOT / "gstack",
        "skill_patterns": ["{name}/SKILL.md"],
        "agent_patterns": ["agents/{name}.md"],
        "stability": "stable",
    },
    "get-shit-done": {
        "root": POOL_ROOT / "get-shit-done",
        "skill_patterns": [],
        "agent_patterns": ["agents/{name}.md"],
        "stability": "stable",
    },
    "learn-claude-code": {
        "root": POOL_ROOT / "learn-claude-code",
        "skill_patterns": ["skills/{name}/SKILL.md"],
        "agent_patterns": ["agents/{name}.md"],
        "stability": "stable",
    },
    "openspec": {
        "root": POOL_ROOT / "openspec",
        "skill_patterns": [],
        "agent_patterns": [],
        "stability": "experimental",
    },
}


def _patterns_for_structure(pattern: str) -> tuple[list[str], list[str]]:
    """Map a detect-skills-pool.py `detected_pattern` to (skill_patterns, agent_patterns)."""
    if pattern == "root-skill":
        return ["SKILL.md"], []
    if pattern == "skills-subdir":
        return ["skills/{name}/SKILL.md"], ["agents/{name}.md"]
    if pattern == "root-subdir":
        return ["{name}/SKILL.md"], ["agents/{name}.md"]
    if pattern == "agents-only":
        return [], ["agents/{name}.md"]
    return [], []  # unknown / raw-markdown: not importable via this script


def _load_sources() -> dict:
    """
    Build the SOURCES dict from hardcoded base + Skills_Pool registry.
    Registry entries with import_status != managed-by-sources get auto-generated patterns.
    """
    sources = dict(_BASE_SOURCES)

    if not REGISTRY_FILE.exists():
        return sources

    try:
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            registry = yaml.safe_load(f) or {}
    except Exception:
        return sources

    for repo_name, entry in registry.items():
        if repo_name in sources:
            continue  # already in hardcoded base
        if entry.get("import_status") == "managed-by-sources":
            continue  # controlled elsewhere
        if entry.get("import_status") in ("skipped", "ignored"):
            continue

        pattern = entry.get("detected_pattern", "unknown")
        skill_patterns, agent_patterns = _patterns_for_structure(pattern)
        if not skill_patterns and not agent_patterns:
            continue

        # `source_root` holds the real absolute path when the project lives
        # outside Skills_Pool/ (e.g. a personal folder elsewhere on disk).
        # Older registry entries predate this field — fall back to the
        # Skills_Pool/<name> convention for those.
        root = Path(entry["source_root"]) if entry.get("source_root") else POOL_ROOT / repo_name

        sources[repo_name] = {
            "root": root,
            "skill_patterns": skill_patterns,
            "agent_patterns": agent_patterns,
            "stability": entry.get("stability", "stable"),
        }

    return sources


# Populated at module load time — includes both hardcoded and registry-derived sources
SOURCES = _load_sources()


def resolve_source(source_arg: str) -> str:
    """
    Accept either a known source name or a filesystem path to a not-yet-registered
    skills project ANYWHERE on disk (e.g. a freshly cloned repo, or a personal
    project folder — it does not need to live inside Skills_Pool/). In the
    latter case, profile it with detect-skills-pool.py, persist it to the
    registry with its real absolute path, and make it available for this run
    too — instead of failing with "Unknown source".
    """
    if source_arg in SOURCES:
        return source_arg

    path = Path(source_arg).expanduser()
    if not path.is_dir():
        return source_arg  # not a known name, not a path — let the normal error fire

    path = path.resolve()
    name = path.name
    if name in SOURCES:
        print(f"[import-skill] '{source_arg}' → known source '{name}'")
        return name

    print(f"[import-skill] '{name}' not registered as a source — auto-detecting structure...")
    cmd = [sys.executable, str(SCRIPT_DIR / "detect-skills-pool.py"),
           "--pool-dir", str(path.parent), "--dir", name,
           "--update-registry", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"[WARN] auto-detect failed: {(result.stderr or result.stdout).strip()}")
        return source_arg

    try:
        # --update-registry prints an extra "[Registry] Updated ..." line after
        # the JSON block, so parse only the leading JSON and ignore the rest.
        profiles, _ = json.JSONDecoder().raw_decode(result.stdout.strip())
    except json.JSONDecodeError:
        return source_arg
    if not profiles:
        return source_arg

    pattern = profiles[0].get("pattern", "unknown")
    skill_patterns, agent_patterns = _patterns_for_structure(pattern)
    if not skill_patterns and not agent_patterns:
        print(f"[WARN] '{name}' has no recognizable SKILL.md/agent structure ('{pattern}') "
              f"— cannot import from it.")
        return source_arg

    SOURCES[name] = {
        "root": path,
        "skill_patterns": skill_patterns,
        "agent_patterns": agent_patterns,
        "stability": "stable",
    }
    found = len(profiles[0].get("discovered_skills", []))
    print(f"[import-skill] Auto-registered '{name}' (pattern: {pattern}, {found} found) "
          f"→ saved to data/skills-pool-registry.yaml")
    return name


# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text). Raises ValueError on bad frontmatter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"YAML parse error: {e}")
            body = parts[2]
            return fm, body
    # No frontmatter — return empty dict
    return {}, text


def validate_frontmatter(fm: dict, entry_type: str) -> None:
    """Raise ValueError if required fields are missing."""
    if not fm.get("name"):
        raise ValueError("frontmatter missing 'name' field")
    if not fm.get("description"):
        raise ValueError("frontmatter missing 'description' field")
    if entry_type == "skill":
        desc = str(fm["description"]).strip()
        # Accept "Use when..." pattern (case-insensitive). Warn but don't fail.
        if not desc.lower().startswith("use when"):
            print(f"  [WARN] description does not start with 'Use when' — consider updating")


def find_source_file(src_cfg: dict, name: str, entry_type: str | None) -> tuple[Path, str]:
    """
    Locate source file. Returns (path, detected_type).
    Tries skill patterns first, then agent patterns unless type is specified.
    """
    root = src_cfg["root"]
    patterns_to_try: list[tuple[str, str]] = []

    if entry_type in (None, "skill"):
        for pat in src_cfg["skill_patterns"]:
            patterns_to_try.append((pat, "skill"))
    if entry_type in (None, "agent"):
        for pat in src_cfg["agent_patterns"]:
            patterns_to_try.append((pat, "agent"))

    for pat, detected_type in patterns_to_try:
        candidate = root / pat.format(name=name)
        if candidate.exists():
            return candidate, detected_type

    raise FileNotFoundError(
        f"'{name}' not found in source '{src_cfg['root'].name}'. "
        f"Tried: {[p.format(name=name) for p, _ in patterns_to_try]}"
    )


def get_library_id(name: str) -> str:
    """Normalize name to kebab-case library ID."""
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


def discover_all_skill_names(source_name: str) -> list[str]:
    """Scan a source's folder (via detect-skills-pool.py) and return every skill/agent name found."""
    root = SOURCES[source_name]["root"] if source_name in SOURCES else POOL_ROOT / source_name
    detect_script = SCRIPT_DIR / "detect-skills-pool.py"
    cmd = [sys.executable, str(detect_script), "--pool-dir", str(root.parent),
           "--dir", root.name, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "detect-skills-pool.py failed")
    profiles = json.loads(result.stdout)
    if not profiles:
        raise RuntimeError(f"'{source_name}' not found under {root.parent}")
    return [s["name"] for s in profiles[0].get("discovered_skills", [])]


# ── Core import logic ─────────────────────────────────────────────────────────

def import_entry(
    source_name: str,
    skill_name: str,
    entry_type: str | None,
    dry_run: bool,
    force: bool,
    verbose: bool,
) -> int:
    """
    Returns exit code (0 = success).
    """
    if source_name not in SOURCES:
        print(f"[ERROR] Unknown source '{source_name}'. Available: {list(SOURCES.keys())}")
        return 1

    src_cfg = SOURCES[source_name]
    if not src_cfg["root"].exists():
        print(f"[ERROR] Source directory not found: {src_cfg['root']}")
        return 1

    # 1. Locate source file
    try:
        source_file, detected_type = find_source_file(src_cfg, skill_name, entry_type)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 2

    resolved_type = entry_type or detected_type
    lib_id = get_library_id(skill_name)

    if verbose:
        print(f"  Source file   : {source_file}")
        print(f"  Type          : {resolved_type}")
        print(f"  Library ID    : {lib_id}")

    # 2. Parse & validate frontmatter
    try:
        fm, body = parse_frontmatter(source_file)
        validate_frontmatter(fm, resolved_type)
    except (ValueError, OSError) as e:
        print(f"[ERROR] Frontmatter problem in '{source_file}': {e}")
        return 4

    # 3. Determine target paths
    if resolved_type == "skill":
        # Skills are stored as a directory with SKILL.md
        source_dir   = source_file.parent
        target_dir   = LIBRARY / "skills" / lib_id
        target_file  = target_dir / "SKILL.md"
    else:
        # Agents are stored as a single .md file
        source_dir   = None
        target_dir   = LIBRARY / "agents"
        target_file  = target_dir / f"{lib_id}.md"

    prov_file    = LIBRARY / "provenance" / f"{lib_id}.yaml"
    enrich_file  = LIBRARY / "enrichment" / f"{lib_id}.yaml"

    # 4. Conflict check
    if target_file.exists() and not force:
        print(f"[ERROR] '{lib_id}' already exists in library. Use --force to overwrite.")
        return 3

    # 5. Compute hash
    file_hash = sha256(source_file)

    if dry_run:
        print(f"[DRY-RUN] Would import '{source_name}:{skill_name}' ({resolved_type}) → {target_file}")
        print(f"          Source: {source_file}")
        print(f"          Hash: {file_hash}")
        return 0

    # 6. Copy files
    try:
        if resolved_type == "skill":
            target_dir.mkdir(parents=True, exist_ok=True)
            if source_dir and source_dir.is_dir():
                # Copy all .md files from skill directory root
                for src_file in source_dir.glob("*.md"):
                    dst = target_dir / src_file.name
                    shutil.copy2(src_file, dst)
                    if verbose:
                        print(f"  Copied: {src_file.name} → {dst}")
                # Copy safe subdirectories (references/, evals/, docs/, etc.)
                # Also respect extra_copy_dirs from registry if source name is in registry
                extra_dirs: set[str] = set()
                try:
                    if REGISTRY_FILE.exists():
                        with open(REGISTRY_FILE, encoding="utf-8") as _rf:
                            _reg = yaml.safe_load(_rf) or {}
                        _entry = _reg.get(source_name, {})
                        extra_dirs = set(_entry.get("extra_copy_dirs", []))
                except Exception:
                    pass
                dirs_to_copy = SAFE_COPY_DIRS | extra_dirs
                for dir_name in sorted(dirs_to_copy):
                    src_subdir = source_dir / dir_name
                    if src_subdir.is_dir():
                        dst_subdir = target_dir / dir_name
                        if dst_subdir.exists():
                            shutil.rmtree(dst_subdir)
                        shutil.copytree(src_subdir, dst_subdir)
                        if verbose:
                            print(f"  Copied dir: {dir_name}/ → {dst_subdir}")
                # Normalize main file to SKILL.md if it has another name
                if not (target_dir / "SKILL.md").exists():
                    for md in target_dir.glob("*.md"):
                        md.rename(target_dir / "SKILL.md")
                        break
            else:
                shutil.copy2(source_file, target_file)
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            if verbose:
                print(f"  Copied: {source_file.name} → {target_file}")

    except OSError as e:
        print(f"[ERROR] I/O error copying files: {e}")
        return 5

    # 7. Create provenance.yaml
    now = datetime.now(timezone.utc).isoformat()
    rel_path = source_file.relative_to(src_cfg["root"]).as_posix()

    prov = {
        "source_project": source_name,
        "source_path": rel_path,
        "imported_at": now,
        "imported_by": os.environ.get("USER", "dkhai"),
        "original_hash": file_hash,
        "library_version": "1.0",
        "customized": False,
        "notes": "",
    }

    try:
        prov_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prov_file, "w", encoding="utf-8") as f:
            yaml.dump(prov, f, default_flow_style=False, allow_unicode=True)
    except OSError as e:
        print(f"[ERROR] Could not write provenance.yaml: {e}")
        return 5

    # 8. Create enrichment.yaml (skeleton, for curator to fill in later).
    # NOTE: intentionally omit complexity/usage_pattern/domains/technologies —
    # build-catalog.py infers those from content; a non-empty stub value here
    # would permanently shadow that inference (`enrich.get(x) or infer_x()`).
    if not enrich_file.exists():
        enrich = {
            "use_with": [],
            "conflicts_with": [],
            "project_types": ["any"],
            "curator_notes": "",
        }
        try:
            enrich_file.parent.mkdir(parents=True, exist_ok=True)
            with open(enrich_file, "w", encoding="utf-8") as f:
                yaml.dump(enrich, f, default_flow_style=False, allow_unicode=True)
        except OSError as e:
            print(f"[WARN] Could not write enrichment.yaml: {e}")

    action = "Updated" if target_file.exists() and force else "Imported"
    print(f"[OK] {action} '{lib_id}' ({resolved_type}) from '{source_name}'")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import a skill or agent from a source project into Agent Hub library."
    )
    parser.add_argument("--source", required=True,
                        help="Source project name (e.g. superpowers, everything-claude-code)")
    parser.add_argument("--skill", nargs="+", metavar="SKILL",
                        help="One or more skill/agent names (kebab-case, space-separated)")
    parser.add_argument("--all", action="store_true",
                        help="Import every skill/agent discovered in --source (scans folder names)")
    parser.add_argument("--type", choices=["skill", "agent"], default=None,
                        dest="entry_type",
                        help="Force type. Auto-detected if omitted.")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite if already exists in library")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would happen without writing files")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed output")

    args = parser.parse_args()
    args.source = resolve_source(args.source)

    if args.all and args.skill:
        parser.error("--all and --skill are mutually exclusive")
    if not args.all and not args.skill:
        parser.error("one of --skill or --all is required")

    if args.all:
        try:
            names = discover_all_skill_names(args.source)
        except RuntimeError as e:
            print(f"[ERROR] {e}")
            return 1
        print(f"[import-skill] --all: found {len(names)} skill(s)/agent(s) in '{args.source}'")
    else:
        names = args.skill

    if len(names) == 1:
        return import_entry(
            source_name=args.source,
            skill_name=names[0],
            entry_type=args.entry_type,
            dry_run=args.dry_run,
            force=args.force,
            verbose=args.verbose,
        )

    exit_code = 0
    imported = 0
    for skill_name in names:
        print(f"\n=== {skill_name} ===")
        rc = import_entry(
            source_name=args.source,
            skill_name=skill_name,
            entry_type=args.entry_type,
            dry_run=args.dry_run,
            force=args.force,
            verbose=args.verbose,
        )
        if rc == 0:
            imported += 1
        else:
            exit_code = rc

    print(f"\n[import-skill] Done — {imported}/{len(names)} succeeded")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
