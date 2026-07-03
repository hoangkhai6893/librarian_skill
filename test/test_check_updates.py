#!/usr/bin/env python3
"""Unit tests for check-updates.py"""

import hashlib
import yaml
from pathlib import Path
from conftest import load_script

cu = load_script("check-updates")


# ── sha256_file ───────────────────────────────────────────────────────────────

class TestSha256File:
    def test_prefix_format(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"content")
        result = cu.sha256_file(f)
        assert result.startswith("sha256:")

    def test_deterministic(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"content")
        assert cu.sha256_file(f) == cu.sha256_file(f)

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"aaa")
        f2.write_bytes(b"bbb")
        assert cu.sha256_file(f1) != cu.sha256_file(f2)


# ── main (integration) ────────────────────────────────────────────────────────

class TestMain:
    def _make_library(self, tmp_path: Path) -> Path:
        lib = tmp_path / "library"
        (lib / "skills" / "my-skill").mkdir(parents=True)
        skill_file = lib / "skills" / "my-skill" / "SKILL.md"
        skill_file.write_text("skill content", encoding="utf-8")
        return lib

    def _make_manifest(self, project: Path, entries: list) -> None:
        manifest = {"schema_version": 1, "entries": entries}
        (project / "library-manifest.yaml").write_text(
            yaml.dump(manifest), encoding="utf-8"
        )

    def test_no_manifest_returns_0(self, tmp_path):
        import sys
        project = tmp_path / "project"
        project.mkdir()
        # Temporarily patch sys.argv
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            exit_code = cu.main()
            assert exit_code == 0
        finally:
            sys.argv = original_argv

    def test_up_to_date_no_output(self, tmp_path, monkeypatch, capsys):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(cu, "LIBRARY", lib)

        project = tmp_path / "project"
        project.mkdir()

        skill_file = lib / "skills" / "my-skill" / "SKILL.md"
        current_hash = cu.sha256_file(skill_file)
        self._make_manifest(project, [
            {"id": "my-skill", "type": "skill", "checksum": current_hash}
        ])

        import sys
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            cu.main()
            captured = capsys.readouterr()
            assert captured.out == ""
        finally:
            sys.argv = original_argv

    def test_stale_skill_prints_notification(self, tmp_path, monkeypatch, capsys):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(cu, "LIBRARY", lib)

        project = tmp_path / "project"
        project.mkdir()

        # Store an old/wrong hash
        self._make_manifest(project, [
            {"id": "my-skill", "type": "skill", "checksum": "sha256:oldhashvalue"}
        ])

        import sys
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            cu.main()
            captured = capsys.readouterr()
            assert "my-skill" in captured.out
            assert "update" in captured.out.lower()
        finally:
            sys.argv = original_argv

    def test_missing_library_skill_skipped_silently(self, tmp_path, monkeypatch, capsys):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(cu, "LIBRARY", lib)

        project = tmp_path / "project"
        project.mkdir()

        # Reference a skill that doesn't exist in library
        self._make_manifest(project, [
            {"id": "ghost-skill", "type": "skill", "checksum": "sha256:anything"}
        ])

        import sys
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            cu.main()
            captured = capsys.readouterr()
            assert captured.out == ""
        finally:
            sys.argv = original_argv

    def test_multiple_updates_reported(self, tmp_path, monkeypatch, capsys):
        lib = self._make_library(tmp_path)
        # Create a second skill
        (lib / "skills" / "skill-two").mkdir(parents=True)
        (lib / "skills" / "skill-two" / "SKILL.md").write_text("skill two content", encoding="utf-8")
        monkeypatch.setattr(cu, "LIBRARY", lib)

        project = tmp_path / "project"
        project.mkdir()

        self._make_manifest(project, [
            {"id": "my-skill", "type": "skill", "checksum": "sha256:old1"},
            {"id": "skill-two", "type": "skill", "checksum": "sha256:old2"},
        ])

        import sys
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            cu.main()
            captured = capsys.readouterr()
            assert "2" in captured.out
        finally:
            sys.argv = original_argv
