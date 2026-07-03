#!/usr/bin/env python3
"""
Agent Hub — publish-to-project.py
Copy skills/agents from the curated library into a target project.

Usage:
    python3 scripts/publish-to-project.py --project /path/to/project --stack ros2-robotics
    python3 scripts/publish-to-project.py --project . --skills systematic-debugging brainstorming
    python3 scripts/publish-to-project.py --project . --collection tdd-first
    python3 scripts/publish-to-project.py --project . --stack web-fullstack-typescript --dry-run
    python3 scripts/publish-to-project.py --project . --stack web-fullstack-typescript --platform github-copilot
    python3 scripts/publish-to-project.py --project . --stack web-fullstack-typescript --platform opencode

Options:
    --project PATH      Target project directory (default: cwd)
    --skills ID...      Specific skill/agent IDs to publish (space-separated)
    --stack ID          Publish all skills from a stack
    --collection ID     Publish all skills from a collection
    --platform          claude-code|opencode|github-copilot  (default: claude-code)
    --dry-run           Preview without copying
    --force             Overwrite if already exists (ignores hash conflict)
    --no-librarian      Skip publishing Librarian agent
    --no-manifest       Skip creating/updating library-manifest.yaml

Exit codes:
    0  success
    1  skill/agent conflict (use --force)
    2  stack/collection not found
    3  skill/agent not found in library
    4  conflict with existing installed skills
    5  I/O error
"""

import argparse
import fcntl
import hashlib
import json
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent.resolve()
INDEX_ROOT   = SCRIPT_DIR.parent
LIBRARY      = INDEX_ROOT / "library"
CATALOG_FILE = LIBRARY / "catalog.json"

# ── Platform target directories ───────────────────────────────────────────────

PLATFORM_DIRS = {
    "claude-code": {
        "skills": ".claude/skills",
        "agents": ".claude/commands",   # agents become slash commands in CC
        "lock_dir": ".claude",
    },
    "opencode": {
        "skills": ".opencode/skills",
        "agents": ".opencode/agents",
        "lock_dir": ".opencode",
    },
    "github-copilot": {
        # Skills → .github/copilot/{id}.prompt.md  (invokable as /{id} in Copilot Chat)
        # Agents → .vscode/{id}.agent.md
        "skills": ".github/copilot",
        "agents": ".vscode",
        "lock_dir": ".github",
    },
}

# ── File locking ──────────────────────────────────────────────────────────────

@contextmanager
def project_lock(project: Path, platform: str = "claude-code"):
    """
    Acquire an exclusive lock on a project directory before publishing.
    Prevents concurrent publish runs from corrupting library-manifest.yaml.
    Raises RuntimeError if another publish is already in progress.
    """
    lock_dir = PLATFORM_DIRS.get(platform, PLATFORM_DIRS["claude-code"]).get("lock_dir", ".claude")
    lock_file = project / lock_dir / ".publish.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "w", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"[ERROR] Another publish is already running for: {project}")
            print(f"        If this is stale, remove: {lock_file}")
            sys.exit(1)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def sha256_content(content: str) -> str:
    h = hashlib.sha256()
    h.update(content.encode("utf-8"))
    return "sha256:" + h.hexdigest()


# ── GitHub Copilot format conversion ─────────────────────────────────────────

def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body)."""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                fm = {}
            return fm, parts[2].lstrip("\n")
    return {}, raw


def convert_for_copilot(src_file: Path, skill_id: str, entry: dict, entry_type: str) -> str:
    """Convert a SKILL.md or agent .md to GitHub Copilot format.

    Skills  → .prompt.md  (mode: ask — invokable as /{id} in Copilot Chat)
    Agents  → .agent.md   (mode: agent with tools)
    """
    raw = src_file.read_text(encoding="utf-8")
    existing_fm, body = _parse_frontmatter(raw)

    description = entry.get("description") or existing_fm.get("description", "")

    if entry_type == "skill":
        fm: dict = {"mode": "ask", "description": description}
        fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True).rstrip()
        return f"---\n{fm_str}\n---\n\n{body}"
    else:
        # Agent: keep model/tools if present
        fm_agent: dict = {"description": description}
        if "model" in existing_fm:
            fm_agent["model"] = existing_fm["model"]
        if "tools" in existing_fm:
            fm_agent["tools"] = existing_fm["tools"]
        fm_str = yaml.dump(fm_agent, default_flow_style=False, allow_unicode=True).rstrip()
        return f"---\n{fm_str}\n---\n\n{body}"


def load_catalog() -> dict:
    if not CATALOG_FILE.exists():
        print(f"[ERROR] catalog.json not found. Run: python3 scripts/build-catalog.py")
        sys.exit(2)
    with open(CATALOG_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_manifest(project: Path) -> dict:
    manifest_file = project / "library-manifest.yaml"
    if not manifest_file.exists():
        return {}
    try:
        with open(manifest_file, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        print(f"[WARN] Could not parse library-manifest.yaml — treating as empty")
        return {}


def save_manifest(project: Path, manifest: dict) -> None:
    manifest_file = project / "library-manifest.yaml"
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_file, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)


# ── Resolve skill lists from stack/collection ─────────────────────────────────

def resolve_stack(stack_id: str, catalog: dict) -> list[str]:
    """Return ordered list of skill IDs from a stack."""
    for stack in catalog.get("stacks", []):
        if stack.get("id") == stack_id:
            ids: list[str] = []
            for s in stack.get("core_skills", []):
                if isinstance(s, dict) and s.get("id"):
                    ids.append(s["id"])
            for s in stack.get("workflow_skills", []):
                if isinstance(s, dict) and s.get("id"):
                    ids.append(s["id"])
            return ids
    print(f"[ERROR] Stack '{stack_id}' not found in catalog. Available stacks:")
    for s in catalog.get("stacks", []):
        print(f"  - {s.get('id', '?')}")
    sys.exit(2)


def resolve_collection(coll_id: str, catalog: dict) -> list[str]:
    """Return ordered list of skill IDs from a collection (sorted by seq)."""
    for coll in catalog.get("collections", []):
        if coll.get("id") == coll_id:
            entries = coll.get("entries", [])
            sorted_entries = sorted(entries, key=lambda e: e.get("seq", 999) if isinstance(e, dict) else 999)
            return [e["id"] for e in sorted_entries if isinstance(e, dict) and e.get("id")]
    print(f"[ERROR] Collection '{coll_id}' not found. Available:")
    for c in catalog.get("collections", []):
        print(f"  - {c.get('id', '?')}")
    sys.exit(2)


def find_in_catalog(skill_id: str, catalog: dict) -> dict | None:
    """Find catalog entry by ID."""
    for entry in catalog.get("entries", []):
        if entry["id"] == skill_id:
            return entry
    return None


# ── Publish single entry ──────────────────────────────────────────────────────

class PublishResult:
    def __init__(self, skill_id: str, status: str, message: str = ""):
        self.skill_id = skill_id
        self.status   = status    # created | updated | skipped | conflict | not_found
        self.message  = message


def publish_one(
    skill_id: str,
    catalog: dict,
    project: Path,
    platform: str,
    force: bool,
    dry_run: bool,
) -> PublishResult:
    entry = find_in_catalog(skill_id, catalog)
    if not entry:
        return PublishResult(skill_id, "not_found", f"'{skill_id}' not in catalog")

    entry_type = entry["type"]
    rel_path   = entry["path"]
    src_file   = LIBRARY / rel_path

    if not src_file.exists():
        return PublishResult(skill_id, "not_found", f"Source file not found: {src_file}")

    # Determine target path and content based on platform
    plat_dirs = PLATFORM_DIRS.get(platform, PLATFORM_DIRS["claude-code"])

    if platform == "github-copilot":
        converted_content = convert_for_copilot(src_file, skill_id, entry, entry_type)
        src_hash = sha256_content(converted_content)
        if entry_type == "skill":
            target_dir  = project / plat_dirs["skills"]
            target_file = target_dir / f"{skill_id}.prompt.md"
        else:
            target_dir  = project / plat_dirs["agents"]
            target_file = target_dir / f"{skill_id}.agent.md"
    else:
        converted_content = None
        src_hash = sha256_file(src_file)
        if entry_type == "skill":
            target_dir  = project / plat_dirs["skills"] / skill_id
            target_file = target_dir / src_file.name
        else:
            target_dir  = project / plat_dirs["agents"]
            target_file = target_dir / src_file.name

    # Check existing
    if target_file.exists():
        existing_hash = sha256_file(target_file)
        if existing_hash == src_hash:
            return PublishResult(skill_id, "skipped", "Up to date")
        if not force:
            return PublishResult(
                skill_id, "conflict",
                f"File exists with different content. Use --force to overwrite."
            )
        status = "updated"
    else:
        status = "created"

    if dry_run:
        return PublishResult(skill_id, f"[dry-run] {status}", str(target_file))

    # Write files
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        if converted_content is not None:
            # GitHub Copilot — write converted content
            target_file.write_text(converted_content, encoding="utf-8")
        elif entry_type == "skill" and src_file.parent.is_dir():
            # Copy all .md files in skill directory
            for md_file in src_file.parent.glob("*.md"):
                shutil.copy2(md_file, target_dir / md_file.name)
        else:
            shutil.copy2(src_file, target_file)
    except OSError as e:
        return PublishResult(skill_id, "error", str(e))

    # Build manifest entry
    prov_file = LIBRARY / "provenance" / f"{skill_id}.yaml"
    prov: dict = {}
    if prov_file.exists():
        try:
            with open(prov_file, encoding="utf-8") as f:
                prov = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            pass

    enrich_file = LIBRARY / "enrichment" / f"{skill_id}.yaml"
    enrich: dict = {}
    if enrich_file.exists():
        try:
            with open(enrich_file, encoding="utf-8") as f:
                enrich = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            pass

    manifest_entry = {
        "id":            skill_id,
        "type":          entry_type,
        "from":          entry.get("source", "unknown"),
        "published_at":  datetime.now(timezone.utc).isoformat(),
        "version":       prov.get("library_version", "1.0"),
        "checksum":      src_hash,
        "use_with":      enrich.get("use_with", []),
        "conflicts_with": enrich.get("conflicts_with", []),
        "usage_pattern": enrich.get("usage_pattern", "standalone"),
    }

    # Attach result for manifest update
    result = PublishResult(skill_id, status, str(target_file))
    result._manifest_entry = manifest_entry  # type: ignore[attr-defined]
    return result


# ── Librarian agent publish ───────────────────────────────────────────────────

def publish_librarian(project: Path, platform: str, force: bool, dry_run: bool) -> None:
    librarian_src = LIBRARY / "agents" / "librarian.md"
    if not librarian_src.exists():
        print("  [SKIP] Librarian agent not found in library")
        return

    plat_dirs = PLATFORM_DIRS.get(platform, PLATFORM_DIRS["claude-code"])

    if platform == "github-copilot":
        librarian_entry = {"name": "Librarian", "description": "AI Librarian for Agent Hub — discover, recommend, and publish skills to your project."}
        converted = convert_for_copilot(librarian_src, "librarian", librarian_entry, "agent")
        src_hash = sha256_content(converted)
        target_dir  = project / plat_dirs["agents"]
        target_file = target_dir / "librarian.agent.md"
    else:
        converted = None
        src_hash = sha256_file(librarian_src)
        target_dir  = project / plat_dirs["agents"]
        target_file = target_dir / "librarian.md"

    if target_file.exists() and sha256_file(target_file) == src_hash:
        print("  [SKIP] Librarian already up to date")
        return
    if dry_run:
        print(f"  [dry-run] Would publish Librarian → {target_file}")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    if converted is not None:
        target_file.write_text(converted, encoding="utf-8")
    else:
        shutil.copy2(librarian_src, target_file)
    print(f"  [OK] Librarian published → {target_file}")


# ── Main publish flow ─────────────────────────────────────────────────────────

def publish(
    project: Path,
    skill_ids: list[str],
    stack_id: str | None,
    collection_id: str | None,
    platform: str,
    force: bool,
    dry_run: bool,
    no_librarian: bool,
    no_manifest: bool,
) -> int:
    if not project.exists():
        print(f"[ERROR] Project directory not found: {project}")
        return 1

    catalog = load_catalog()

    # Resolve final skill list
    ids_to_publish: list[str] = list(skill_ids)
    applied_stack: str | None = None
    applied_collection: str | None = None

    if stack_id:
        resolved = resolve_stack(stack_id, catalog)
        ids_to_publish = resolved + [i for i in ids_to_publish if i not in resolved]
        applied_stack = stack_id

    if collection_id:
        resolved = resolve_collection(collection_id, catalog)
        ids_to_publish = resolved + [i for i in ids_to_publish if i not in resolved]
        applied_collection = collection_id

    if not ids_to_publish:
        print("[ERROR] No skills specified. Use --skills, --stack, or --collection.")
        return 1

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for sid in ids_to_publish:
        if sid not in seen:
            unique_ids.append(sid)
            seen.add(sid)

    print(f"Publishing {len(unique_ids)} entries to: {project}")
    if dry_run:
        print("(DRY-RUN — no files will be written)")
    print()

    # Publish each
    results: list[PublishResult] = []
    manifest_entries: dict[str, dict] = {}

    # Load existing manifest
    existing_manifest = load_manifest(project)
    existing_entries: dict[str, dict] = {
        e["id"]: e for e in existing_manifest.get("entries", [])
    }

    for sid in unique_ids:
        result = publish_one(sid, catalog, project, platform, force, dry_run)
        results.append(result)
        icon = {"created": "+", "updated": "↑", "skipped": "=",
                "conflict": "!", "not_found": "?", "error": "✗"}.get(result.status, "?")
        # Handle dry-run statuses
        clean_status = result.status.replace("[dry-run] ", "")
        icon = {"created": "+", "updated": "↑", "skipped": "=",
                "conflict": "!", "not_found": "?", "error": "✗"}.get(clean_status, "~")
        print(f"  [{icon}] {sid:45} {result.status}")
        if result.message and result.status not in ("skipped",):
            print(f"         {result.message}")

        # Collect manifest data
        if hasattr(result, "_manifest_entry"):
            manifest_entries[sid] = result._manifest_entry  # type: ignore[attr-defined]
        elif result.status == "skipped" and sid in existing_entries:
            manifest_entries[sid] = existing_entries[sid]

    # Publish Librarian agent
    if not no_librarian:
        print()
        publish_librarian(project, platform, force, dry_run)

    # Count results
    created  = sum(1 for r in results if "created" in r.status)
    updated  = sum(1 for r in results if "updated" in r.status)
    skipped  = sum(1 for r in results if r.status == "skipped")
    conflicts = sum(1 for r in results if r.status == "conflict")
    errors   = sum(1 for r in results if r.status in ("not_found", "error"))

    print()
    print(f"Summary: {created} created  {updated} updated  {skipped} skipped  "
          f"{conflicts} conflicts  {errors} errors")

    # Write manifest
    if not no_manifest and not dry_run:
        all_entries = dict(existing_entries)
        all_entries.update(manifest_entries)

        manifest = {
            "schema_version": 1,
            "library_source":  str(INDEX_ROOT / "library"),
            "created_at":      existing_manifest.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            "stack":           applied_stack or existing_manifest.get("stack"),
            "entries":         list(all_entries.values()),
        }
        save_manifest(project, manifest)
        print(f"  Manifest: {project / 'library-manifest.yaml'}")

    if conflicts > 0 or errors > 0:
        return 1
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish skills from Agent Hub library to a target project."
    )
    parser.add_argument("--project", type=Path, default=Path("."),
                        help="Target project directory (default: current directory)")
    parser.add_argument("--skills", nargs="+", default=[],
                        help="Specific skill/agent IDs to publish")
    parser.add_argument("--stack", default=None,
                        help="Stack ID (e.g. ros2-robotics)")
    parser.add_argument("--collection", default=None,
                        help="Collection ID (e.g. tdd-first)")
    parser.add_argument("--platform", choices=["claude-code", "opencode", "github-copilot"],
                        default="claude-code",
                        help="Target platform (default: claude-code)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing files")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing files even if content differs")
    parser.add_argument("--no-librarian", action="store_true",
                        help="Skip publishing Librarian agent")
    parser.add_argument("--no-manifest", action="store_true",
                        help="Skip writing library-manifest.yaml")

    args = parser.parse_args()
    project = args.project.resolve()

    if args.dry_run:
        # Lock not needed for dry-run — no files will be written
        return publish(
            project=project,
            skill_ids=args.skills,
            stack_id=args.stack,
            collection_id=args.collection,
            platform=args.platform,
            force=args.force,
            dry_run=True,
            no_librarian=args.no_librarian,
            no_manifest=args.no_manifest,
        )

    with project_lock(project, args.platform):
        return publish(
            project=project,
            skill_ids=args.skills,
            stack_id=args.stack,
            collection_id=args.collection,
            platform=args.platform,
            force=args.force,
            dry_run=False,
            no_librarian=args.no_librarian,
            no_manifest=args.no_manifest,
        )


if __name__ == "__main__":
    sys.exit(main())
