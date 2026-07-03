#!/usr/bin/env python3
"""
Agent Hub — detect-skills-pool.py
Scan Skills_Pool/ and detect skill/agent structure in each subdirectory.

Usage:
    python3 scripts/detect-skills-pool.py                    # print summary
    python3 scripts/detect-skills-pool.py --pool-dir PATH    # custom pool dir
    python3 scripts/detect-skills-pool.py --json             # machine-readable output
    python3 scripts/detect-skills-pool.py --dir ros2-engineering-skills  # single repo

Exit codes:
    0  success (new projects found or everything already known)
    1  pool directory not found
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = Path(__file__).parent.resolve()
INDEX_ROOT   = SCRIPT_DIR.parent
HUB_ROOT     = INDEX_ROOT.parent
POOL_DIR     = HUB_ROOT / "Skills_Pool"
REGISTRY_FILE = INDEX_ROOT / "data" / "skills-pool-registry.yaml"

# Subdirectory names that are safe to copy alongside SKILL.md
SAFE_COPY_DIRS = {"references", "examples", "docs", "assets", "evals", "prompts"}

# Markers that indicate a directory is NOT a skill repo (tool/framework)
NON_SKILL_MARKERS = {".openspec", "package.json", "pyproject.toml", "Cargo.toml"}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class DiscoveredSkill:
    name: str
    path: str          # relative to repo root
    entry_type: str    # "skill" or "agent"


@dataclass
class StructureProfile:
    dir_name: str
    pattern: str       # root-skill | skills-subdir | root-subdir | agents-only | raw-markdown | unknown
    stability: str     # stable | experimental
    discovered_skills: list[DiscoveredSkill] = field(default_factory=list)
    extra_copy_dirs: list[str] = field(default_factory=list)
    notes: str = ""
    skip_reason: str = ""


# ── Git helpers ───────────────────────────────────────────────────────────────

def get_git_sha(repo_path: Path) -> str:
    """Return HEAD sha for a git repo, empty string if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_github_url(repo_path: Path) -> str:
    """Return remote origin URL, empty string if unavailable."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


# ── Frontmatter check ─────────────────────────────────────────────────────────

def has_valid_frontmatter(md_file: Path) -> bool:
    """Return True if the file has YAML frontmatter with name + description."""
    try:
        text = md_file.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            return False
        parts = text.split("---", 2)
        if len(parts) < 3:
            return False
        fm = yaml.safe_load(parts[1]) or {}
        return bool(fm.get("name")) and bool(fm.get("description"))
    except Exception:
        return False


# ── Detection algorithm ───────────────────────────────────────────────────────

def scan_one(repo_path: Path) -> StructureProfile:
    """
    Inspect a single Skills_Pool subdirectory and return a StructureProfile.
    Detection order (first match wins):
      1. .claude-plugin/marketplace.json  → explicit plugin manifest
      2. SKILL.md at root                → root-skill
      3. skills/{name}/SKILL.md          → skills-subdir
      4. {name}/SKILL.md at root level   → root-subdir
      5. agents/{name}.md                → agents-only
      6. *.md files anywhere (≤2 levels) → raw-markdown
      7. fallback                        → unknown
    """
    dir_name = repo_path.name
    profile = StructureProfile(dir_name=dir_name, pattern="unknown", stability="stable")

    if not repo_path.is_dir():
        profile.skip_reason = "not a directory"
        return profile

    # ── Step 1: marketplace.json ─────────────────────────────────────────────
    marketplace = repo_path / ".claude-plugin" / "marketplace.json"
    if marketplace.exists():
        try:
            data = json.loads(marketplace.read_text(encoding="utf-8"))
            for plugin in data.get("plugins", []):
                for skill_src in plugin.get("skills", []):
                    skill_root = (repo_path / skill_src).resolve()
                    if skill_root == repo_path:
                        rel = "SKILL.md"
                    else:
                        try:
                            rel = (skill_root / "SKILL.md").relative_to(repo_path).as_posix()
                        except ValueError:
                            rel = "SKILL.md"
                    if (repo_path / rel).exists():
                        profile.discovered_skills.append(
                            DiscoveredSkill(
                                name=dir_name,
                                path=rel,
                                entry_type="skill",
                            )
                        )
            if profile.discovered_skills:
                profile.pattern = "root-skill"
                _detect_extra_dirs(repo_path, profile)
                return profile
        except (json.JSONDecodeError, KeyError):
            pass

    # ── Step 2: SKILL.md at root ─────────────────────────────────────────────
    root_skill = repo_path / "SKILL.md"
    if root_skill.exists():
        profile.pattern = "root-skill"
        profile.discovered_skills.append(
            DiscoveredSkill(name=dir_name, path="SKILL.md", entry_type="skill")
        )
        _detect_extra_dirs(repo_path, profile)
        _detect_agents(repo_path, profile)
        return profile

    # ── Step 3: skills/{name}/SKILL.md ──────────────────────────────────────
    skills_subdir = repo_path / "skills"
    if skills_subdir.is_dir():
        found = []
        for candidate in sorted(skills_subdir.iterdir()):
            if candidate.is_dir() and (candidate / "SKILL.md").exists():
                found.append(
                    DiscoveredSkill(
                        name=candidate.name,
                        path=f"skills/{candidate.name}/SKILL.md",
                        entry_type="skill",
                    )
                )
        if found:
            profile.pattern = "skills-subdir"
            profile.discovered_skills.extend(found)
            _detect_agents(repo_path, profile)
            return profile

    # ── Step 4: {name}/SKILL.md at root (flat layout like gstack) ───────────
    flat_found = []
    for candidate in sorted(repo_path.iterdir()):
        if candidate.is_dir() and (candidate / "SKILL.md").exists():
            flat_found.append(
                DiscoveredSkill(
                    name=candidate.name,
                    path=f"{candidate.name}/SKILL.md",
                    entry_type="skill",
                )
            )
    if flat_found:
        profile.pattern = "root-subdir"
        profile.discovered_skills.extend(flat_found)
        _detect_agents(repo_path, profile)
        return profile

    # ── Step 5: agents/{name}.md only ────────────────────────────────────────
    agents_found = _collect_agents(repo_path)
    if agents_found:
        profile.pattern = "agents-only"
        profile.discovered_skills.extend(agents_found)
        return profile

    # ── Step 6: raw .md files (no frontmatter) ───────────────────────────────
    raw_mds = []
    for md in repo_path.glob("*.md"):
        if md.name.lower() not in ("readme.md", "changelog.md", "license.md"):
            raw_mds.append(md)
    # Also check one level deep
    for subdir in repo_path.iterdir():
        if subdir.is_dir() and subdir.name not in (".git", ".github", "node_modules"):
            for md in subdir.glob("*.md"):
                raw_mds.append(md)

    if raw_mds:
        profile.pattern = "raw-markdown"
        profile.notes = f"Found {len(raw_mds)} .md files — frontmatter will be auto-generated"
        for md in raw_mds[:5]:  # max 5 discovered, curator reviews rest
            rel = md.relative_to(repo_path).as_posix()
            profile.discovered_skills.append(
                DiscoveredSkill(name=md.stem, path=rel, entry_type="skill")
            )
        return profile

    # ── Step 7: unknown ───────────────────────────────────────────────────────
    profile.pattern = "unknown"
    profile.skip_reason = "no SKILL.md, agent .md, or raw markdown files detected"
    return profile


def _detect_extra_dirs(repo_path: Path, profile: StructureProfile) -> None:
    """Detect safe subdirectories to copy alongside SKILL.md."""
    for d in sorted(repo_path.iterdir()):
        if d.is_dir() and d.name in SAFE_COPY_DIRS:
            profile.extra_copy_dirs.append(d.name)


def _detect_agents(repo_path: Path, profile: StructureProfile) -> None:
    """Detect agents/{name}.md and append to discovered_skills."""
    for agent in _collect_agents(repo_path):
        profile.discovered_skills.append(agent)


def _collect_agents(repo_path: Path) -> list[DiscoveredSkill]:
    agents_dir = repo_path / "agents"
    if not agents_dir.is_dir():
        return []
    found = []
    for md in sorted(agents_dir.glob("*.md")):
        found.append(
            DiscoveredSkill(
                name=md.stem,
                path=f"agents/{md.name}",
                entry_type="agent",
            )
        )
    return found


# ── Pool scanner ──────────────────────────────────────────────────────────────

def scan_pool(pool_dir: Path, target: Optional[str] = None) -> list[StructureProfile]:
    """
    Scan all subdirectories in pool_dir (or just `target` if given).
    Returns list of StructureProfile.
    """
    if not pool_dir.exists():
        return []

    dirs = []
    if target:
        candidate = pool_dir / target
        if candidate.is_dir():
            dirs = [candidate]
    else:
        dirs = sorted(d for d in pool_dir.iterdir() if d.is_dir() and d.name != ".git")

    return [scan_one(d) for d in dirs]


# ── Registry helpers ──────────────────────────────────────────────────────────

def load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {}
    with open(REGISTRY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_registry(registry: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        yaml.dump(registry, f, default_flow_style=False, allow_unicode=True, sort_keys=True)


def update_registry(profiles: list[StructureProfile], pool_dir: Path) -> tuple[list[str], list[str]]:
    """
    Merge scan results into registry.
    Returns (new_projects, changed_projects).
    """
    registry = load_registry()
    now = datetime.now(timezone.utc).isoformat()
    new_projects: list[str] = []
    changed_projects: list[str] = []

    for profile in profiles:
        repo_path = pool_dir / profile.dir_name
        current_sha = get_git_sha(repo_path)
        github_url  = get_github_url(repo_path)

        existing = registry.get(profile.dir_name, {})
        prev_sha = existing.get("last_git_sha", "")
        prev_status = existing.get("import_status", "")

        is_new = profile.dir_name not in registry
        is_changed = (
            not is_new
            and current_sha
            and prev_sha
            and current_sha != prev_sha
            and prev_status == "imported"
        )

        if is_new:
            new_projects.append(profile.dir_name)
        elif is_changed:
            changed_projects.append(profile.dir_name)

        # Don't overwrite managed-by-sources entries (those are controlled by SOURCES dict)
        if prev_status == "managed-by-sources":
            registry[profile.dir_name]["last_scanned"] = now
            if current_sha:
                registry[profile.dir_name]["last_git_sha"] = current_sha
            if github_url:
                registry[profile.dir_name]["github_url"] = github_url
            continue

        # Build registry entry
        entry = {
            "github_url": github_url or existing.get("github_url", ""),
            "source_root": str(repo_path.resolve()),
            "detected_pattern": profile.pattern,
            "stability": existing.get("stability", profile.stability),
            "discovered_skills": [
                {"name": s.name, "path": s.path, "type": s.entry_type}
                for s in profile.discovered_skills
            ],
            "extra_copy_dirs": existing.get("extra_copy_dirs") or profile.extra_copy_dirs,
            "last_scanned": now,
            "last_git_sha": current_sha,
            "import_status": existing.get("import_status", "pending") if not is_new else "pending",
            "skip_reason": profile.skip_reason or existing.get("skip_reason", ""),
            "notes": existing.get("notes", profile.notes),
        }

        # Auto-set status for unknown/skipped patterns on first scan
        if is_new and profile.pattern == "unknown":
            entry["import_status"] = "skipped"

        registry[profile.dir_name] = entry

    save_registry(registry)
    return new_projects, changed_projects


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Skills_Pool/ and detect skill/agent structure."
    )
    parser.add_argument("--pool-dir", type=Path, default=POOL_DIR,
                        help=f"Path to Skills_Pool directory (default: {POOL_DIR})")
    parser.add_argument("--dir", metavar="NAME",
                        help="Scan only this subdirectory name")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output JSON instead of human-readable summary")
    parser.add_argument("--update-registry", action="store_true",
                        help="Write results into data/skills-pool-registry.yaml")
    args = parser.parse_args()

    pool_dir: Path = args.pool_dir
    if not pool_dir.exists():
        if pool_dir == POOL_DIR:
            # The default Skills_Pool/ lives outside this git repo and is
            # legitimately absent until the first import (see `import` in
            # commands/librarian.md) — not an error, just nothing to scan yet.
            print("[]" if args.as_json else f"\nSkills Pool scan: {pool_dir}\n  (does not exist yet — nothing to scan)\n")
            return 0
        print(f"[ERROR] Pool directory not found: {pool_dir}", file=sys.stderr)
        return 1

    profiles = scan_pool(pool_dir, target=args.dir)

    if args.as_json:
        output = []
        for p in profiles:
            output.append({
                "dir_name": p.dir_name,
                "pattern": p.pattern,
                "stability": p.stability,
                "discovered_skills": [
                    {"name": s.name, "path": s.path, "type": s.entry_type}
                    for s in p.discovered_skills
                ],
                "extra_copy_dirs": p.extra_copy_dirs,
                "skip_reason": p.skip_reason,
                "notes": p.notes,
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\nSkills Pool scan: {pool_dir}\n")
        for p in profiles:
            skill_count = len([s for s in p.discovered_skills if s.entry_type == "skill"])
            agent_count = len([s for s in p.discovered_skills if s.entry_type == "agent"])
            parts = [f"  [{p.pattern}]"]
            if skill_count:
                parts.append(f"{skill_count} skill(s)")
            if agent_count:
                parts.append(f"{agent_count} agent(s)")
            if p.extra_copy_dirs:
                parts.append(f"+ dirs: {p.extra_copy_dirs}")
            if p.skip_reason:
                parts.append(f"→ SKIP: {p.skip_reason}")
            print(f"  {p.dir_name}")
            print("  " + "  ".join(parts))
            for s in p.discovered_skills:
                print(f"      - {s.entry_type}: {s.name}  ({s.path})")
            print()

    if args.update_registry:
        new_p, changed_p = update_registry(profiles, pool_dir)
        if new_p:
            print(f"[Registry] New projects: {new_p}")
        if changed_p:
            print(f"[Registry] Changed projects: {changed_p}")
        print(f"[Registry] Updated → {REGISTRY_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
