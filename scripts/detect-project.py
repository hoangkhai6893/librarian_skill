#!/usr/bin/env python3
"""
detect-project.py — Scan a project directory and suggest matching stacks.
Called by the session-start hook for new projects (no library-manifest.yaml).

Usage:
    python3 scripts/detect-project.py [project_dir]

Output:
    Human-readable suggestion message (1-3 lines) on stdout.
    Silent (no output) if no signals detected.
    Exit 0 always.
"""

import json
import sys
from pathlib import Path

import yaml

SCRIPT_DIR   = Path(__file__).parent.resolve()
INDEX_ROOT   = SCRIPT_DIR.parent
LIBRARY      = INDEX_ROOT / "library"
CATALOG_FILE = LIBRARY / "catalog.json"

# ── File signals → tech/domain mapping ───────────────────────────────────────

FILE_SIGNALS: dict[str, dict[str, list[str]]] = {
    "CMakeLists.txt": {"technologies": ["cpp"], "domains": []},
    "package.xml":    {"technologies": ["ros2"], "domains": ["robotics"]},
    "colcon.meta":    {"technologies": ["ros2"], "domains": ["robotics"]},
    "go.mod":         {"technologies": ["go"],   "domains": ["web-backend"]},
    "Cargo.toml":     {"technologies": ["rust"],  "domains": []},
    "pyproject.toml": {"technologies": ["python"], "domains": []},
    "requirements.txt": {"technologies": ["python"], "domains": []},
    "setup.py":       {"technologies": ["python"], "domains": []},
    "package.json":   {"technologies": ["typescript", "javascript"], "domains": []},
    "tsconfig.json":  {"technologies": ["typescript"], "domains": []},
    "Dockerfile":     {"technologies": ["docker"], "domains": ["devops"]},
}

CONTENT_SIGNALS: dict[str, dict[str, list[str]]] = {
    # file_glob → {keyword → tech/domain addition}
    "CMakeLists.txt": {
        "ament_cmake": {"technologies": ["ros2"], "domains": ["robotics"]},
        "rclcpp":      {"technologies": ["ros2", "cpp"], "domains": ["robotics"]},
    },
    "package.json": {
        '"react"':     {"technologies": ["react"], "domains": ["web-frontend"]},
        '"next':       {"technologies": ["react"], "domains": ["web-frontend"]},
        '"vue"':       {"technologies": [], "domains": ["web-frontend"]},
        '"fastapi"':   {"technologies": ["python"], "domains": ["web-backend"]},
        '"express"':   {"technologies": [], "domains": ["web-backend"]},
    },
    "pyproject.toml": {
        "pytorch":     {"technologies": ["pytorch"], "domains": ["ai-ml"]},
        "torch":       {"technologies": ["pytorch"], "domains": ["ai-ml"]},
        "fastapi":     {"technologies": [], "domains": ["web-backend"]},
        "django":      {"technologies": [], "domains": ["web-backend"]},
    },
    "requirements.txt": {
        "torch":       {"technologies": ["pytorch"], "domains": ["ai-ml"]},
        "pytorch":     {"technologies": ["pytorch"], "domains": ["ai-ml"]},
        "fastapi":     {"technologies": [], "domains": ["web-backend"]},
        "django":      {"technologies": [], "domains": ["web-backend"]},
    },
}


def extract_signals(project: Path) -> dict[str, list[str]]:
    techs: set[str]   = set()
    domains: set[str] = set()

    for filename, signals in FILE_SIGNALS.items():
        if (project / filename).exists():
            techs.update(signals["technologies"])
            domains.update(signals["domains"])

    # Deep content checks
    for filename, keyword_map in CONTENT_SIGNALS.items():
        fpath = project / filename
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for kw, additions in keyword_map.items():
                    if kw in content:
                        techs.update(additions.get("technologies", []))
                        domains.update(additions.get("domains", []))
            except OSError:
                pass

    return {"technologies": list(techs), "domains": list(domains)}


def score_stack(stack: dict, signals: dict) -> float:
    """Score a stack against detected signals (0-100)."""
    proj_signals = stack.get("project_signals", {})

    stack_techs   = proj_signals.get("technologies", [])
    stack_domains = proj_signals.get("domains", [])
    stack_files   = proj_signals.get("file_patterns", [])

    detected_techs   = set(signals["technologies"])
    detected_domains = set(signals["domains"])

    # Tech score
    if stack_techs:
        matched_techs = sum(1 for t in stack_techs if t in detected_techs)
        tech_score = (matched_techs / len(stack_techs)) * 100
    else:
        tech_score = 0

    # Domain score
    if stack_domains:
        matched_domains = sum(1 for d in stack_domains if d in detected_domains)
        domain_score = (matched_domains / len(stack_domains)) * 100
    else:
        domain_score = 0

    # File pattern score (from current directory)
    # (We already checked via FILE_SIGNALS, use tech/domain as proxy)
    # For simplicity: weight by tech 30%, domain 70% (no cwd glob here)
    return tech_score * 0.30 + domain_score * 0.70


def find_best_stack(catalog: dict, signals: dict) -> tuple[str | None, float]:
    if not signals["technologies"] and not signals["domains"]:
        return None, 0.0

    best_id    = None
    best_score = 0.0

    for stack in catalog.get("stacks", []):
        score = score_stack(stack, signals)
        if score > best_score:
            best_score = score
            best_id    = stack.get("id")

    if best_score < 20.0:
        return None, best_score
    return best_id, best_score


def main() -> int:
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    project = project.resolve()

    if not CATALOG_FILE.exists():
        return 0   # Silent if library not set up

    try:
        with open(CATALOG_FILE, encoding="utf-8") as f:
            catalog = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0

    signals = extract_signals(project)
    if not signals["technologies"] and not signals["domains"]:
        # No file/content signals matched — still let the agent know the library
        # exists so it isn't left completely unaware of available skills.
        total = catalog.get("totalEntries", 0)
        stack_ids = [s.get("id") for s in catalog.get("stacks", []) if s.get("id")]
        if total:
            print(f"[Agent Hub] Skill library available: {total} skills/agents "
                  f"({', '.join(stack_ids)} stacks pre-built)")
            print("Run /librarian browse (list all) or /librarian search <keyword> to find one")
        return 0

    stack_id, score = find_best_stack(catalog, signals)

    if stack_id:
        stack_count = 0
        for s in catalog.get("stacks", []):
            if s.get("id") == stack_id:
                core = len(s.get("core_skills", []))
                workflow = len(s.get("workflow_skills", []))
                stack_count = core + workflow
                break

        print(f"[Agent Hub] Detected project: {', '.join(signals['technologies'] + signals['domains'])}")
        print(f"Suggested stack: {stack_id} ({stack_count} skills, fit: {score:.0f}%)")
        print(f"Run: /librarian stack {stack_id}  or  /librarian recommend")
    else:
        detected = ", ".join((signals["technologies"] + signals["domains"])[:3])
        if detected:
            print(f"[Agent Hub] Detected: {detected}")
            print(f"Run /librarian recommend for skill suggestions")

    return 0


if __name__ == "__main__":
    sys.exit(main())
