#!/usr/bin/env python3
"""
Agent Hub — diff-skill.py
Compare a library skill/agent's currently-imported content against its
upstream source, so the librarian can decide whether `import-skill.py --force`
is actually needed — instead of blindly force-overwriting every time.

Two ways to point at the source:
  1. Provenance-driven (default) — reads `library/provenance/<id>.yaml` for
     `source_project` + `source_path`, recorded automatically at import time.
  2. Explicit `--source <path>` — scan a folder directly (same folder you'd
     pass to `/librarian import`). Use this when you have a fresher local
     checkout than what provenance points at, or when checking skills that
     aren't in the library yet (they'll be reported as `not_in_library`).

Usage:
    python3 scripts/diff-skill.py --id obsidian-cli
    python3 scripts/diff-skill.py --id obsidian-cli obsidian-markdown
    python3 scripts/diff-skill.py --id obsidian-cli --source $HOME/Downloads/obsidian-skills
    python3 scripts/diff-skill.py --source $HOME/Downloads/obsidian-skills --all
    python3 scripts/diff-skill.py --all                 # audit whole library vs recorded provenance
    python3 scripts/diff-skill.py --id obsidian-cli --json

Per-item status:
    up_to_date        source and library file are byte-identical — nothing to do
    update_available  source changed since import, library copy untouched
                       since import — safe to `import-skill.py --force`
    diverged          library copy no longer matches what was imported (it was
                       hand-edited after import) AND the source also changed —
                       forcing would silently destroy the local edit; needs a
                       human to reconcile, not a blind --force
    not_in_library    found in --source scan but no matching id in the library
                       yet — that's a job for `/librarian import`, not update
    no_provenance     no provenance.yaml for this id and no --source given —
                       can't determine the upstream source at all
    source_not_found  source project/file could not be resolved or read

Exit codes:
    0  every checked item is up_to_date
    2  at least one item is update_available / diverged / not_in_library
    1  usage error, or nothing could be checked at all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR    = Path(__file__).parent.resolve()
INDEX_ROOT    = SCRIPT_DIR.parent
HUB_ROOT      = INDEX_ROOT.parent
POOL_ROOT     = HUB_ROOT / "Skills_Pool"
LIBRARY       = INDEX_ROOT / "library"
REGISTRY_FILE = INDEX_ROOT / "data" / "skills-pool-registry.yaml"
PROVENANCE_DIR = LIBRARY / "provenance"

ACTIONABLE = {"update_available", "diverged", "not_in_library"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def get_library_id(name: str) -> str:
    """Same normalization as import-skill.py — must stay identical."""
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


def library_file_for(lib_id: str) -> Path | None:
    skill_file = LIBRARY / "skills" / lib_id / "SKILL.md"
    if skill_file.exists():
        return skill_file
    agent_file = LIBRARY / "agents" / f"{lib_id}.md"
    if agent_file.exists():
        return agent_file
    return None


def load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {}
    with open(REGISTRY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_source_root(source_project: str) -> Path | None:
    """
    Mirrors import-skill.py's two-tier source resolution WITHOUT duplicating
    its pattern-matching logic: registry `source_root` first (set for any
    project scanned from outside Skills_Pool/), else the Skills_Pool/<name>
    convention (true for the original hardcoded `managed-by-sources` set).
    """
    entry = load_registry().get(source_project, {})
    root = entry.get("source_root")
    if root and Path(root).is_dir():
        return Path(root)
    fallback = POOL_ROOT / source_project
    return fallback if fallback.is_dir() else None


def load_provenance(lib_id: str) -> dict | None:
    prov_file = PROVENANCE_DIR / f"{lib_id}.yaml"
    if not prov_file.exists():
        return None
    with open(prov_file, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def classify(source_hash: str, library_hash: str, original_hash: str | None) -> str:
    if source_hash == library_hash:
        return "up_to_date"
    if original_hash is None or library_hash == original_hash:
        return "update_available"
    return "diverged"


def diff_by_provenance(lib_id: str) -> dict:
    prov = load_provenance(lib_id)
    if prov is None:
        return {"id": lib_id, "status": "no_provenance"}

    source_project = prov.get("source_project", "")
    source_path    = prov.get("source_path", "")
    original_hash  = prov.get("original_hash")

    source_root = resolve_source_root(source_project)
    if source_root is None:
        return {"id": lib_id, "status": "source_not_found", "source_project": source_project}

    source_file = source_root / source_path
    if not source_file.exists():
        return {"id": lib_id, "status": "source_not_found",
                "source_project": source_project, "detail": str(source_file)}

    lib_file = library_file_for(lib_id)
    if lib_file is None:
        return {"id": lib_id, "status": "source_not_found", "detail": "library file missing"}

    source_hash  = sha256(source_file)
    library_hash = sha256(lib_file)
    return {
        "id": lib_id,
        "status": classify(source_hash, library_hash, original_hash),
        "source_project": source_project,
        "source_path": source_path,
        "source_hash": source_hash,
        "library_hash": library_hash,
    }


def scan_source(source: Path) -> list[dict]:
    """Run detect-skills-pool.py --json on an explicit folder and return its
    discovered_skills list (name/path/type), reusing the one real scanner
    instead of re-implementing pattern detection here."""
    cmd = [sys.executable, str(SCRIPT_DIR / "detect-skills-pool.py"),
           "--pool-dir", str(source.parent), "--dir", source.name, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return []
    profiles = json.loads(result.stdout)
    return profiles[0]["discovered_skills"] if profiles else []


def diff_by_source(source: Path, wanted_ids: set[str] | None) -> list[dict]:
    results = []
    for entry in scan_source(source):
        lib_id = get_library_id(entry["name"])
        if wanted_ids is not None and lib_id not in wanted_ids:
            continue

        lib_file = library_file_for(lib_id)
        if lib_file is None:
            results.append({"id": lib_id, "status": "not_in_library"})
            continue

        source_file = source / entry["path"]
        source_hash = sha256(source_file)
        library_hash = sha256(lib_file)
        prov = load_provenance(lib_id) or {}
        results.append({
            "id": lib_id,
            "status": classify(source_hash, library_hash, prov.get("original_hash")),
            "source_project": source.name,
            "source_path": entry["path"],
            "source_hash": source_hash,
            "library_hash": library_hash,
        })
    return results


def all_provenance_ids() -> list[str]:
    if not PROVENANCE_DIR.is_dir():
        return []
    return sorted(p.stem for p in PROVENANCE_DIR.glob("*.yaml"))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare library skills/agents against their upstream source."
    )
    parser.add_argument("--id", nargs="+", metavar="LIB_ID",
                        help="Library id(s) to check (as under library/skills/ or library/agents/)")
    parser.add_argument("--source", type=Path, default=None,
                        help="Explicit source folder to compare against (overrides provenance)")
    parser.add_argument("--all", action="store_true",
                        help="Check every id with provenance (or every id found in --source)")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if not args.id and not args.all:
        parser.error("one of --id or --all is required")

    if args.source:
        source = args.source.expanduser().resolve()
        if not source.is_dir():
            print(f"[ERROR] Source directory not found: {source}", file=sys.stderr)
            return 1
        wanted = set(args.id) if args.id else None
        results = diff_by_source(source, wanted)
        if not results:
            print(f"[ERROR] No skills/agents discovered in {source}", file=sys.stderr)
            return 1
    else:
        ids = args.id if args.id else all_provenance_ids()
        if not ids:
            print("[ERROR] No provenance records found — pass --source explicitly", file=sys.stderr)
            return 1
        results = [diff_by_provenance(i) for i in ids]

    if args.as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"  {r['id']:<30} {r['status']}")
            if r["status"] in ("update_available", "diverged"):
                print(f"      source : {r.get('source_hash', '')}")
                print(f"      library: {r.get('library_hash', '')}")
            if r["status"] == "source_not_found" and r.get("detail"):
                print(f"      {r['detail']}")

    if any(r["status"] in ACTIONABLE for r in results):
        return 2
    if all(r["status"] in ("no_provenance", "source_not_found") for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
