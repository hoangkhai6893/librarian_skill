#!/usr/bin/env python3
"""
Agent Hub — auto-import.py
Orchestrator: scan Skills_Pool/ → detect new/changed projects → import → rebuild catalog.

Usage:
    python3 scripts/auto-import.py                     # scan and import everything new
    python3 scripts/auto-import.py --dry-run           # preview without writing
    python3 scripts/auto-import.py --force             # re-import even if already imported
    python3 scripts/auto-import.py --dir NAME          # target a single repo
    python3 scripts/auto-import.py --no-rebuild        # skip catalog rebuild (faster)
    python3 scripts/auto-import.py --silent            # suppress output (hook mode)

Exit codes:
    0  success (imported or nothing to do)
    1  fatal error
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR    = Path(__file__).parent.resolve()
INDEX_ROOT    = SCRIPT_DIR.parent
HUB_ROOT      = INDEX_ROOT.parent
POOL_DIR      = HUB_ROOT / "Skills_Pool"
LIBRARY       = INDEX_ROOT / "library"
REGISTRY_FILE = INDEX_ROOT / "data" / "skills-pool-registry.yaml"
IMPORT_LOG    = LIBRARY / "import-log.yaml"

# Subdirectories safe to copy alongside SKILL.md
SAFE_COPY_DIRS = {"references", "examples", "docs", "assets", "evals", "prompts"}

# Statuses that auto-import will not touch
SKIP_STATUSES = {"managed-by-sources", "skipped", "ignored"}


# ── Registry I/O ──────────────────────────────────────────────────────────────

def load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {}
    with open(REGISTRY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_registry(registry: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        yaml.dump(registry, f, default_flow_style=False, allow_unicode=True, sort_keys=True)


# ── Import log ────────────────────────────────────────────────────────────────

def append_log(entry: dict) -> None:
    log: list = []
    if IMPORT_LOG.exists():
        with open(IMPORT_LOG, encoding="utf-8") as f:
            log = yaml.safe_load(f) or []
    log.append(entry)
    IMPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(IMPORT_LOG, "w", encoding="utf-8") as f:
        yaml.dump(log, f, default_flow_style=False, allow_unicode=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def get_git_sha(repo_path: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                fm = {}
            return fm, parts[2]
    return {}, text


def generate_frontmatter(skill_name: str, md_file: Path) -> str:
    """
    Generate minimal YAML frontmatter for a raw markdown file (no existing frontmatter).
    Tries to extract name/description from README or first heading.
    """
    # Try README in same directory
    readme = md_file.parent / "README.md"
    description = f"Use when working with {skill_name.replace('-', ' ')}."
    if readme.exists():
        try:
            text = readme.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    description = f"Use when: {line[:200]}"
                    break
        except Exception:
            pass
    else:
        # Try first paragraph in the file itself
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    description = f"Use when: {line[:200]}"
                    break
        except Exception:
            pass

    fm_block = textwrap.dedent(f"""\
        ---
        name: {skill_name}
        description: >
          {description}
        ---
        """)
    return fm_block


def copy_skill_dir(source_dir: Path, target_dir: Path, extra_dirs: list[str], verbose: bool) -> None:
    """
    Copy SKILL.md and safe subdirectories from source_dir to target_dir.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all .md files from the root of the skill directory
    for src_file in source_dir.glob("*.md"):
        dst = target_dir / src_file.name
        shutil.copy2(src_file, dst)
        if verbose:
            print(f"    copied: {src_file.name}")

    # Copy safe subdirectories
    dirs_to_copy = SAFE_COPY_DIRS | set(extra_dirs)
    for dir_name in sorted(dirs_to_copy):
        src_subdir = source_dir / dir_name
        if src_subdir.is_dir():
            dst_subdir = target_dir / dir_name
            if dst_subdir.exists():
                shutil.rmtree(dst_subdir)
            shutil.copytree(src_subdir, dst_subdir)
            if verbose:
                print(f"    copied dir: {dir_name}/")


def write_provenance(lib_id: str, source_name: str, rel_path: str, file_hash: str) -> None:
    prov_file = LIBRARY / "provenance" / f"{lib_id}.yaml"
    now = datetime.now(timezone.utc).isoformat()
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
    prov_file.parent.mkdir(parents=True, exist_ok=True)
    with open(prov_file, "w", encoding="utf-8") as f:
        yaml.dump(prov, f, default_flow_style=False, allow_unicode=True)


def write_enrichment(lib_id: str) -> None:
    # NOTE: intentionally omit complexity/usage_pattern/domains/technologies —
    # build-catalog.py infers those from content; a non-empty stub value here
    # would permanently shadow that inference (`enrich.get(x) or infer_x()`).
    enrich_file = LIBRARY / "enrichment" / f"{lib_id}.yaml"
    if enrich_file.exists():
        return
    enrich = {
        "use_with": [],
        "conflicts_with": [],
        "project_types": ["any"],
        "curator_notes": "",
    }
    enrich_file.parent.mkdir(parents=True, exist_ok=True)
    with open(enrich_file, "w", encoding="utf-8") as f:
        yaml.dump(enrich, f, default_flow_style=False, allow_unicode=True)


# ── Core import for one discovered skill ─────────────────────────────────────

def import_one(
    repo_path: Path,
    skill: dict,             # {"name": ..., "path": ..., "type": ...}
    repo_name: str,
    extra_dirs: list[str],
    dry_run: bool,
    force: bool,
    verbose: bool,
) -> tuple[bool, str]:
    """
    Import a single skill/agent into the library.
    Returns (success, message).
    """
    skill_name  = skill["name"]
    skill_path  = skill["path"]
    entry_type  = skill["type"]
    source_file = repo_path / skill_path

    if not source_file.exists():
        return False, f"source file not found: {source_file}"

    # Normalize library ID
    lib_id = skill_name.lower().replace(" ", "-").replace("_", "-")

    # Parse frontmatter — generate if missing
    fm, body = parse_frontmatter(source_file)
    if not fm.get("name") or not fm.get("description"):
        if dry_run:
            return True, f"[DRY-RUN] would generate frontmatter for '{lib_id}'"
        # Prepend generated frontmatter
        generated = generate_frontmatter(lib_id, source_file)
        original  = source_file.read_text(encoding="utf-8", errors="ignore")
        # Write to a temp location in target (not source)
        temp_content = generated + "\n" + original
    else:
        temp_content = None

    # Determine target paths
    if entry_type == "skill":
        target_dir  = LIBRARY / "skills" / lib_id
        target_file = target_dir / "SKILL.md"
    else:
        target_dir  = LIBRARY / "agents"
        target_file = target_dir / f"{lib_id}.md"

    # Conflict check
    if target_file.exists() and not force:
        existing_hash = sha256(target_file)
        new_hash      = sha256(source_file)
        if existing_hash == new_hash:
            return True, f"already up-to-date: {lib_id}"
        return False, f"conflict: '{lib_id}' exists and differs (use --force)"

    if dry_run:
        return True, f"[DRY-RUN] would import '{repo_name}:{skill_name}' → {target_file}"

    # Copy files
    try:
        if entry_type == "skill":
            source_dir = source_file.parent
            copy_skill_dir(source_dir, target_dir, extra_dirs, verbose)
            # Ensure main file is named SKILL.md
            if not (target_dir / "SKILL.md").exists():
                for md in target_dir.glob("*.md"):
                    md.rename(target_dir / "SKILL.md")
                    break
            # Write generated frontmatter if needed
            if temp_content:
                (target_dir / "SKILL.md").write_text(temp_content, encoding="utf-8")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            if temp_content:
                target_file.write_text(temp_content, encoding="utf-8")
    except OSError as e:
        return False, f"I/O error: {e}"

    # Write provenance + enrichment
    rel_path = source_file.relative_to(repo_path).as_posix()
    file_hash = sha256(source_file)
    write_provenance(lib_id, repo_name, rel_path, file_hash)
    write_enrichment(lib_id)

    return True, f"imported '{lib_id}' ({entry_type}) from '{repo_name}'"


# ── Per-project import ────────────────────────────────────────────────────────

def import_project(
    repo_name: str,
    registry_entry: dict,
    dry_run: bool,
    force: bool,
    verbose: bool,
    silent: bool,
) -> tuple[int, int]:
    """
    Import all skills/agents for one project.
    Returns (imported_count, error_count).
    """
    repo_path   = POOL_DIR / repo_name
    skills      = registry_entry.get("discovered_skills", [])
    extra_dirs  = registry_entry.get("extra_copy_dirs", [])

    imported = 0
    errors   = 0

    for skill in skills:
        ok, msg = import_one(
            repo_path=repo_path,
            skill=skill,
            repo_name=repo_name,
            extra_dirs=extra_dirs,
            dry_run=dry_run,
            force=force,
            verbose=verbose,
        )
        if ok:
            if not silent:
                if "already up-to-date" not in msg:
                    print(f"  [OK] {msg}")
            if "already up-to-date" not in msg and not dry_run:
                imported += 1
        else:
            if not silent:
                print(f"  [ERROR] {msg}", file=sys.stderr)
            errors += 1

    return imported, errors


# ── Main orchestrator ─────────────────────────────────────────────────────────

def auto_import(
    pool_dir: Path = POOL_DIR,
    target_dir: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    no_rebuild: bool = False,
    silent: bool = False,
    verbose: bool = False,
) -> int:
    """
    Full pipeline:
      1. Run detect-skills-pool.py to scan pool and update registry
      2. Load registry and find projects to import
      3. Import each project
      4. Rebuild catalog (unless --no-rebuild)
    Returns exit code.
    """
    # ── Step 1: Scan pool and update registry ────────────────────────────────
    detect_script = SCRIPT_DIR / "detect-skills-pool.py"
    cmd = [sys.executable, str(detect_script), "--update-registry", "--pool-dir", str(pool_dir)]
    if target_dir:
        cmd += ["--dir", target_dir]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if not silent and result.stdout.strip():
            # Only print registry update lines
            for line in result.stdout.splitlines():
                if "[Registry]" in line:
                    print(line)
    except subprocess.TimeoutExpired:
        if not silent:
            print("[WARN] detect-skills-pool.py timed out — using existing registry")

    # ── Step 2: Load registry ────────────────────────────────────────────────
    registry = load_registry()
    if not registry:
        if not silent:
            print("[INFO] Registry is empty — nothing to import")
        return 0

    # ── Step 3: Determine which projects need import ─────────────────────────
    to_process: list[str] = []
    for name, entry in registry.items():
        if target_dir and name != target_dir:
            continue

        status = entry.get("import_status", "pending")

        if status in SKIP_STATUSES:
            continue

        if force:
            to_process.append(name)
        elif status == "pending":
            to_process.append(name)
        elif status == "imported":
            # Check if git sha changed
            repo_path = pool_dir / name
            current_sha = get_git_sha(repo_path)
            stored_sha  = entry.get("last_git_sha", "")
            if current_sha and stored_sha and current_sha != stored_sha:
                to_process.append(name)

    if not to_process:
        if not silent:
            print("[INFO] No new or changed projects to import.")
        return 0

    if not silent:
        print(f"[auto-import] Processing {len(to_process)} project(s): {to_process}")

    # ── Step 4: Import each project ──────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    total_imported = 0
    total_errors   = 0
    log_entry: dict = {
        "timestamp": now,
        "dry_run": dry_run,
        "projects": [],
    }

    for name in to_process:
        entry = registry[name]
        if not silent:
            print(f"\n→ {name}  [{entry.get('detected_pattern', '?')}]")

        imported, errors = import_project(
            repo_name=name,
            registry_entry=entry,
            dry_run=dry_run,
            force=force,
            verbose=verbose,
            silent=silent,
        )
        total_imported += imported
        total_errors   += errors

        log_entry["projects"].append({
            "name": name,
            "imported": imported,
            "errors": errors,
        })

        # Update registry entry status
        if not dry_run:
            registry[name]["import_status"] = "imported" if errors == 0 else "error"
            registry[name]["last_git_sha"]  = get_git_sha(pool_dir / name)

    # ── Step 5: Save registry + write log ────────────────────────────────────
    if not dry_run:
        save_registry(registry)
        log_entry["total_imported"] = total_imported
        log_entry["total_errors"]   = total_errors
        append_log(log_entry)

    # ── Step 6: Rebuild catalog ───────────────────────────────────────────────
    if not dry_run and not no_rebuild and total_imported > 0:
        if not silent:
            print("\n[auto-import] Rebuilding catalog.json ...")
        build_script = SCRIPT_DIR / "build-catalog.py"
        try:
            result = subprocess.run(
                [sys.executable, str(build_script)],
                capture_output=not verbose,
                text=True,
                timeout=60,
            )
            if not silent:
                if result.returncode == 0:
                    # Print only the final summary line
                    for line in (result.stdout or "").splitlines():
                        if "[OK]" in line or "Entries:" in line:
                            print(f"  {line.strip()}")
                else:
                    print(f"  [WARN] catalog rebuild failed: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            if not silent:
                print("  [WARN] catalog rebuild timed out")

    # ── Summary ───────────────────────────────────────────────────────────────
    if not silent:
        print(f"\n[auto-import] Done — {total_imported} imported, {total_errors} errors")

    return 0 if total_errors == 0 else 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-import skills/agents from Skills_Pool/ into the library."
    )
    parser.add_argument("--pool-dir", type=Path, default=POOL_DIR,
                        help=f"Skills_Pool directory (default: {POOL_DIR})")
    parser.add_argument("--dir", metavar="NAME",
                        help="Target a single repo by directory name")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing any files")
    parser.add_argument("--force", action="store_true",
                        help="Re-import even if already imported")
    parser.add_argument("--no-rebuild", action="store_true",
                        help="Skip catalog.json rebuild after import")
    parser.add_argument("--silent", action="store_true",
                        help="Suppress output (for hook mode)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show each file copied")
    args = parser.parse_args()

    return auto_import(
        pool_dir=args.pool_dir,
        target_dir=args.dir,
        dry_run=args.dry_run,
        force=args.force,
        no_rebuild=args.no_rebuild,
        silent=args.silent,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
