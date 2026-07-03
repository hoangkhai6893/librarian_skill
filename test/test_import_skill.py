#!/usr/bin/env python3
"""Unit tests for import-skill.py"""

import yaml
from pathlib import Path
from conftest import load_script

imp = load_script("import-skill")


# ── get_library_id ────────────────────────────────────────────────────────────

class TestGetLibraryId:
    def test_lowercase(self):
        assert imp.get_library_id("MySkill") == "myskill"

    def test_spaces_become_hyphens(self):
        assert imp.get_library_id("my skill") == "my-skill"

    def test_underscores_become_hyphens(self):
        assert imp.get_library_id("my_skill") == "my-skill"

    def test_already_kebab_case(self):
        assert imp.get_library_id("my-skill") == "my-skill"

    def test_strips_leading_trailing_hyphens(self):
        result = imp.get_library_id("  skill  ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_special_chars_replaced(self):
        result = imp.get_library_id("skill!@#name")
        assert "!" not in result
        assert "@" not in result


# ── parse_frontmatter ─────────────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        f = tmp_path / "skill.md"
        f.write_text("---\nname: Test\ndescription: Use when testing\n---\nBody", encoding="utf-8")
        fm, body = imp.parse_frontmatter(f)
        assert fm["name"] == "Test"
        assert "Body" in body

    def test_no_frontmatter_returns_empty_dict(self, tmp_path):
        f = tmp_path / "skill.md"
        f.write_text("Just body", encoding="utf-8")
        fm, body = imp.parse_frontmatter(f)
        assert fm == {}

    def test_bad_yaml_raises_value_error(self, tmp_path):
        import pytest
        f = tmp_path / "skill.md"
        f.write_text("---\n: [broken\n---\nBody", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML parse error"):
            imp.parse_frontmatter(f)


# ── validate_frontmatter ──────────────────────────────────────────────────────

class TestValidateFrontmatter:
    def test_valid_skill_frontmatter(self):
        fm = {"name": "My Skill", "description": "Use when testing code"}
        imp.validate_frontmatter(fm, "skill")  # Should not raise

    def test_missing_name_raises(self):
        import pytest
        fm = {"description": "Use when testing"}
        with pytest.raises(ValueError, match="name"):
            imp.validate_frontmatter(fm, "skill")

    def test_missing_description_raises(self):
        import pytest
        fm = {"name": "My Skill"}
        with pytest.raises(ValueError, match="description"):
            imp.validate_frontmatter(fm, "skill")

    def test_valid_agent_frontmatter(self):
        fm = {"name": "My Agent", "description": "Does stuff"}
        imp.validate_frontmatter(fm, "agent")  # Should not raise


# ── find_source_file ──────────────────────────────────────────────────────────

class TestFindSourceFile:
    def _make_source(self, tmp_path: Path) -> dict:
        skill_dir = tmp_path / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").touch()
        return {
            "root": tmp_path,
            "skill_patterns": ["skills/{name}/SKILL.md"],
            "agent_patterns": ["agents/{name}.md"],
        }

    def test_finds_skill(self, tmp_path):
        src_cfg = self._make_source(tmp_path)
        path, detected = imp.find_source_file(src_cfg, "my-skill", "skill")
        assert path.exists()
        assert detected == "skill"

    def test_finds_agent(self, tmp_path):
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir(parents=True)
        (agent_dir / "my-agent.md").touch()
        src_cfg = {
            "root": tmp_path,
            "skill_patterns": [],
            "agent_patterns": ["agents/{name}.md"],
        }
        path, detected = imp.find_source_file(src_cfg, "my-agent", "agent")
        assert path.exists()
        assert detected == "agent"

    def test_not_found_raises_file_not_found(self, tmp_path):
        src_cfg = self._make_source(tmp_path)
        import pytest
        with pytest.raises(FileNotFoundError):
            imp.find_source_file(src_cfg, "ghost-skill", "skill")

    def test_auto_detects_type(self, tmp_path):
        src_cfg = self._make_source(tmp_path)
        path, detected = imp.find_source_file(src_cfg, "my-skill", None)
        assert detected == "skill"


# ── import_entry ──────────────────────────────────────────────────────────────

class TestImportEntry:
    def _make_hub(self, tmp_path: Path):
        """Set up a fake hub with a source project and library."""
        source_root = tmp_path / "superpowers"
        skill_dir = source_root / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: My Skill\ndescription: Use when testing\n---\nBody",
            encoding="utf-8"
        )

        lib = tmp_path / "library"
        (lib / "skills").mkdir(parents=True)
        (lib / "provenance").mkdir(parents=True)
        (lib / "enrichment").mkdir(parents=True)
        (lib / "agents").mkdir(parents=True)

        return source_root, lib

    def test_import_new_skill(self, tmp_path, monkeypatch):
        source_root, lib = self._make_hub(tmp_path)
        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(imp, "SOURCES", {
            "superpowers": {
                "root": source_root,
                "skill_patterns": ["skills/{name}/SKILL.md"],
                "agent_patterns": [],
                "stability": "stable",
            }
        })

        exit_code = imp.import_entry(
            source_name="superpowers",
            skill_name="my-skill",
            entry_type="skill",
            dry_run=False,
            force=False,
            verbose=False,
        )
        assert exit_code == 0
        assert (lib / "skills" / "my-skill" / "SKILL.md").exists()
        assert (lib / "provenance" / "my-skill.yaml").exists()
        assert (lib / "enrichment" / "my-skill.yaml").exists()

    def test_conflict_without_force_returns_3(self, tmp_path, monkeypatch):
        source_root, lib = self._make_hub(tmp_path)
        (lib / "skills" / "my-skill").mkdir(parents=True)
        (lib / "skills" / "my-skill" / "SKILL.md").touch()
        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(imp, "SOURCES", {
            "superpowers": {
                "root": source_root,
                "skill_patterns": ["skills/{name}/SKILL.md"],
                "agent_patterns": [],
                "stability": "stable",
            }
        })

        exit_code = imp.import_entry(
            source_name="superpowers",
            skill_name="my-skill",
            entry_type="skill",
            dry_run=False,
            force=False,
            verbose=False,
        )
        assert exit_code == 3

    def test_dry_run_no_files_written(self, tmp_path, monkeypatch):
        source_root, lib = self._make_hub(tmp_path)
        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(imp, "SOURCES", {
            "superpowers": {
                "root": source_root,
                "skill_patterns": ["skills/{name}/SKILL.md"],
                "agent_patterns": [],
                "stability": "stable",
            }
        })

        exit_code = imp.import_entry(
            source_name="superpowers",
            skill_name="my-skill",
            entry_type="skill",
            dry_run=True,
            force=False,
            verbose=False,
        )
        assert exit_code == 0
        assert not (lib / "skills" / "my-skill").exists()

    def test_unknown_source_returns_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(imp, "SOURCES", {})
        exit_code = imp.import_entry(
            source_name="nonexistent",
            skill_name="my-skill",
            entry_type=None,
            dry_run=False,
            force=False,
            verbose=False,
        )
        assert exit_code == 1

    def test_missing_source_dir_returns_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr(imp, "SOURCES", {
            "superpowers": {
                "root": tmp_path / "nonexistent-dir",
                "skill_patterns": [],
                "agent_patterns": [],
                "stability": "stable",
            }
        })
        exit_code = imp.import_entry(
            source_name="superpowers",
            skill_name="my-skill",
            entry_type=None,
            dry_run=False,
            force=False,
            verbose=False,
        )
        assert exit_code == 1
