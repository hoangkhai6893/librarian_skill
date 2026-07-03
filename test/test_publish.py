#!/usr/bin/env python3
"""Unit tests for publish-to-project.py"""

import hashlib
import json
import yaml
from pathlib import Path
from conftest import load_script

pub = load_script("publish-to-project")


# ── sha256_file ───────────────────────────────────────────────────────────────

class TestSha256File:
    def test_known_hash(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello world")
        expected = "sha256:" + hashlib.sha256(b"hello world").hexdigest()
        assert pub.sha256_file(f) == expected

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content a")
        f2.write_bytes(b"content b")
        assert pub.sha256_file(f1) != pub.sha256_file(f2)

    def test_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"same content")
        f2.write_bytes(b"same content")
        assert pub.sha256_file(f1) == pub.sha256_file(f2)


# ── load_manifest ─────────────────────────────────────────────────────────────

class TestLoadManifest:
    def test_no_manifest_returns_empty(self, tmp_path):
        result = pub.load_manifest(tmp_path)
        assert result == {}

    def test_valid_manifest_loaded(self, tmp_path):
        manifest_data = {
            "schema_version": 1,
            "entries": [{"id": "my-skill", "type": "skill"}]
        }
        (tmp_path / "library-manifest.yaml").write_text(
            yaml.dump(manifest_data), encoding="utf-8"
        )
        result = pub.load_manifest(tmp_path)
        assert result["schema_version"] == 1
        assert len(result["entries"]) == 1

    def test_broken_yaml_returns_empty(self, tmp_path):
        (tmp_path / "library-manifest.yaml").write_text(
            ": broken: yaml: [", encoding="utf-8"
        )
        result = pub.load_manifest(tmp_path)
        assert result == {}


# ── save_manifest ─────────────────────────────────────────────────────────────

class TestSaveManifest:
    def test_saves_yaml_file(self, tmp_path):
        manifest = {"schema_version": 1, "entries": []}
        pub.save_manifest(tmp_path, manifest)
        assert (tmp_path / "library-manifest.yaml").exists()

    def test_adds_updated_at_field(self, tmp_path):
        manifest = {"entries": []}
        pub.save_manifest(tmp_path, manifest)
        loaded = yaml.safe_load((tmp_path / "library-manifest.yaml").read_text())
        assert "updated_at" in loaded

    def test_roundtrip(self, tmp_path):
        manifest = {
            "schema_version": 1,
            "entries": [{"id": "skill-a", "type": "skill"}]
        }
        pub.save_manifest(tmp_path, manifest)
        loaded = pub.load_manifest(tmp_path)
        assert loaded["schema_version"] == 1
        assert loaded["entries"][0]["id"] == "skill-a"


# ── resolve_stack ─────────────────────────────────────────────────────────────

class TestResolveStack:
    def _make_catalog(self):
        return {
            "stacks": [{
                "id": "my-stack",
                "core_skills": [{"id": "skill-a"}, {"id": "skill-b"}],
                "workflow_skills": [{"id": "skill-c"}],
            }]
        }

    def test_resolve_existing_stack(self):
        catalog = self._make_catalog()
        ids = pub.resolve_stack("my-stack", catalog)
        assert ids == ["skill-a", "skill-b", "skill-c"]

    def test_resolve_nonexistent_stack_exits(self):
        import pytest
        catalog = self._make_catalog()
        with pytest.raises(SystemExit) as exc:
            pub.resolve_stack("ghost-stack", catalog)
        assert exc.value.code == 2

    def test_skips_entries_without_id(self):
        catalog = {
            "stacks": [{
                "id": "my-stack",
                "core_skills": [{"id": "skill-a"}, {"name": "no-id"}],
                "workflow_skills": [],
            }]
        }
        ids = pub.resolve_stack("my-stack", catalog)
        assert ids == ["skill-a"]


# ── resolve_collection ────────────────────────────────────────────────────────

class TestResolveCollection:
    def _make_catalog(self):
        return {
            "collections": [{
                "id": "my-coll",
                "entries": [
                    {"id": "skill-b", "seq": 2},
                    {"id": "skill-a", "seq": 1},
                    {"id": "skill-c", "seq": 3},
                ],
            }]
        }

    def test_resolve_existing_collection(self):
        catalog = self._make_catalog()
        ids = pub.resolve_collection("my-coll", catalog)
        # Should be sorted by seq
        assert ids == ["skill-a", "skill-b", "skill-c"]

    def test_resolve_nonexistent_collection_exits(self):
        import pytest
        catalog = self._make_catalog()
        with pytest.raises(SystemExit) as exc:
            pub.resolve_collection("ghost-coll", catalog)
        assert exc.value.code == 2


# ── find_in_catalog ───────────────────────────────────────────────────────────

class TestFindInCatalog:
    def _make_catalog(self):
        return {
            "entries": [
                {"id": "skill-a", "type": "skill"},
                {"id": "skill-b", "type": "skill"},
                {"id": "my-agent", "type": "agent"},
            ]
        }

    def test_find_existing_skill(self):
        catalog = self._make_catalog()
        result = pub.find_in_catalog("skill-a", catalog)
        assert result is not None
        assert result["id"] == "skill-a"

    def test_find_nonexistent_returns_none(self):
        catalog = self._make_catalog()
        result = pub.find_in_catalog("ghost", catalog)
        assert result is None

    def test_find_agent(self):
        catalog = self._make_catalog()
        result = pub.find_in_catalog("my-agent", catalog)
        assert result is not None
        assert result["type"] == "agent"


# ── publish_one ───────────────────────────────────────────────────────────────

class TestPublishOne:
    def _make_library(self, tmp_path: Path) -> Path:
        lib = tmp_path / "library"
        skill_dir = lib / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (lib / "provenance").mkdir(parents=True)
        (lib / "enrichment").mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: My Skill\ndescription: Use when testing\n---\nBody",
            encoding="utf-8"
        )
        return lib

    def _make_catalog(self, lib: Path) -> dict:
        return {
            "entries": [{
                "id": "my-skill",
                "type": "skill",
                "path": "skills/my-skill/SKILL.md",
                "source": "superpowers",
            }]
        }

    def test_dry_run_no_files_created(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        monkeypatch.setattr(pub, "CATALOG_FILE", lib / "catalog.json")
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        result = pub.publish_one("my-skill", catalog, project, "claude-code", False, True)
        assert "dry-run" in result.status
        assert not (project / ".claude" / "skills" / "my-skill").exists()

    def test_creates_skill_directory(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        monkeypatch.setattr(pub, "CATALOG_FILE", lib / "catalog.json")
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        result = pub.publish_one("my-skill", catalog, project, "claude-code", False, False)
        assert result.status == "created"
        assert (project / ".claude" / "skills" / "my-skill").is_dir()

    def test_skipped_when_up_to_date(self, tmp_path, monkeypatch):
        import shutil
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        monkeypatch.setattr(pub, "CATALOG_FILE", lib / "catalog.json")
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        # First publish
        pub.publish_one("my-skill", catalog, project, "claude-code", False, False)
        # Second publish — should skip
        result = pub.publish_one("my-skill", catalog, project, "claude-code", False, False)
        assert result.status == "skipped"

    def test_conflict_without_force(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        monkeypatch.setattr(pub, "CATALOG_FILE", lib / "catalog.json")
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        # Plant a different file at destination
        target_dir = project / ".claude" / "skills" / "my-skill"
        target_dir.mkdir(parents=True)
        (target_dir / "SKILL.md").write_text("different content", encoding="utf-8")

        result = pub.publish_one("my-skill", catalog, project, "claude-code", False, False)
        assert result.status == "conflict"

    def test_force_overwrites_conflict(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        monkeypatch.setattr(pub, "CATALOG_FILE", lib / "catalog.json")
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        # Plant a different file at destination
        target_dir = project / ".claude" / "skills" / "my-skill"
        target_dir.mkdir(parents=True)
        (target_dir / "SKILL.md").write_text("different content", encoding="utf-8")

        result = pub.publish_one("my-skill", catalog, project, "claude-code", True, False)
        assert result.status == "updated"

    def test_not_found_in_catalog(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        catalog = {"entries": []}
        project = tmp_path / "myproject"
        project.mkdir()

        result = pub.publish_one("ghost-skill", catalog, project, "claude-code", False, False)
        assert result.status == "not_found"

    def test_opencode_platform_uses_different_dir(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        result = pub.publish_one("my-skill", catalog, project, "opencode", False, False)
        assert result.status == "created"
        assert (project / ".opencode" / "skills" / "my-skill").is_dir()

    def test_github_copilot_creates_prompt_md(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        result = pub.publish_one("my-skill", catalog, project, "github-copilot", False, False)
        assert result.status == "created"
        prompt_file = project / ".github" / "copilot" / "my-skill.prompt.md"
        assert prompt_file.exists()
        content = prompt_file.read_text()
        assert "mode: ask" in content
        assert "description:" in content
        # No subdir created for github-copilot skills
        assert not (project / ".github" / "copilot" / "my-skill").is_dir()

    def test_github_copilot_skipped_when_up_to_date(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        pub.publish_one("my-skill", catalog, project, "github-copilot", False, False)
        result = pub.publish_one("my-skill", catalog, project, "github-copilot", False, False)
        assert result.status == "skipped"

    def test_github_copilot_conflict_without_force(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        # Plant different file at destination
        copilot_dir = project / ".github" / "copilot"
        copilot_dir.mkdir(parents=True)
        (copilot_dir / "my-skill.prompt.md").write_text("customized content", encoding="utf-8")

        result = pub.publish_one("my-skill", catalog, project, "github-copilot", False, False)
        assert result.status == "conflict"

    def test_github_copilot_dry_run(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(pub, "LIBRARY", lib)
        catalog = self._make_catalog(lib)
        project = tmp_path / "myproject"
        project.mkdir()

        result = pub.publish_one("my-skill", catalog, project, "github-copilot", False, True)
        assert "dry-run" in result.status
        assert not (project / ".github" / "copilot" / "my-skill.prompt.md").exists()


# ── convert_for_copilot ───────────────────────────────────────────────────────

class TestConvertForCopilot:
    def _make_skill_file(self, tmp_path: Path, content: str) -> Path:
        f = tmp_path / "SKILL.md"
        f.write_text(content, encoding="utf-8")
        return f

    def test_skill_gets_mode_ask(self, tmp_path):
        src = self._make_skill_file(tmp_path, "---\nname: Test\ndescription: A test skill\n---\nBody text")
        entry = {"name": "Test", "description": "A test skill"}
        result = pub.convert_for_copilot(src, "test-skill", entry, "skill")
        assert "mode: ask" in result
        assert "Body text" in result

    def test_skill_description_from_entry(self, tmp_path):
        src = self._make_skill_file(tmp_path, "---\nname: Test\ndescription: old desc\n---\nBody")
        entry = {"description": "new description from catalog"}
        result = pub.convert_for_copilot(src, "test-skill", entry, "skill")
        assert "new description from catalog" in result

    def test_agent_gets_model_and_tools(self, tmp_path):
        src = self._make_skill_file(tmp_path,
            "---\nname: Agent\ndescription: An agent\nmodel: gpt-4\ntools: [Read, Write]\n---\nAgent body")
        entry = {"description": "An agent"}
        result = pub.convert_for_copilot(src, "my-agent", entry, "agent")
        assert "model: gpt-4" in result
        assert "tools:" in result
        assert "Agent body" in result

    def test_skill_no_frontmatter(self, tmp_path):
        src = self._make_skill_file(tmp_path, "Just plain content without frontmatter")
        entry = {"description": "Plain skill"}
        result = pub.convert_for_copilot(src, "plain-skill", entry, "skill")
        assert "mode: ask" in result
        assert "Just plain content without frontmatter" in result
