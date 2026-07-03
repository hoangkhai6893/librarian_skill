#!/usr/bin/env python3
"""
System integration tests for Agent Hub Index.

Tests full pipelines end-to-end:
  - Catalog build pipeline
  - Publish pipeline (skill/stack/collection)
  - Update detection cycle
  - Concurrent lock protection
  - CLI smoke tests (subprocess)
"""

import json
import subprocess
import sys
import threading
import time
import hashlib
import yaml
from pathlib import Path

import pytest

from conftest import load_script, HubFixture, INDEX_ROOT, SCRIPTS_DIR

bc = load_script("build-catalog")
vl = load_script("validate")
pub = load_script("publish-to-project")
imp = load_script("import-skill")
cu = load_script("check-updates")
dp = load_script("detect-project")


# ── Helpers ───────────────────────────────────────────────────────────────────


def published_skills(project: Path, platform: str = "claude-code") -> set:
    """Return set of skill IDs installed in project."""
    skills_dir = project / ".claude" / "skills"
    if not skills_dir.exists():
        return set()
    return {d.name for d in skills_dir.iterdir() if d.is_dir()}


def read_manifest(project: Path) -> dict:
    f = project / "library-manifest.yaml"
    return yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CATALOG BUILD PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestCatalogBuildPipeline:
    """Test the full build-catalog → validate pipeline."""

    def test_catalog_built_with_all_skills(self, hub: HubFixture):
        catalog = hub.get_catalog()
        assert catalog["totalEntries"] == len(HubFixture.SKILL_IDS) + len(
            HubFixture.AGENT_IDS
        )

    def test_catalog_has_required_top_level_keys(self, hub: HubFixture):
        catalog = hub.get_catalog()
        for key in (
            "version",
            "builtAt",
            "totalEntries",
            "entries",
            "collections",
            "stacks",
        ):
            assert key in catalog, f"Missing key: {key}"

    def test_every_skill_id_in_catalog(self, hub: HubFixture):
        ids = hub.catalog_ids
        for sid in HubFixture.SKILL_IDS:
            assert sid in ids, f"Skill '{sid}' missing from catalog"

    def test_every_agent_id_in_catalog(self, hub: HubFixture):
        ids = hub.catalog_ids
        for aid in HubFixture.AGENT_IDS:
            assert aid in ids, f"Agent '{aid}' missing from catalog"

    def test_catalog_entries_have_required_fields(self, hub: HubFixture):
        required = {
            "id",
            "name",
            "type",
            "description",
            "domains",
            "technologies",
            "phases",
            "cost",
            "stability",
            "complexity",
            "usage_pattern",
            "path",
            "keywords",
        }
        for entry in hub.get_catalog()["entries"]:
            missing = required - set(entry.keys())
            assert not missing, f"Entry '{entry['id']}' missing fields: {missing}"

    def test_catalog_collection_included(self, hub: HubFixture):
        catalog = hub.get_catalog()
        coll_ids = {c["id"] for c in catalog.get("collections", [])}
        assert "debugging-deep-dive" in coll_ids

    def test_catalog_stack_included(self, hub: HubFixture):
        catalog = hub.get_catalog()
        stack_ids = {s["id"] for s in catalog.get("stacks", [])}
        assert "web-fullstack-typescript" in stack_ids

    def test_rebuild_is_idempotent(self, hub: HubFixture):
        """Building catalog twice produces same result."""
        catalog1 = hub.get_catalog()
        hub.build_catalog()
        catalog2 = hub.get_catalog()
        assert catalog1["totalEntries"] == catalog2["totalEntries"]
        assert {e["id"] for e in catalog1["entries"]} == {
            e["id"] for e in catalog2["entries"]
        }

    def test_cost_field_valid_values(self, hub: HubFixture):
        valid_costs = {"light", "medium", "heavy"}
        for entry in hub.get_catalog()["entries"]:
            assert entry["cost"] in valid_costs, (
                f"'{entry['id']}' has invalid cost: {entry['cost']}"
            )

    def test_stability_field_valid_values(self, hub: HubFixture):
        valid = {"stable", "experimental", "beta"}
        for entry in hub.get_catalog()["entries"]:
            assert entry["stability"] in valid


# ═══════════════════════════════════════════════════════════════════════════════
# 2. VALIDATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidationPipeline:
    """Test the validate pipeline against the hub library."""

    def test_valid_library_passes_all_checks(self, hub: HubFixture, monkeypatch):
        monkeypatch.setattr(vl, "LIBRARY", hub.library)
        monkeypatch.setattr(vl, "CATALOG_FILE", hub.library / "catalog.json")
        exit_code = vl.run_validation(strict=False, output_json=False)
        assert exit_code == 0

    def test_validation_json_report_structure(
        self, hub: HubFixture, monkeypatch, capsys
    ):
        monkeypatch.setattr(vl, "LIBRARY", hub.library)
        monkeypatch.setattr(vl, "CATALOG_FILE", hub.library / "catalog.json")
        vl.run_validation(strict=False, output_json=True)
        captured = capsys.readouterr()
        report = json.loads(captured.out)

        assert report["status"] in ("pass", "warn", "fail")
        assert "summary" in report
        assert "results" in report
        assert report["summary"]["fail"] == 0

    def test_missing_skill_md_detected(self, hub: HubFixture, monkeypatch, tmp_path):
        # Add an orphan dir with no SKILL.md
        orphan = hub.library / "skills" / "orphan-skill"
        orphan.mkdir(parents=True)
        # Rebuild catalog (orphan won't be in it since it has no SKILL.md)
        monkeypatch.setattr(vl, "LIBRARY", hub.library)
        monkeypatch.setattr(vl, "CATALOG_FILE", hub.library / "catalog.json")
        result = vl.check_skill_has_md()
        assert result.status == "fail"
        assert any("orphan-skill" in issue for issue in result.issues)

    def test_catalog_out_of_sync_detected(self, hub: HubFixture, monkeypatch):
        """Adding a skill dir without rebuilding catalog should fail CATALOG_COMPLETE."""
        new_skill = hub.library / "skills" / "new-uncataloged-skill"
        new_skill.mkdir(parents=True)
        (new_skill / "SKILL.md").write_text(
            "---\nname: New Skill\ndescription: Use when testing\n---\nBody",
            encoding="utf-8",
        )
        monkeypatch.setattr(vl, "LIBRARY", hub.library)
        monkeypatch.setattr(vl, "CATALOG_FILE", hub.library / "catalog.json")
        result = vl.check_catalog_complete(hub.get_catalog())
        assert result.status == "fail"
        assert any("new-uncataloged-skill" in issue for issue in result.issues)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PUBLISH PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestPublishPipeline:
    """Test full publish workflows."""

    def _publish(self, hub: HubFixture, project: Path, **kwargs):
        catalog = hub.get_catalog()
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(pub, "LIBRARY", hub.library)
            mp.setattr(pub, "CATALOG_FILE", hub.library / "catalog.json")
        return pub.publish(project=project, catalog=catalog, **kwargs)

    def test_publish_single_skill(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        catalog = hub.get_catalog()

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        assert (project / ".claude" / "skills" / "brainstorming").is_dir()
        assert (project / ".claude" / "skills" / "brainstorming" / "SKILL.md").exists()

    def test_publish_creates_manifest(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming", "code-review"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        manifest = read_manifest(project)
        assert manifest["schema_version"] == 1
        manifest_ids = {e["id"] for e in manifest.get("entries", [])}
        assert "brainstorming" in manifest_ids
        assert "code-review" in manifest_ids

    def test_publish_stack(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(pub, "CATALOG_FILE", hub.library / "catalog.json")

        pub.publish(
            project=project,
            skill_ids=[],
            stack_id="web-fullstack-typescript",
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        installed = published_skills(project)
        expected = {
            "api-design",
            "frontend-patterns",
            "security-scan",
            "brainstorming",
            "code-review",
        }
        assert expected.issubset(installed), f"Missing: {expected - installed}"

    def test_publish_collection(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(pub, "CATALOG_FILE", hub.library / "catalog.json")

        pub.publish(
            project=project,
            skill_ids=[],
            stack_id=None,
            collection_id="debugging-deep-dive",
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        installed = published_skills(project)
        assert "brainstorming" in installed
        assert "systematic-debugging" in installed
        assert "code-review" in installed

    def test_dry_run_writes_nothing(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming", "code-review"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=True,
            no_librarian=True,
            no_manifest=True,
        )

        assert not published_skills(project)
        assert not (project / "library-manifest.yaml").exists()

    def test_manifest_checksums_match_files(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming", "systematic-debugging"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        manifest = read_manifest(project)
        for entry in manifest["entries"]:
            sid = entry["id"]
            stored_hash = entry["checksum"]
            src_file = hub.library / "skills" / sid / "SKILL.md"
            actual_hash = pub.sha256_file(src_file)
            assert stored_hash == actual_hash, f"Hash mismatch for '{sid}'"

    def test_publish_opencode_platform(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None,
            collection_id=None,
            platform="opencode",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=True,
        )

        assert (project / ".opencode" / "skills" / "brainstorming").is_dir()
        assert not (project / ".claude" / "skills" / "brainstorming").exists()

    def test_no_duplicate_skills_when_stack_and_skills_overlap(
        self, hub: HubFixture, monkeypatch
    ):
        """If --skills includes an ID already in --stack, it should only be published once."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],  # also in test-web-stack
            stack_id="web-fullstack-typescript",
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        manifest = read_manifest(project)
        ids = [e["id"] for e in manifest.get("entries", [])]
        assert ids.count("brainstorming") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. UPDATE DETECTION CYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestUpdateDetectionCycle:
    """Test the full publish → modify → check-updates → republish cycle."""

    def test_no_updates_when_library_unchanged(
        self, hub: HubFixture, monkeypatch, capsys
    ):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(cu, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        # Simulate check-updates
        manifest_file = project / "library-manifest.yaml"
        manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
        updates = []
        for entry in manifest["entries"]:
            sid = entry.get("id")
            stored_hash = entry.get("checksum")
            src_file = hub.library / "skills" / sid / "SKILL.md"
            if src_file.exists() and pub.sha256_file(src_file) != stored_hash:
                updates.append(sid)

        assert updates == [], f"Unexpected updates: {updates}"

    def test_update_detected_after_library_change(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(cu, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        # Modify skill in library (simulate upstream update)
        hub.modify_skill("brainstorming")

        manifest_file = project / "library-manifest.yaml"
        manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
        updates = []
        for entry in manifest["entries"]:
            sid = entry.get("id")
            stored_hash = entry.get("checksum")
            src_file = hub.library / "skills" / sid / "SKILL.md"
            if src_file.exists() and pub.sha256_file(src_file) != stored_hash:
                updates.append(sid)

        assert "brainstorming" in updates

    def test_republish_after_update_clears_stale_hash(
        self, hub: HubFixture, monkeypatch
    ):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        # Initial publish
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        # Modify library skill
        hub.modify_skill("brainstorming")

        # Re-publish with force
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=True,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        # Now hashes should match
        manifest = read_manifest(project)
        for entry in manifest["entries"]:
            if entry["id"] == "brainstorming":
                src_file = hub.library / "skills" / "brainstorming" / "SKILL.md"
                assert entry["checksum"] == pub.sha256_file(src_file)

    def test_check_updates_script_integration(
        self, hub: HubFixture, monkeypatch, capsys
    ):
        """Run check_updates.main() directly to verify notification output."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(cu, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming", "code-review"],
            stack_id=None,
            collection_id=None,
            platform="claude-code",
            force=False,
            dry_run=False,
            no_librarian=True,
            no_manifest=False,
        )

        # Modify one skill
        hub.modify_skill("brainstorming")

        # Run check-updates
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            cu.main()
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "brainstorming" in captured.out
        assert "update" in captured.out.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. IMPORT PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestImportPipeline:
    """Test import → build catalog → validate pipeline."""

    def _make_sources(self, tmp_path: Path) -> tuple[Path, Path]:
        """Return (source_root, library_path)."""
        source = tmp_path / "superpowers"
        skill_dir = source / "skills" / "new-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: New Skill\ndescription: Use when testing new imports\n---\nBody",
            encoding="utf-8",
        )

        lib = tmp_path / "library"
        (lib / "skills").mkdir(parents=True)
        (lib / "provenance").mkdir(parents=True)
        (lib / "enrichment").mkdir(parents=True)
        (lib / "agents").mkdir(parents=True)
        return source, lib

    def test_import_then_build_includes_new_skill(self, tmp_path, monkeypatch):
        source, lib = self._make_sources(tmp_path)
        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(
            imp,
            "SOURCES",
            {
                "superpowers": {
                    "root": source,
                    "skill_patterns": ["skills/{name}/SKILL.md"],
                    "agent_patterns": [],
                    "stability": "stable",
                }
            },
        )

        exit_code = imp.import_entry(
            "superpowers", "new-skill", "skill", False, False, False
        )
        assert exit_code == 0

        # Build catalog
        import unittest.mock as mock

        with (
            mock.patch.object(bc, "LIBRARY", lib),
            mock.patch.object(bc, "CATALOG_FILE", lib / "catalog.json"),
            mock.patch.object(
                bc, "KEYWORDS_FILE", SCRIPTS_DIR / "domain-keywords.json"
            ),
        ):
            kw = bc.load_keywords()
            bc.DOMAIN_KEYWORDS = kw.get("DOMAIN_KEYWORDS", {})
            bc.TECH_KEYWORDS = kw.get("TECH_KEYWORDS", {})
            bc.PHASE_KEYWORDS = kw.get("PHASE_KEYWORDS", {})
            bc.build_catalog()

        catalog = json.loads((lib / "catalog.json").read_text(encoding="utf-8"))
        ids = {e["id"] for e in catalog["entries"]}
        assert "new-skill" in ids

    def test_import_creates_provenance_and_enrichment(self, tmp_path, monkeypatch):
        source, lib = self._make_sources(tmp_path)
        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(
            imp,
            "SOURCES",
            {
                "superpowers": {
                    "root": source,
                    "skill_patterns": ["skills/{name}/SKILL.md"],
                    "agent_patterns": [],
                    "stability": "stable",
                }
            },
        )

        imp.import_entry("superpowers", "new-skill", "skill", False, False, False)

        assert (lib / "provenance" / "new-skill.yaml").exists()
        assert (lib / "enrichment" / "new-skill.yaml").exists()

        prov = yaml.safe_load((lib / "provenance" / "new-skill.yaml").read_text())
        assert prov["source_project"] == "superpowers"
        assert prov["original_hash"].startswith("sha256:")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CONCURRENT LOCK PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestConcurrentLockProtection:
    """Verify the file lock prevents concurrent publish operations."""

    def test_lock_acquired_and_released(self, hub: HubFixture, monkeypatch, tmp_path):
        project = hub.make_project()
        lock_file = project / ".claude" / ".publish.lock"

        with pub.project_lock(project):
            assert lock_file.exists()

    def test_concurrent_lock_raises_system_exit(self, hub: HubFixture, tmp_path):
        """
        Acquire the lock in the main thread, then verify a second call
        in a thread raises SystemExit (LOCK_NB → BlockingIOError → sys.exit(1)).
        """
        project = hub.make_project()
        errors = []

        with pub.project_lock(project):

            def try_lock():
                try:
                    with pub.project_lock(project):
                        pass
                except SystemExit as e:
                    errors.append(e.code)

            t = threading.Thread(target=try_lock)
            t.start()
            t.join(timeout=3)

        assert 1 in errors, "Expected SystemExit(1) from concurrent lock attempt"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. PROJECT DETECTION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectDetectionPipeline:
    """Test detect-project against hub catalog."""

    def test_typescript_project_matches_web_stack(self, hub: HubFixture, tmp_path):
        project = tmp_path / "ts-project"
        project.mkdir()
        (project / "package.json").write_text(
            '{"dependencies": {"react": "^18"}}', encoding="utf-8"
        )
        (project / "tsconfig.json").write_text("{}", encoding="utf-8")

        signals = dp.extract_signals(project)
        catalog = hub.get_catalog()
        stack_id, score = dp.find_best_stack(catalog, signals)

        assert stack_id == "web-fullstack-typescript"
        assert score > 20.0

    def test_go_project_no_matching_stack(self, hub: HubFixture, tmp_path):
        project = tmp_path / "go-project"
        project.mkdir()
        (project / "go.mod").write_text("module myapp\n", encoding="utf-8")

        signals = dp.extract_signals(project)
        catalog = hub.get_catalog()
        # hub has only test-web-stack, which doesn't match Go
        stack_id, score = dp.find_best_stack(catalog, signals)
        # Either no match or low score
        assert stack_id is None or score < 50

    def test_empty_project_no_suggestion(self, hub: HubFixture, tmp_path):
        project = tmp_path / "empty-project"
        project.mkdir()

        signals = dp.extract_signals(project)
        assert not signals["technologies"]
        assert not signals["domains"]


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CLI SMOKE TESTS (subprocess)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCLISmoke:
    """Verify each CLI script starts correctly and handles --help."""

    SCRIPTS = [
        "build-catalog.py",
        "validate.py",
        "import-skill.py",
        "publish-to-project.py",
        "detect-project.py",
        "check-updates.py",
    ]

    @pytest.mark.parametrize("script", SCRIPTS)
    def test_help_flag_exits_0(self, script):
        # Some scripts don't support --help (detect-project, check-updates)
        if script in ("detect-project.py", "check-updates.py"):
            pytest.skip(f"{script} does not support --help")

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"{script} --help failed:\n{result.stderr}"
        assert "usage" in result.stdout.lower() or "Usage" in result.stdout

    def test_build_catalog_against_real_library(self):
        """build-catalog.py should succeed on the real library."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "build-catalog.py")],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(INDEX_ROOT),
        )
        assert result.returncode == 0, f"build-catalog failed:\n{result.stderr}"
        assert "catalog.json written" in result.stdout

    def test_validate_against_real_library(self):
        """validate.py should pass on the real library."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate.py")],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(INDEX_ROOT),
        )
        assert result.returncode == 0, (
            f"validate failed:\n{result.stderr}\n{result.stdout}"
        )

    def test_detect_project_against_empty_dir(self, tmp_path):
        """detect-project.py on empty dir should exit 0 and surface that the library exists."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "detect-project.py"), str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Agent Hub" in result.stdout

    def test_check_updates_no_manifest_exits_0(self, tmp_path):
        """check-updates.py with no manifest should exit 0 silently."""
        project = tmp_path / "project"
        project.mkdir()
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check-updates.py"), str(project)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_validate_json_output(self):
        """validate.py --json should produce valid JSON."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(INDEX_ROOT),
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["status"] == "pass"
        assert report["summary"]["fail"] == 0

    def test_publish_dry_run_no_project_dir(self, tmp_path):
        """publish-to-project.py --dry-run on missing project should fail gracefully."""
        ghost = tmp_path / "nonexistent-project"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "publish-to-project.py"),
                "--project",
                str(ghost),
                "--skills",
                "brainstorming",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(INDEX_ROOT),
        )
        # Should exit non-zero (project not found)
        assert result.returncode != 0
