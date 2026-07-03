#!/usr/bin/env python3
"""
check-updates.py — Check if installed skills have updates available.
Called by session-start hook when library-manifest.yaml exists.

Usage:
    python3 scripts/check-updates.py [project_dir]

Output:
    If updates available: brief notification message (1-2 lines).
    If up-to-date: silent (no output).
    Exit 0 always.
"""

import hashlib
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent.resolve()
INDEX_ROOT = SCRIPT_DIR.parent
LIBRARY    = INDEX_ROOT / "library"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def main() -> int:
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    project = project.resolve()

    manifest_file = project / "library-manifest.yaml"
    if not manifest_file.exists():
        return 0

    try:
        with open(manifest_file, encoding="utf-8") as f:
            manifest = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return 0

    entries = manifest.get("entries", [])
    if not entries:
        return 0

    updates_available: list[str] = []

    for entry in entries:
        skill_id     = entry.get("id")
        stored_hash  = entry.get("checksum")
        entry_type   = entry.get("type", "skill")

        if not skill_id or not stored_hash:
            continue

        # Find source file in library
        if entry_type == "skill":
            src_file = LIBRARY / "skills" / skill_id / "SKILL.md"
        else:
            src_file = LIBRARY / "agents" / f"{skill_id}.md"

        if not src_file.exists():
            continue  # Skill removed from library — silently skip

        current_hash = sha256_file(src_file)
        if current_hash != stored_hash:
            updates_available.append(skill_id)

    if updates_available:
        n = len(updates_available)
        print(f"[Agent Hub] {n} skill update{'s' if n > 1 else ''} available: "
              f"{', '.join(updates_available[:3])}{'...' if n > 3 else ''}")
        print(f"Run: /librarian update")

    return 0


if __name__ == "__main__":
    sys.exit(main())
