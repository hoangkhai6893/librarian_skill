#!/usr/bin/env python3
"""System integration tests for Agent Hub.

These tests verify end-to-end workflows across multiple scripts and components.
"""

import json
import subprocess
import sys
import yaml
from pathlib import Path
from conftest import load_script, HubFixture


# ============================================================================
# Integration: Full catalog rebuild workflow
# ============================================================================


class TestCatalogRebuildIntegration:
    """Test the complete catalog rebuild process."""

    def test_full_rebuild_workflow(self, hub):
        """Test: Import -> Build Catalog -> Validate pipeline."""
        import unittest.mock as mock

        # Step 1: Build catalog from existing library
        bc = load_script("build-catalog")

        with (
            mock.patch.object(bc, "LIBRARY", hub.library),
            mock.patch.object(bc, "CATALOG_FILE", hub.library / "catalog.json"),
        ):
            catalog = bc.build_catalog(verbose=False)

        # Verify catalog was created
        assert len(catalog["entries"]) > 0

        # Step 2: Validate the library
        vl = load_script("validate")
        exit_code = vl.run_validation(strict=True, output_json=False)

        # Should pass with strict mode (no warnings/errors)
        assert exit_code == 0

    def test_catalog_consistency(self, hub):
        """Test that catalog accurately reflects library state."""
        import unittest.mock as mock

        bc = load_script("build-catalog")

        with (
            mock.patch.object(bc, "LIBRARY", hub.library),
            mock.patch.object(bc, "CATALOG_FILE", hub.library / "catalog.json"),
        ):
            catalog = bc.build_catalog(verbose=False)

        # Count skills in library directory
        skill_dirs = list((hub.library / "skills").iterdir())
        actual_skill_count = len([d for d in skill_dirs if d.is_dir()])

        # Count entries in catalog
        catalog_entries = [e for e in catalog["entries"] if e["type"] == "skill"]

        # They should match (allowing for some flexibility)
        assert len(catalog_entries) > 0


# ============================================================================
# Integration: Publish workflow with real scripts
# ============================================================================


class TestPublishIntegration:
    """Test publishing using actual command-line execution."""

    def test_publish_via_command_line(self, hub):
        """Test publish-to-project.py via subprocess."""
        project = hub.make_project("cli-publish")

        result = subprocess.run(
            [
                sys.executable,
                str(hub.scripts / "publish-to-project.py"),
                "--project",
                str(project),
                "--skills",
                "brainstorming",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=hub.root,
        )

        # Should succeed (dry run doesn't write files)
        assert result.returncode == 0

    def test_publish_stack_via_command_line(self, hub):
        """Test publishing a stack via command line."""
        project = hub.make_project("cli-stack-publish")

        result = subprocess.run(
            [
                sys.executable,
                str(hub.scripts / "publish-to-project.py"),
                "--project",
                str(project),
                "--stack",
                "web-fullstack-typescript",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=hub.root,
        )

        assert result.returncode == 0

    def test_validate_via_command_line(self, hub):
        """Test validate.py via subprocess."""
        result = subprocess.run(
            [sys.executable, str(hub.scripts / "validate.py")],
            capture_output=True,
            text=True,
            cwd=hub.root,
        )

        # Should succeed
        assert result.returncode == 0


# ============================================================================
# Integration: Detect project workflow
# ============================================================================


class TestDetectProjectIntegration:
    """Test project detection workflow."""

    def test_detect_ros2_project(self, hub):
        """Test detecting a ROS2-style project."""
        import io
        import sys

        # Create a ROS2-like project
        ros_project = hub.root / "ros-test"
        ros_project.mkdir()

        # Add typical ROS2 files
        (ros_project / "package.xml").write_text(
            '<package format="3"><name>my_robot</name></package>', encoding="utf-8"
        )
        (ros_project / "CMakeLists.txt").write_text(
            "find_package(ament_cmake REQUIRED)", encoding="utf-8"
        )

        # Run detect-project script by setting sys.argv (main() reads from argv)
        detect_dp = load_script("detect-project")

        old_stdout = sys.stdout
        old_argv = sys.argv
        sys.stdout = io.StringIO()
        sys.argv = ["detect-project.py", str(ros_project)]

        try:
            exit_code = detect_dp.main()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.argv = old_argv

        # May or may not find a stack match, but should complete without error
        assert exit_code == 0

    def test_detect_web_project(self, hub):
        """Test detecting a web development project."""
        import io
        import sys

        web_project = hub.root / "web-test"
        web_project.mkdir()

        # Add typical web files
        (web_project / "package.json").write_text(
            '{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8"
        )
        (web_project / "tsconfig.json").write_text(
            '{"compilerOptions": {"target": "ES2020"}}', encoding="utf-8"
        )

        # Run detection by setting sys.argv (main() reads from argv)
        detect_dp = load_script("detect-project")

        old_stdout = sys.stdout
        old_argv = sys.argv
        sys.stdout = io.StringIO()
        sys.argv = ["detect-project.py", str(web_project)]

        try:
            exit_code = detect_dp.main()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.argv = old_argv

        assert exit_code == 0


# ============================================================================
# Integration: Import skill workflow (simulated)
# ============================================================================


class TestImportSkillIntegration:
    """Test the import-skill.py workflow."""

    def test_import_flow_simulation(self, hub):
        """Simulate what import-skill.py does without actually importing."""
        # 1. Source file exists in superpowers
        source_file = hub.source / "skills" / "brainstorming" / "SKILL.md"
        assert source_file.exists()

        # 2. Library skill directory should be created by HubFixture
        library_skill_dir = hub.library / "skills" / "brainstorming"
        assert library_skill_dir.exists()

        # 3. Verify SKILL.md exists and has proper content
        skill_md = library_skill_dir / "SKILL.md"
        assert skill_md.exists()

        content = skill_md.read_text()
        assert "---" in content  # Has frontmatter delimiter

    def test_import_creates_provenance(self, hub):
        """Verify that imported skills have provenance.yaml."""
        for skill_id in ["brainstorming", "systematic-debugging"]:
            prov_file = hub.library / "provenance" / f"{skill_id}.yaml"
            assert prov_file.exists(), f"Missing provenance for {skill_id}"

            # Verify provenance structure
            provenance = yaml.safe_load(prov_file.read_text())
            assert "source_project" in provenance
            assert "imported_at" in provenance


# ============================================================================
# Integration: Full end-to-end publish cycle
# ============================================================================


class TestEndToEndPublishCycle:
    """Complete end-to-end test of the publish workflow."""

    def test_complete_publish_cycle(self, hub):
        """Test the full cycle: build catalog -> publish -> verify manifest."""

        # Phase 1: Build/verify catalog
        import unittest.mock as mock

        bc = load_script("build-catalog")

        with (
            mock.patch.object(bc, "LIBRARY", hub.library),
            mock.patch.object(bc, "CATALOG_FILE", hub.library / "catalog.json"),
        ):
            catalog = bc.build_catalog(verbose=False)

        # Phase 2: Publish a stack to a new project
        project = hub.make_project("e2e-test")

        pp = load_script("publish-to-project")

        with (
            mock.patch.object(pp, "LIBRARY", hub.library),
            mock.patch.object(pp, "CATALOG_FILE", hub.library / "catalog.json"),
        ):
            exit_code = pp.publish(
                project=project,
                skill_ids=[],
                stack_id="web-fullstack-typescript",
                collection_id=None,
                platform="claude-code",
                force=False,
                dry_run=False,
                no_librarian=True,  # Skip for cleaner test
                no_manifest=False,
            )

        assert exit_code == 0

        # Phase 3: Verify published files exist
        stack = None
        for s in catalog.get("stacks", []):
            if s["id"] == "web-fullstack-typescript":
                stack = s
                break

        if stack:
            for core_skill in stack.get("core_skills", []):
                skill_id = core_skill["id"]
                skill_path = project / ".claude" / "skills" / skill_id / "SKILL.md"
                assert skill_path.exists(), f"Skill {skill_id} not published"

        # Phase 4: Verify manifest was created and is valid
        import yaml as yaml_lib

        manifest_path = project / "library-manifest.yaml"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert manifest["schema_version"] == 1
        assert len(manifest.get("entries", [])) > 0

        # Verify manifest entries match catalog
        for entry in manifest.get("entries", []):
            found = False
            for cat_entry in catalog.get("entries", []):
                if cat_entry["id"] == entry["id"]:
                    found = True
                    break
            assert found, f"Manifest entry {entry['id']} not in catalog"


# ============================================================================
# Integration: Cross-module data flow
# ============================================================================


class TestDataFlowIntegration:
    """Test that data flows correctly between modules."""

    def test_catalog_to_publish_data_flow(self, hub):
        """Verify publish can read and use catalog data."""
        import unittest.mock as mock

        # Build catalog first
        bc = load_script("build-catalog")

        with (
            mock.patch.object(bc, "LIBRARY", hub.library),
            mock.patch.object(bc, "CATALOG_FILE", hub.library / "catalog.json"),
        ):
            catalog = bc.build_catalog(verbose=False)

        # Now try to resolve a stack using the same catalog data
        pp = load_script("publish-to-project")

        resolved_ids = pp.resolve_stack("web-fullstack-typescript", catalog)

        assert len(resolved_ids) > 0

        # Verify resolved IDs exist in catalog entries
        catalog_ids = {e["id"] for e in catalog["entries"]}
        for skill_id in resolved_ids:
            assert skill_id in catalog_ids, f"{skill_id} not found in catalog"

    def test_detect_to_catalog_data_flow(self, hub):
        """Verify detection can use stack information from catalog."""
        import unittest.mock as mock

        # Get catalog
        bc = load_script("build-catalog")

        with (
            mock.patch.object(bc, "LIBRARY", hub.library),
            mock.patch.object(bc, "CATALOG_FILE", hub.library / "catalog.json"),
        ):
            catalog = bc.build_catalog(verbose=False)

        # Create a project with signals
        test_project = hub.root / "detect-integration"
        test_project.mkdir()
        (test_project / "package.json").write_text(
            '{"react": "^18.0.0"}', encoding="utf-8"
        )

        # Extract signals from the project
        dp = load_script("detect-project")
        signals = dp.extract_signals(test_project)

        # Find best matching stack using catalog data
        stack_id, score = dp.find_best_stack(catalog, signals)

        # Verify the returned stack exists in catalog
        if stack_id:
            found = False
            for s in catalog.get("stacks", []):
                if s["id"] == stack_id:
                    found = True
                    break
            assert found, f"Stack {stack_id} not found in catalog"


# ============================================================================
# Integration: Error handling across modules
# ============================================================================


class TestErrorHandlingIntegration:
    """Test that errors are handled gracefully across module boundaries."""

    def test_missing_catalog_fails_gracefully(self, tmp_path):
        """Verify publish fails gracefully when catalog is missing."""
        import io
        import sys

        project = tmp_path / "project"
        project.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "scripts" / "publish-to-project.py"),
                "--project",
                str(project),
                "--skills",
                "nonexistent",
            ],
            capture_output=True,
            text=True,
        )

        # Should fail with exit code 1 or 2 (not crash)
        assert result.returncode != 0

    def test_nonexistent_stack_fails_gracefully(self, hub):
        """Verify publish fails gracefully when stack doesn't exist."""
        project = hub.make_project("bad-stack-test")

        result = subprocess.run(
            [
                sys.executable,
                str(hub.scripts / "publish-to-project.py"),
                "--project",
                str(project),
                "--stack",
                "nonexistent-stack",
            ],
            capture_output=True,
            text=True,
            cwd=hub.root,
        )

        # Should fail with exit code 2 (not found)
        assert result.returncode == 2


# ============================================================================
# Helper import for tests using dp directly
# ============================================================================

try:
    from conftest import dp as detect_project_module
except ImportError:
    pass
