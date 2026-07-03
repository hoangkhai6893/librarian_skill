#!/usr/bin/env python3
"""
Agent Hub — validate.py
Validate library integrity: skills, agents, catalog, collections, stacks.

Usage:
    python3 scripts/validate.py
    python3 scripts/validate.py --strict    # treat warnings as errors
    python3 scripts/validate.py --json      # output JSON report

Exit codes:
    0  all checks pass (or only warnings without --strict)
    1  one or more checks FAIL
    2  system error (missing directory or JSON parse failure)
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent.resolve()
INDEX_ROOT   = SCRIPT_DIR.parent
LIBRARY      = INDEX_ROOT / "library"
CATALOG_FILE = LIBRARY / "catalog.json"

# ── Check result dataclass ────────────────────────────────────────────────────

class CheckResult:
    def __init__(self, name: str):
        self.name   = name
        self.status = "pass"   # pass | fail | warn | skip
        self.issues: list[str] = []

    def fail(self, msg: str):
        self.status = "fail"
        self.issues.append(msg)

    def warn(self, msg: str):
        if self.status == "pass":
            self.status = "warn"
        self.issues.append(f"[WARN] {msg}")

    def __str__(self):
        icon = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "-"}[self.status]
        lines = [f"  [{icon}] {self.name}: {self.status.upper()}"]
        for issue in self.issues:
            lines.append(f"      {issue}")
        return "\n".join(lines)


# ── Individual checks ─────────────────────────────────────────────────────────

def check_skill_has_md() -> CheckResult:
    """Every directory in library/skills/ must have SKILL.md."""
    result = CheckResult("SKILL_HAS_MD")
    skills_dir = LIBRARY / "skills"
    if not skills_dir.exists():
        result.fail(f"library/skills/ directory not found")
        return result
    for d in skills_dir.iterdir():
        if d.is_dir() and not (d / "SKILL.md").exists():
            result.fail(f"Missing SKILL.md: {d.name}/")
    return result


def check_skill_has_provenance() -> CheckResult:
    """Every skill should have a provenance.yaml (warn, not fail)."""
    result = CheckResult("SKILL_HAS_PROVENANCE")
    skills_dir = LIBRARY / "skills"
    if not skills_dir.exists():
        result.warn("library/skills/ not found — skipping")
        return result
    prov_dir = LIBRARY / "provenance"
    for d in skills_dir.iterdir():
        if d.is_dir() and (d / "SKILL.md").exists():
            prov_file = prov_dir / f"{d.name}.yaml"
            if not prov_file.exists():
                result.warn(f"Missing provenance.yaml for: {d.name}")
    return result


def check_agent_valid_frontmatter() -> CheckResult:
    """Every agent .md must have valid YAML frontmatter with name + description."""
    result = CheckResult("AGENT_VALID_FRONTMATTER")
    agents_dir = LIBRARY / "agents"
    if not agents_dir.exists():
        result.warn("library/agents/ not found — skipping")
        return result
    for f in agents_dir.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        if not text.startswith("---"):
            result.fail(f"{f.name}: no YAML frontmatter")
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            result.fail(f"{f.name}: malformed frontmatter delimiters")
            continue
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as e:
            result.fail(f"{f.name}: YAML parse error: {e}")
            continue
        if not fm.get("name"):
            result.fail(f"{f.name}: missing 'name' field")
        if not fm.get("description"):
            result.fail(f"{f.name}: missing 'description' field")
    return result


def check_librarian_copies_in_sync() -> CheckResult:
    """`commands/librarian.md` (plugin) and `library/agents/librarian.md` (published
    copy) must expose the same subcommands — see "Two Copies of /librarian" in README."""
    result = CheckResult("LIBRARIAN_COPIES_IN_SYNC")
    cmd_file = INDEX_ROOT / "commands" / "librarian.md"
    lib_file = LIBRARY / "agents" / "librarian.md"
    if not cmd_file.exists() or not lib_file.exists():
        result.warn("One or both librarian.md copies not found — skipping")
        return result

    pattern = r"^###\s+`([a-zA-Z][a-zA-Z0-9_-]*)"
    cmd_subs = set(re.findall(pattern, cmd_file.read_text(encoding="utf-8"), re.MULTILINE))
    lib_subs = set(re.findall(pattern, lib_file.read_text(encoding="utf-8"), re.MULTILINE))

    only_in_cmd = cmd_subs - lib_subs
    only_in_lib = lib_subs - cmd_subs
    if only_in_cmd:
        result.warn(f"commands/librarian.md has subcommands missing from library/agents/librarian.md: {sorted(only_in_cmd)}")
    if only_in_lib:
        result.warn(f"library/agents/librarian.md has subcommands missing from commands/librarian.md: {sorted(only_in_lib)}")
    return result


def check_catalog_exists() -> tuple[CheckResult, dict | None]:
    """catalog.json must exist and be valid JSON."""
    result = CheckResult("CATALOG_EXISTS")
    if not CATALOG_FILE.exists():
        result.fail(f"catalog.json not found at {CATALOG_FILE}")
        return result, None
    try:
        with open(CATALOG_FILE, encoding="utf-8") as f:
            catalog = json.load(f)
        if "entries" not in catalog:
            result.fail("catalog.json missing 'entries' key")
            return result, None
    except json.JSONDecodeError as e:
        result.fail(f"catalog.json JSON parse error: {e}")
        return result, None
    return result, catalog


def check_catalog_complete(catalog: dict) -> CheckResult:
    """Every skill dir and agent file must have an entry in catalog."""
    result = CheckResult("CATALOG_COMPLETE")
    catalog_ids = {e["id"] for e in catalog.get("entries", [])}

    skills_dir = LIBRARY / "skills"
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                if d.name not in catalog_ids:
                    result.fail(f"Skill '{d.name}' not in catalog")

    agents_dir = LIBRARY / "agents"
    if agents_dir.exists():
        for f in agents_dir.glob("*.md"):
            if f.stem not in catalog_ids:
                result.fail(f"Agent '{f.stem}' not in catalog")

    return result


def check_no_duplicate_ids(catalog: dict) -> CheckResult:
    """No duplicate IDs in catalog."""
    result = CheckResult("NO_DUPLICATE_IDS")
    ids = [e["id"] for e in catalog.get("entries", [])]
    seen: dict[str, int] = {}
    for eid in ids:
        seen[eid] = seen.get(eid, 0) + 1
    for eid, count in seen.items():
        if count > 1:
            result.fail(f"Duplicate ID '{eid}' appears {count} times")
    return result


def check_use_with_valid(catalog: dict) -> CheckResult:
    """All use_with references must point to existing catalog IDs."""
    result = CheckResult("USE_WITH_VALID")
    catalog_ids = {e["id"] for e in catalog.get("entries", [])}
    for entry in catalog.get("entries", []):
        eid = entry["id"]
        for ref in entry.get("use_with", []):
            if ref not in catalog_ids:
                result.fail(f"'{eid}'.use_with references unknown ID: '{ref}'")
        for ref in entry.get("conflicts_with", []):
            if ref not in catalog_ids:
                result.fail(f"'{eid}'.conflicts_with references unknown ID: '{ref}'")
    return result


def check_collections_valid(catalog: dict) -> CheckResult:
    """Collections must reference valid catalog IDs and have contiguous sequences."""
    result = CheckResult("COLLECTIONS_VALID")
    coll_dir = LIBRARY / "collections"
    if not coll_dir.exists():
        result.warn("library/collections/ not found — skipping")
        return result

    catalog_ids = {e["id"] for e in catalog.get("entries", [])}

    for f in sorted(coll_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                coll = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            result.fail(f"{f.name}: YAML parse error: {e}")
            continue

        if not coll:
            result.fail(f"{f.name}: empty file")
            continue

        coll_id = coll.get("id", f.stem)

        # Required fields
        for field in ["name", "id", "description", "entries"]:
            if not coll.get(field):
                result.fail(f"{f.name}: missing required field '{field}'")

        entries = coll.get("entries", [])

        # Entry count
        if len(entries) < 2:
            result.fail(f"{coll_id}: must have at least 2 entries (has {len(entries)})")
        if len(entries) > 12:
            result.fail(f"{coll_id}: too many entries {len(entries)} (max 12)")

        # Sequence continuity
        seqs = [e.get("seq") for e in entries if isinstance(e, dict)]
        if seqs:
            expected = list(range(1, len(seqs) + 1))
            if sorted(seqs) != expected:
                result.fail(f"{coll_id}: sequences {sorted(seqs)} not contiguous from 1")

        # ID references
        for entry in entries:
            if isinstance(entry, dict):
                ref_id = entry.get("id")
                if ref_id and ref_id not in catalog_ids:
                    result.fail(f"{coll_id}: references unknown skill ID '{ref_id}'")

    return result


def check_stacks_valid(catalog: dict) -> CheckResult:
    """Stacks must reference valid catalog IDs and meet minimum requirements."""
    result = CheckResult("STACKS_VALID")
    stacks_dir = LIBRARY / "stacks"
    if not stacks_dir.exists():
        result.warn("library/stacks/ not found — skipping")
        return result

    catalog_ids = {e["id"] for e in catalog.get("entries", [])}

    for f in sorted(stacks_dir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                stack = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            result.fail(f"{f.name}: YAML parse error: {e}")
            continue

        if not stack:
            result.fail(f"{f.name}: empty file")
            continue

        stack_id = stack.get("id", f.stem)

        # Required fields
        for field in ["name", "id", "description", "core_skills"]:
            if not stack.get(field):
                result.fail(f"{f.name}: missing required field '{field}'")

        core_skills     = stack.get("core_skills", [])
        workflow_skills = stack.get("workflow_skills", [])

        if len(core_skills) < 3:
            result.fail(f"{stack_id}: core_skills must have >= 3 entries (has {len(core_skills)})")
        if len(workflow_skills) < 2:
            result.fail(f"{stack_id}: workflow_skills must have >= 2 entries (has {len(workflow_skills)})")

        # ID references
        for skill_entry in core_skills + workflow_skills:
            if isinstance(skill_entry, dict):
                ref_id = skill_entry.get("id")
                if ref_id and ref_id not in catalog_ids:
                    result.fail(f"{stack_id}: references unknown skill ID '{ref_id}'")

    return result


# ── Main validator ────────────────────────────────────────────────────────────

def run_validation(strict: bool = False, output_json: bool = False) -> int:
    results: list[CheckResult] = []

    # Check 1: skills have SKILL.md
    results.append(check_skill_has_md())

    # Check 2: skills have provenance.yaml (warn)
    results.append(check_skill_has_provenance())

    # Check 3: agents have valid frontmatter
    results.append(check_agent_valid_frontmatter())

    # Check 3b: the two librarian.md copies expose the same subcommands
    results.append(check_librarian_copies_in_sync())

    # Check 4: catalog.json exists
    cat_result, catalog = check_catalog_exists()
    results.append(cat_result)

    if catalog is None:
        # Can't run catalog-dependent checks
        if output_json:
            print(json.dumps({"status": "error", "results": [r.__dict__ for r in results]}, indent=2))
        else:
            print("Validation Results:")
            for r in results:
                print(r)
            print("\n[ABORT] Cannot continue without valid catalog.json")
        return 2

    # Checks 5-9: catalog-dependent
    results.append(check_catalog_complete(catalog))
    results.append(check_no_duplicate_ids(catalog))
    results.append(check_use_with_valid(catalog))
    results.append(check_collections_valid(catalog))
    results.append(check_stacks_valid(catalog))

    # Tally
    fails  = [r for r in results if r.status == "fail"]
    warns  = [r for r in results if r.status == "warn"]
    passes = [r for r in results if r.status == "pass"]

    if output_json:
        report = {
            "status": "fail" if fails else ("warn" if warns else "pass"),
            "summary": {"pass": len(passes), "warn": len(warns), "fail": len(fails)},
            "results": [
                {"name": r.name, "status": r.status, "issues": r.issues}
                for r in results
            ],
        }
        print(json.dumps(report, indent=2))
    else:
        print("Validation Results:")
        print(f"  library: {LIBRARY}")
        print()
        for r in results:
            print(r)
        print()
        print(f"Summary: {len(passes)} pass  {len(warns)} warn  {len(fails)} fail")

    if fails:
        return 1
    if warns and strict:
        return 1
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Agent Hub library integrity.")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", dest="output_json",
                        help="Output JSON report instead of human-readable text")
    args = parser.parse_args()

    return run_validation(strict=args.strict, output_json=args.output_json)


if __name__ == "__main__":
    sys.exit(main())
