#!/usr/bin/env python3
"""Unit tests for validate.py"""

import json
import yaml
from pathlib import Path
from conftest import load_script

vl = load_script("validate")


# ── CheckResult ───────────────────────────────────────────────────────────────

class TestCheckResult:
    def test_initial_state_is_pass(self):
        r = vl.CheckResult("TEST")
        assert r.status == "pass"
        assert r.issues == []

    def test_fail_sets_status(self):
        r = vl.CheckResult("TEST")
        r.fail("something wrong")
        assert r.status == "fail"
        assert "something wrong" in r.issues

    def test_warn_sets_status_when_passing(self):
        r = vl.CheckResult("TEST")
        r.warn("minor issue")
        assert r.status == "warn"
        assert "[WARN] minor issue" in r.issues

    def test_fail_overrides_warn(self):
        r = vl.CheckResult("TEST")
        r.warn("minor")
        r.fail("critical")
        assert r.status == "fail"

    def test_warn_does_not_override_fail(self):
        r = vl.CheckResult("TEST")
        r.fail("critical")
        r.warn("minor")
        # fail status should remain
        assert r.status == "fail"

    def test_multiple_issues_accumulated(self):
        r = vl.CheckResult("TEST")
        r.fail("issue 1")
        r.fail("issue 2")
        assert len(r.issues) == 2

    def test_str_representation_pass(self):
        r = vl.CheckResult("MY_CHECK")
        s = str(r)
        assert "MY_CHECK" in s
        assert "PASS" in s

    def test_str_representation_fail(self):
        r = vl.CheckResult("MY_CHECK")
        r.fail("broken")
        s = str(r)
        assert "FAIL" in s
        assert "broken" in s


# ── check_skill_has_md ────────────────────────────────────────────────────────

class TestCheckSkillHasMd:
    def test_all_skills_have_skill_md(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills"
        (skills_dir / "my-skill").mkdir(parents=True)
        (skills_dir / "my-skill" / "SKILL.md").touch()
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)

        result = vl.check_skill_has_md()
        assert result.status == "pass"

    def test_missing_skill_md_fails(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills"
        (skills_dir / "broken-skill").mkdir(parents=True)
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)

        result = vl.check_skill_has_md()
        assert result.status == "fail"
        assert any("broken-skill" in issue for issue in result.issues)

    def test_no_skills_dir_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)
        result = vl.check_skill_has_md()
        assert result.status == "fail"


# ── check_skill_has_provenance ────────────────────────────────────────────────

class TestCheckSkillHasProvenance:
    def test_all_provenance_present(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills" / "my-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").touch()
        prov_dir = tmp_path / "provenance"
        prov_dir.mkdir()
        (prov_dir / "my-skill.yaml").touch()
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)

        result = vl.check_skill_has_provenance()
        assert result.status == "pass"

    def test_missing_provenance_warns(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills" / "my-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").touch()
        (tmp_path / "provenance").mkdir()
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)

        result = vl.check_skill_has_provenance()
        assert result.status == "warn"


# ── check_agent_valid_frontmatter ─────────────────────────────────────────────

class TestCheckAgentValidFrontmatter:
    def test_valid_agent(self, tmp_path, monkeypatch):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(
            "---\nname: My Agent\ndescription: Does stuff\n---\nBody",
            encoding="utf-8"
        )
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)
        result = vl.check_agent_valid_frontmatter()
        assert result.status == "pass"

    def test_missing_name_fails(self, tmp_path, monkeypatch):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "bad.md").write_text(
            "---\ndescription: No name here\n---\nBody",
            encoding="utf-8"
        )
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)
        result = vl.check_agent_valid_frontmatter()
        assert result.status == "fail"

    def test_missing_description_fails(self, tmp_path, monkeypatch):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "bad.md").write_text(
            "---\nname: Agent\n---\nBody",
            encoding="utf-8"
        )
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)
        result = vl.check_agent_valid_frontmatter()
        assert result.status == "fail"

    def test_no_frontmatter_fails(self, tmp_path, monkeypatch):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "bad.md").write_text("Just a body without frontmatter", encoding="utf-8")
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)
        result = vl.check_agent_valid_frontmatter()
        assert result.status == "fail"


# ── check_catalog_exists ──────────────────────────────────────────────────────

class TestCheckCatalogExists:
    def test_valid_catalog(self, tmp_path, monkeypatch):
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text(json.dumps({"entries": []}), encoding="utf-8")
        monkeypatch.setattr(vl, "CATALOG_FILE", catalog_file)

        result, catalog = vl.check_catalog_exists()
        assert result.status == "pass"
        assert catalog is not None
        assert "entries" in catalog

    def test_missing_catalog_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vl, "CATALOG_FILE", tmp_path / "nonexistent.json")
        result, catalog = vl.check_catalog_exists()
        assert result.status == "fail"
        assert catalog is None

    def test_invalid_json_fails(self, tmp_path, monkeypatch):
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text("{broken json", encoding="utf-8")
        monkeypatch.setattr(vl, "CATALOG_FILE", catalog_file)

        result, catalog = vl.check_catalog_exists()
        assert result.status == "fail"
        assert catalog is None

    def test_catalog_missing_entries_key_fails(self, tmp_path, monkeypatch):
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text(json.dumps({"version": 1}), encoding="utf-8")
        monkeypatch.setattr(vl, "CATALOG_FILE", catalog_file)

        result, catalog = vl.check_catalog_exists()
        assert result.status == "fail"


# ── check_catalog_complete ────────────────────────────────────────────────────

class TestCheckCatalogComplete:
    def test_all_skills_in_catalog(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills" / "my-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").touch()
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)

        catalog = {"entries": [{"id": "my-skill", "type": "skill"}]}
        result = vl.check_catalog_complete(catalog)
        assert result.status == "pass"

    def test_skill_missing_from_catalog_fails(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "skills" / "orphan-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").touch()
        monkeypatch.setattr(vl, "LIBRARY", tmp_path)

        catalog = {"entries": []}
        result = vl.check_catalog_complete(catalog)
        assert result.status == "fail"
        assert any("orphan-skill" in issue for issue in result.issues)


# ── check_no_duplicate_ids ────────────────────────────────────────────────────

class TestCheckNoDuplicateIds:
    def test_no_duplicates_passes(self):
        catalog = {"entries": [
            {"id": "skill-a"},
            {"id": "skill-b"},
            {"id": "skill-c"},
        ]}
        result = vl.check_no_duplicate_ids(catalog)
        assert result.status == "pass"

    def test_duplicate_id_fails(self):
        catalog = {"entries": [
            {"id": "skill-a"},
            {"id": "skill-a"},
        ]}
        result = vl.check_no_duplicate_ids(catalog)
        assert result.status == "fail"
        assert any("skill-a" in issue for issue in result.issues)


# ── check_use_with_valid ──────────────────────────────────────────────────────

class TestCheckUseWithValid:
    def test_valid_references(self):
        catalog = {"entries": [
            {"id": "skill-a", "use_with": ["skill-b"], "conflicts_with": []},
            {"id": "skill-b", "use_with": [], "conflicts_with": []},
        ]}
        result = vl.check_use_with_valid(catalog)
        assert result.status == "pass"

    def test_invalid_use_with_reference_fails(self):
        catalog = {"entries": [
            {"id": "skill-a", "use_with": ["nonexistent"], "conflicts_with": []},
        ]}
        result = vl.check_use_with_valid(catalog)
        assert result.status == "fail"
        assert any("nonexistent" in issue for issue in result.issues)

    def test_invalid_conflicts_with_reference_fails(self):
        catalog = {"entries": [
            {"id": "skill-a", "use_with": [], "conflicts_with": ["ghost-skill"]},
        ]}
        result = vl.check_use_with_valid(catalog)
        assert result.status == "fail"


# ── run_validation integration ────────────────────────────────────────────────

class TestRunValidation:
    def _make_valid_library(self, tmp_path: Path) -> Path:
        """Create a minimal valid library structure."""
        lib = tmp_path / "library"
        skills_dir = lib / "skills" / "my-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").touch()
        (lib / "provenance" / "my-skill.yaml").parent.mkdir(parents=True)
        (lib / "provenance" / "my-skill.yaml").touch()
        (lib / "agents").mkdir(parents=True)
        (lib / "collections").mkdir(parents=True)
        (lib / "stacks").mkdir(parents=True)
        catalog = {
            "entries": [{"id": "my-skill", "type": "skill", "use_with": [], "conflicts_with": []}]
        }
        catalog_file = lib / "catalog.json"
        catalog_file.write_text(json.dumps(catalog), encoding="utf-8")
        return lib

    def test_valid_library_returns_0(self, tmp_path, monkeypatch):
        lib = self._make_valid_library(tmp_path)
        monkeypatch.setattr(vl, "LIBRARY", lib)
        monkeypatch.setattr(vl, "CATALOG_FILE", lib / "catalog.json")

        exit_code = vl.run_validation(strict=False, output_json=False)
        assert exit_code == 0

    def test_json_output_mode(self, tmp_path, monkeypatch, capsys):
        lib = self._make_valid_library(tmp_path)
        monkeypatch.setattr(vl, "LIBRARY", lib)
        monkeypatch.setattr(vl, "CATALOG_FILE", lib / "catalog.json")

        vl.run_validation(strict=False, output_json=True)
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert "status" in report
        assert "results" in report
        assert "summary" in report
