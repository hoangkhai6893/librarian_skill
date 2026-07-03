"""
pytest configuration, shared fixtures, and helpers.

Provides:
  - load_script()       Import hyphen-named scripts as modules
  - HubFixture          Complete fake hub with library, source projects, stacks, collections
  - real_library_path   Points to the actual agent-hub-index library (read-only)
"""

import importlib.util
import json
import sys
import types
import yaml
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
INDEX_ROOT = Path(__file__).parent.parent
REAL_LIBRARY = INDEX_ROOT / "library"


# ── Script loader ─────────────────────────────────────────────────────────────


def load_script(name: str) -> types.ModuleType:
    """Load a script from scripts/ by filename (hyphens allowed)."""
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name.replace("-", "_")] = mod
    spec.loader.exec_module(mod)
    return mod


# ── Skill content factory ─────────────────────────────────────────────────────


def make_skill_content(skill_id: str, extra_body: str = "") -> str:
    name = skill_id.replace("-", " ").title()
    return (
        f"---\nname: {name}\n"
        f"description: Use when you need to {skill_id.replace('-', ' ')}\n---\n"
        f"# {name}\n\n"
        f"This skill helps with {skill_id.replace('-', ' ')}.\n"
        f"{extra_body}\n"
    )


def make_agent_content(agent_id: str) -> str:
    name = agent_id.replace("-", " ").title()
    return (
        f"---\nname: {name}\n"
        f"description: Agent for {agent_id.replace('-', ' ')}\n"
        f"model: claude-sonnet-4-6\n"
        f'tools: ["Read", "Write", "Bash"]\n---\n'
        f"# {name}\n\nYou are the {name} agent.\n"
    )


# ── HubFixture ────────────────────────────────────────────────────────────────


class HubFixture:
    """
    A complete isolated fake Agent Hub for testing.

    Structure:
      root/
        superpowers/            ← source project
          skills/{id}/SKILL.md
          agents/{id}.md
        library/                ← curated library
          skills/{id}/SKILL.md
          agents/{id}.md
          provenance/{id}.yaml
          enrichment/{id}.yaml
          collections/
          stacks/
          catalog.json
    """

    SKILL_IDS = [
        "brainstorming",
        "systematic-debugging",
        "code-review",
        "tdd-workflow",
        "writing-plans",
        "executing-plans",
        "docker-patterns",
        "security-scan",
        "api-design",
        "frontend-patterns",
    ]

    AGENT_IDS = ["librarian", "code-reviewer"]

    def __init__(self, root: Path):
        self.root = root
        self.source = root / "superpowers"
        self.library = root / "agent-hub-index" / "library"
        self.scripts = INDEX_ROOT / "scripts"  # always use real scripts
        self._build()

    def _build(self):
        self._build_source()
        self._build_library()

    def _build_source(self):
        """Create fake source project (superpowers)."""
        for sid in self.SKILL_IDS:
            d = self.source / "skills" / sid
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(make_skill_content(sid), encoding="utf-8")

        for aid in self.AGENT_IDS:
            d = self.source / "agents"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{aid}.md").write_text(make_agent_content(aid), encoding="utf-8")

    def _build_library(self):
        """Build a pre-populated library (simulates skills already imported)."""
        lib = self.library
        (lib / "provenance").mkdir(parents=True, exist_ok=True)
        (lib / "enrichment").mkdir(parents=True, exist_ok=True)
        (lib / "agents").mkdir(parents=True, exist_ok=True)
        (lib / "collections").mkdir(parents=True, exist_ok=True)
        (lib / "stacks").mkdir(parents=True, exist_ok=True)

        for sid in self.SKILL_IDS:
            skill_dir = lib / "skills" / sid
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                make_skill_content(sid), encoding="utf-8"
            )

            (lib / "provenance" / f"{sid}.yaml").write_text(
                yaml.dump(
                    {
                        "source_project": "superpowers",
                        "source_path": f"skills/{sid}/SKILL.md",
                        "imported_at": "2026-01-01T00:00:00+00:00",
                        "imported_by": "test",
                        "library_version": "1.0",
                        "customized": False,
                        "notes": "",
                    }
                ),
                encoding="utf-8",
            )

            (lib / "enrichment" / f"{sid}.yaml").write_text(
                yaml.dump(
                    {
                        "use_with": [],
                        "conflicts_with": [],
                        "project_types": ["any"],
                        "complexity": "intermediate",
                        "usage_pattern": "standalone",
                        "curator_notes": "",
                    }
                ),
                encoding="utf-8",
            )

        for aid in self.AGENT_IDS:
            (lib / "agents" / f"{aid}.md").write_text(
                make_agent_content(aid), encoding="utf-8"
            )

        self._build_collection()
        self._build_stack()
        self.build_catalog()

    def _build_collection(self):
        """Create a test collection YAML using only skills from SKILL_IDS."""
        # Use real collection name but with valid skill IDs from our fixture
        coll = {
            "id": "debugging-deep-dive",
            "name": "Debugging Deep Dive (Test Version)",
            "curator": "test",
            "description": "Comprehensive debugging workflow using available skills.",
            "entries": [
                {"id": "brainstorming", "seq": 1, "role": "Understand the problem"},
                {
                    "id": "systematic-debugging",
                    "seq": 2,
                    "role": "Systematically find the bug",
                },
                {"id": "code-review", "seq": 3, "role": "Review the fix"},
            ],
            "tags": ["debugging", "workflow"],
        }
        (self.library / "collections" / "debugging-deep-dive.yaml").write_text(
            yaml.dump(coll), encoding="utf-8"
        )

    def _build_stack(self):
        """Create a test stack YAML."""
        # Use real stack name from the actual catalog with skills that exist in HubFixture
        stack = {
            "id": "web-fullstack-typescript",
            "name": "Web FullStack TypeScript",
            "description": "Stack for web development with TypeScript.",
            "project_signals": {
                "technologies": ["typescript", "frontend-patterns"],
                "domains": ["web-frontend"],
                "file_patterns": ["package.json"],
            },
            "core_skills": [
                {"id": "api-design", "priority": "critical", "why": "API design"},
                {"id": "frontend-patterns", "priority": "critical", "why": "Frontend"},
                {"id": "security-scan", "priority": "high", "why": "Security"},
            ],
            "workflow_skills": [
                {"id": "brainstorming", "priority": "high", "why": "Planning"},
                {"id": "code-review", "priority": "high", "why": "Quality"},
                {"id": "tdd-workflow", "priority": "medium", "why": "Testing workflow"},
            ],
        }
        (self.library / "stacks" / "web-fullstack-typescript.yaml").write_text(
            yaml.dump(stack), encoding="utf-8"
        )

    def build_catalog(self):
        """Run build-catalog against this library and return the catalog dict."""
        bc = load_script("build-catalog")
        import unittest.mock as mock

        with (
            mock.patch.object(bc, "LIBRARY", self.library),
            mock.patch.object(bc, "CATALOG_FILE", self.library / "catalog.json"),
            mock.patch.object(
                bc, "KEYWORDS_FILE", SCRIPTS_DIR / "domain-keywords.json"
            ),
        ):
            # Reload KW tables since we monkeypatched KEYWORDS_FILE
            kw = bc.load_keywords()
            bc.DOMAIN_KEYWORDS = kw.get("DOMAIN_KEYWORDS", {})
            bc.TECH_KEYWORDS = kw.get("TECH_KEYWORDS", {})
            bc.PHASE_KEYWORDS = kw.get("PHASE_KEYWORDS", {})
            catalog = bc.build_catalog(verbose=False)
        return catalog

    def get_catalog(self) -> dict:
        catalog_file = self.library / "catalog.json"
        return json.loads(catalog_file.read_text(encoding="utf-8"))

    def make_project(self, name: str = "myproject") -> Path:
        """Create a blank target project directory."""
        project = self.root / name
        project.mkdir(parents=True, exist_ok=True)
        return project

    def modify_skill(self, skill_id: str, append_text: str = "\n## Updated section\n"):
        """Modify a skill in the library to simulate an update."""
        skill_file = self.library / "skills" / skill_id / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        skill_file.write_text(content + append_text, encoding="utf-8")

    @property
    def catalog_ids(self) -> set:
        return {e["id"] for e in self.get_catalog().get("entries", [])}


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def hub(tmp_path) -> HubFixture:
    """Full isolated fake Agent Hub fixture."""
    return HubFixture(tmp_path)


@pytest.fixture
def real_library_path() -> Path:
    """Path to the real curated library (read-only, never modify)."""
    return REAL_LIBRARY
