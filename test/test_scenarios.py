#!/usr/bin/env python3
"""
Scenario (use case) tests for Agent Hub Index.

Each test class represents a realistic user workflow, told as a narrative.
These tests verify that the system works correctly from the user's perspective.

Scenarios:
  1. Nhà phát triển mới setup project TypeScript
  2. Chu trình import skill đầy đủ
  3. Xử lý conflict khi publish
  4. Phát hiện và cập nhật skill bị lỗi thời
  5. Xuất bản nhiều skill từ collection theo thứ tự
  6. Kiểm tra tính toàn vẹn thư viện thực tế
  7. Dự án ROS2/Robotics detection
  8. Librarian workflow: gợi ý → publish → verify
  9. Stack publish đầy đủ và kiểm tra manifest
 10. Rollback-safety: validate trước khi publish
"""

import json
import sys
import yaml
from pathlib import Path

import pytest

from conftest import (
    load_script, HubFixture, INDEX_ROOT, SCRIPTS_DIR,
    make_skill_content, make_agent_content,
)

bc  = load_script("build-catalog")
vl  = load_script("validate")
pub = load_script("publish-to-project")
imp = load_script("import-skill")
cu  = load_script("check-updates")
dp  = load_script("detect-project")


# ── Helpers ───────────────────────────────────────────────────────────────────

def installed_skill_ids(project: Path) -> set:
    skills_dir = project / ".claude" / "skills"
    return {d.name for d in skills_dir.iterdir() if d.is_dir()} if skills_dir.exists() else set()


def get_manifest(project: Path) -> dict:
    f = project / "library-manifest.yaml"
    return yaml.safe_load(f.read_text(encoding="utf-8")) if f.exists() else {}


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 1: Nhà phát triển mới setup project TypeScript
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_NewTypescriptProjectSetup:
    """
    Kịch bản: Một developer mở project TypeScript/React mới.
    System tự phát hiện loại project → gợi ý stack phù hợp →
    developer publish stack → tất cả skills được cài đặt.
    """

    def test_step1_detect_project_type(self, hub: HubFixture, tmp_path):
        """Bước 1: detect-project nhận diện đây là TypeScript/React project."""
        project = tmp_path / "my-react-app"
        project.mkdir()
        (project / "package.json").write_text(
            '{"name": "my-app", "dependencies": {"react": "^18.2.0", "next": "^14.0.0"}}',
            encoding="utf-8"
        )
        (project / "tsconfig.json").write_text('{"compilerOptions": {}}', encoding="utf-8")

        signals = dp.extract_signals(project)
        assert "typescript" in signals["technologies"] or "javascript" in signals["technologies"]
        assert "web-frontend" in signals["domains"]

    def test_step2_find_matching_stack(self, hub: HubFixture, tmp_path):
        """Bước 2: Catalog tìm ra stack phù hợp nhất là test-web-stack."""
        project = tmp_path / "my-react-app"
        project.mkdir()
        (project / "package.json").write_text(
            '{"dependencies": {"react": "^18", "next": "^14"}}',
            encoding="utf-8"
        )
        (project / "tsconfig.json").write_text('{}', encoding="utf-8")

        signals = dp.extract_signals(project)
        catalog = hub.get_catalog()
        stack_id, score = dp.find_best_stack(catalog, signals)

        assert stack_id == "web-fullstack-typescript"
        assert score >= 20.0, f"Score too low: {score}"

    def test_step3_publish_stack_to_project(self, hub: HubFixture, monkeypatch, tmp_path):
        """Bước 3: Publish stack → tất cả core và workflow skills được cài."""
        project = tmp_path / "my-react-app"
        project.mkdir()
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

        installed = installed_skill_ids(project)
        # Core skills must all be present
        assert "api-design" in installed
        assert "frontend-patterns" in installed
        assert "security-scan" in installed
        # Workflow skills also present
        assert "brainstorming" in installed
        assert "code-review" in installed

    def test_step4_manifest_records_stack_name(self, hub: HubFixture, monkeypatch, tmp_path):
        """Bước 4: Manifest ghi lại stack đã được dùng."""
        project = tmp_path / "my-react-app"
        project.mkdir()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

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

        manifest = get_manifest(project)
        assert manifest.get("stack") == "web-fullstack-typescript"

    def test_full_scenario_end_to_end(self, hub: HubFixture, monkeypatch, tmp_path):
        """Full scenario: detect → match → publish → validate manifest integrity."""
        # Setup project
        project = tmp_path / "my-react-app"
        project.mkdir()
        (project / "package.json").write_text(
            '{"dependencies": {"react": "^18"}}', encoding="utf-8"
        )
        (project / "tsconfig.json").write_text('{}', encoding="utf-8")

        # Detect
        signals = dp.extract_signals(project)
        catalog = hub.get_catalog()
        stack_id, _ = dp.find_best_stack(catalog, signals)
        assert stack_id is not None

        # Publish
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        pub.publish(
            project=project,
            skill_ids=[],
            stack_id=stack_id,
            collection_id=None,
            platform="claude-code",
            force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        # Verify
        manifest = get_manifest(project)
        assert manifest["schema_version"] == 1
        assert len(manifest["entries"]) >= 3
        for entry in manifest["entries"]:
            src_file = hub.library / "skills" / entry["id"] / "SKILL.md"
            if src_file.exists():
                assert entry["checksum"] == pub.sha256_file(src_file)


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 2: Chu trình import skill đầy đủ
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_SkillImportLifecycle:
    """
    Kịch bản: Curator phát hiện một skill tốt trong source project,
    muốn thêm vào library. Quy trình: import → rebuild catalog →
    validate → publish → kiểm tra trong project.
    """

    def test_full_import_lifecycle(self, tmp_path, monkeypatch):
        """Import một skill mới từ đầu đến khi cài vào project."""
        # Setup source project
        source = tmp_path / "superpowers"
        skill_dir = source / "skills" / "my-new-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: My New Skill\ndescription: Use when you need something new\n---\n"
            "# My New Skill\n\nThis is a brand new skill.\n",
            encoding="utf-8"
        )

        # Setup empty library
        lib = tmp_path / "library"
        for d in ("skills", "provenance", "enrichment", "agents", "collections", "stacks"):
            (lib / d).mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(imp, "SOURCES", {
            "superpowers": {
                "root": source,
                "skill_patterns": ["skills/{name}/SKILL.md"],
                "agent_patterns": [],
                "stability": "stable",
            }
        })

        # Step 1: Import
        exit_code = imp.import_entry(
            source_name="superpowers",
            skill_name="my-new-skill",
            entry_type="skill",
            dry_run=False,
            force=False,
            verbose=False,
        )
        assert exit_code == 0
        assert (lib / "skills" / "my-new-skill" / "SKILL.md").exists()

        # Step 2: Rebuild catalog
        import unittest.mock as mock
        with mock.patch.object(bc, "LIBRARY", lib), \
             mock.patch.object(bc, "CATALOG_FILE", lib / "catalog.json"), \
             mock.patch.object(bc, "KEYWORDS_FILE", SCRIPTS_DIR / "domain-keywords.json"):
            kw = bc.load_keywords()
            bc.DOMAIN_KEYWORDS = kw.get("DOMAIN_KEYWORDS", {})
            bc.TECH_KEYWORDS   = kw.get("TECH_KEYWORDS", {})
            bc.PHASE_KEYWORDS  = kw.get("PHASE_KEYWORDS", {})
            bc.build_catalog()

        # Step 3: Validate
        monkeypatch.setattr(vl, "LIBRARY", lib)
        monkeypatch.setattr(vl, "CATALOG_FILE", lib / "catalog.json")
        exit_code = vl.run_validation(strict=False, output_json=False)
        assert exit_code == 0

        # Step 4: Publish to project
        project = tmp_path / "my-project"
        project.mkdir()
        monkeypatch.setattr(pub, "LIBRARY", lib)
        monkeypatch.setattr(pub, "CATALOG_FILE", lib / "catalog.json")
        catalog = json.loads((lib / "catalog.json").read_text(encoding="utf-8"))
        pub.publish(
            project=project,
            skill_ids=["my-new-skill"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        # Step 5: Verify
        assert (project / ".claude" / "skills" / "my-new-skill" / "SKILL.md").exists()
        manifest = get_manifest(project)
        ids = {e["id"] for e in manifest.get("entries", [])}
        assert "my-new-skill" in ids

    def test_import_preserves_provenance_metadata(self, tmp_path, monkeypatch):
        """Provenance file phải ghi đúng source project và hash."""
        source = tmp_path / "superpowers"
        skill_dir = source / "skills" / "traced-skill"
        skill_dir.mkdir(parents=True)
        content = "---\nname: Traced Skill\ndescription: Use when testing provenance\n---\nBody"
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

        lib = tmp_path / "library"
        for d in ("skills", "provenance", "enrichment", "agents"):
            (lib / d).mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(imp, "LIBRARY", lib)
        monkeypatch.setattr(imp, "SOURCES", {
            "superpowers": {
                "root": source,
                "skill_patterns": ["skills/{name}/SKILL.md"],
                "agent_patterns": [],
                "stability": "stable",
            }
        })

        imp.import_entry("superpowers", "traced-skill", "skill", False, False, False)

        prov = yaml.safe_load((lib / "provenance" / "traced-skill.yaml").read_text())
        assert prov["source_project"] == "superpowers"
        assert prov["source_path"] == "skills/traced-skill/SKILL.md"
        assert prov["original_hash"].startswith("sha256:")
        assert prov["customized"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 3: Xử lý conflict khi publish
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_ConflictResolution:
    """
    Kịch bản: Developer đã customize một skill trong project của mình.
    Khi publish lại từ library, hệ thống phát hiện conflict và yêu cầu
    --force để overwrite, giúp tránh mất customization vô tình.
    """

    def test_scenario_conflict_detected_without_force(self, hub: HubFixture, monkeypatch):
        """Bước 1: Publish ban đầu thành công."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )
        assert (project / ".claude" / "skills" / "brainstorming" / "SKILL.md").exists()

        # Developer customizes the skill locally
        custom_file = project / ".claude" / "skills" / "brainstorming" / "SKILL.md"
        custom_file.write_text("## My Custom Version\n\nI added this myself.", encoding="utf-8")

        # Attempt to publish again without --force
        result = pub.publish_one(
            skill_id="brainstorming",
            catalog=hub.get_catalog(),
            project=project,
            platform="claude-code",
            force=False,
            dry_run=False,
        )
        assert result.status == "conflict"
        # Custom content should be preserved
        assert "My Custom Version" in custom_file.read_text()

    def test_scenario_force_overwrites_custom_version(self, hub: HubFixture, monkeypatch):
        """Bước 2: Dùng --force để overwrite, file được cập nhật từ library."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        # Customize
        custom_file = project / ".claude" / "skills" / "brainstorming" / "SKILL.md"
        custom_file.write_text("## My Custom Version", encoding="utf-8")

        # Force overwrite
        result = pub.publish_one(
            skill_id="brainstorming",
            catalog=hub.get_catalog(),
            project=project,
            platform="claude-code",
            force=True,
            dry_run=False,
        )
        assert result.status == "updated"

        # Content should now match library
        lib_content = (hub.library / "skills" / "brainstorming" / "SKILL.md").read_text()
        installed_content = custom_file.read_text()
        assert installed_content == lib_content

    def test_scenario_dry_run_shows_conflict_without_modifying(self, hub: HubFixture, monkeypatch):
        """Dry-run phải báo cáo conflict nhưng không thay đổi file."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=True,
        )

        custom_file = project / ".claude" / "skills" / "brainstorming" / "SKILL.md"
        custom_content = "## Precious Custom Work"
        custom_file.write_text(custom_content, encoding="utf-8")

        # Dry-run
        result = pub.publish_one(
            "brainstorming", hub.get_catalog(), project, "claude-code", False, True
        )
        assert "dry-run" in result.status or result.status == "conflict"
        assert custom_file.read_text() == custom_content


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 4: Phát hiện và cập nhật skill bị lỗi thời
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_StaleSkillUpdate:
    """
    Kịch bản: Library được cập nhật sau khi developer đã publish.
    System phát hiện skill cũ và thông báo cần update.
    Developer chạy lại publish để nhận bản mới.
    """

    def test_full_update_cycle(self, hub: HubFixture, monkeypatch, capsys):
        """Chu trình đầy đủ: publish → cập nhật library → phát hiện → republish."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(cu, "LIBRARY", hub.library)

        # Bước 1: Publish ban đầu
        pub.publish(
            project=project,
            skill_ids=["brainstorming", "systematic-debugging"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )
        original_manifest = get_manifest(project)

        # Bước 2: Library curator cập nhật skill
        hub.modify_skill("brainstorming", "\n## New section added by curator\n")
        hub.modify_skill("systematic-debugging", "\n## Updated debugging steps\n")

        # Bước 3: check-updates phát hiện 2 updates
        original_argv = sys.argv
        sys.argv = ["check-updates.py", str(project)]
        try:
            cu.main()
        finally:
            sys.argv = original_argv

        notification = capsys.readouterr().out
        assert "2" in notification
        assert "update" in notification.lower()

        # Bước 4: Republish với force
        pub.publish(
            project=project,
            skill_ids=["brainstorming", "systematic-debugging"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=True, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        # Bước 5: Verify hashes updated
        new_manifest = get_manifest(project)
        for entry in new_manifest["entries"]:
            sid = entry["id"]
            src = hub.library / "skills" / sid / "SKILL.md"
            if src.exists():
                assert entry["checksum"] == pub.sha256_file(src), f"Hash stale for {sid}"

    def test_only_modified_skills_detected(self, hub: HubFixture, monkeypatch):
        """Chỉ skill bị thay đổi mới được phát hiện là stale."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming", "code-review", "tdd-workflow"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        # Only modify one skill
        hub.modify_skill("code-review", "\n## Updated review checklist\n")

        manifest = get_manifest(project)
        stale = []
        for entry in manifest["entries"]:
            sid = entry["id"]
            src = hub.library / "skills" / sid / "SKILL.md"
            if src.exists() and pub.sha256_file(src) != entry["checksum"]:
                stale.append(sid)

        assert stale == ["code-review"], f"Expected only code-review stale, got: {stale}"


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 5: Collection theo đúng thứ tự seq
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_CollectionOrdering:
    """
    Kịch bản: Collection có thứ tự seq cụ thể (workflow).
    Hệ thống phải publish đúng thứ tự, không bỏ sót, không lặp.
    """

    def test_collection_skills_all_installed(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        monkeypatch.setattr(pub, "CATALOG_FILE", hub.library / "catalog.json")

        pub.publish(
            project=project,
            skill_ids=[],
            stack_id=None,
            collection_id="debugging-deep-dive",
            platform="claude-code",
            force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        installed = installed_skill_ids(project)
        assert "brainstorming" in installed
        assert "systematic-debugging" in installed
        assert "code-review" in installed

    def test_collection_resolve_order(self, hub: HubFixture):
        """resolve_collection phải trả về danh sách theo seq tăng dần."""
        catalog = hub.get_catalog()
        ids = pub.resolve_collection("debugging-deep-dive", catalog)
        assert ids == ["brainstorming", "systematic-debugging", "code-review"]

    def test_collection_no_duplicates_when_combined_with_skills(self, hub: HubFixture, monkeypatch):
        """Không được install trùng skill nếu vừa trong collection vừa trong --skills."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],          # also in quick-debug collection
            stack_id=None,
            collection_id="debugging-deep-dive",
            platform="claude-code",
            force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        manifest = get_manifest(project)
        ids = [e["id"] for e in manifest.get("entries", [])]
        assert ids.count("brainstorming") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 6: Kiểm tra tính toàn vẹn thư viện thực tế
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_RealLibraryIntegrity:
    """
    Kịch bản: Kiểm tra thư viện thực tế (không dùng fixture).
    Mọi skill, agent, collection, stack phải valid.
    """

    def test_real_library_validate_passes(self, real_library_path):
        """validate.py phải pass hoàn toàn trên library thực."""
        import unittest.mock as mock
        with mock.patch.object(vl, "LIBRARY", real_library_path), \
             mock.patch.object(vl, "CATALOG_FILE", real_library_path / "catalog.json"):
            exit_code = vl.run_validation(strict=False, output_json=False)
        assert exit_code == 0

    def test_real_catalog_has_minimum_entries(self, real_library_path):
        """Library thực phải có ít nhất 40 entries."""
        catalog_file = real_library_path / "catalog.json"
        assert catalog_file.exists()
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        assert catalog["totalEntries"] >= 40, f"Too few entries: {catalog['totalEntries']}"

    def test_real_catalog_no_duplicate_ids(self, real_library_path):
        """Không được có duplicate ID trong catalog thực."""
        catalog = json.loads((real_library_path / "catalog.json").read_text())
        ids = [e["id"] for e in catalog["entries"]]
        seen = {}
        duplicates = []
        for eid in ids:
            seen[eid] = seen.get(eid, 0) + 1
            if seen[eid] == 2:
                duplicates.append(eid)
        assert not duplicates, f"Duplicate IDs found: {duplicates}"

    def test_real_catalog_all_paths_exist(self, real_library_path):
        """Mỗi entry trong catalog phải có file thực tế."""
        catalog = json.loads((real_library_path / "catalog.json").read_text())
        missing = []
        for entry in catalog["entries"]:
            path = real_library_path / entry["path"]
            if not path.exists():
                missing.append(f"{entry['id']}: {entry['path']}")
        assert not missing, f"Missing files:\n" + "\n".join(missing)

    def test_real_stacks_reference_valid_skills(self, real_library_path):
        """Mọi skill ID trong stacks phải tồn tại trong catalog."""
        catalog = json.loads((real_library_path / "catalog.json").read_text())
        catalog_ids = {e["id"] for e in catalog["entries"]}
        errors = []
        for stack in catalog.get("stacks", []):
            for section in ("core_skills", "workflow_skills"):
                for skill in stack.get(section, []):
                    sid = skill.get("id") if isinstance(skill, dict) else None
                    if sid and sid not in catalog_ids:
                        errors.append(f"Stack '{stack['id']}' refs unknown '{sid}'")
        assert not errors, "\n".join(errors)

    def test_real_collections_reference_valid_skills(self, real_library_path):
        """Mọi skill ID trong collections phải tồn tại trong catalog."""
        catalog = json.loads((real_library_path / "catalog.json").read_text())
        catalog_ids = {e["id"] for e in catalog["entries"]}
        errors = []
        for coll in catalog.get("collections", []):
            for entry in coll.get("entries", []):
                sid = entry.get("id") if isinstance(entry, dict) else None
                if sid and sid not in catalog_ids:
                    errors.append(f"Collection '{coll['id']}' refs unknown '{sid}'")
        assert not errors, "\n".join(errors)


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 7: Robotics project detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_RoboticsProjectDetection:
    """
    Kịch bản: Developer mở ROS2 project (có package.xml và CMakeLists.txt).
    System nhận diện là robotics + ROS2 project.
    """

    def test_ros2_signals_detected(self, tmp_path):
        project = tmp_path / "ros2_workspace" / "my_package"
        project.mkdir(parents=True)
        (project / "package.xml").write_text(
            '<?xml version="1.0"?>\n<package format="3"><name>my_pkg</name></package>',
            encoding="utf-8"
        )
        (project / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.8)\nfind_package(ament_cmake REQUIRED)\n"
            "find_package(rclcpp REQUIRED)\n",
            encoding="utf-8"
        )

        signals = dp.extract_signals(project)
        assert "ros2" in signals["technologies"]
        assert "robotics" in signals["domains"]
        assert "cpp" in signals["technologies"]

    def test_pytorch_ml_signals_detected(self, tmp_path):
        project = tmp_path / "ml-project"
        project.mkdir()
        (project / "requirements.txt").write_text(
            "torch==2.1.0\ntorchvision==0.16.0\ntransformers==4.35.0\n",
            encoding="utf-8"
        )
        (project / "pyproject.toml").write_text(
            '[tool.poetry.dependencies]\ntorch = "^2.1"\n',
            encoding="utf-8"
        )

        signals = dp.extract_signals(project)
        assert "pytorch" in signals["technologies"]
        assert "ai-ml" in signals["domains"]
        assert "python" in signals["technologies"]


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 8: Stack và Collection publishing — manifest integrity
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_ManifestIntegrity:
    """
    Kịch bản: Sau khi publish, manifest phải chứa đúng thông tin
    cho tất cả skills — checksums, types, sources.
    """

    def test_manifest_has_correct_schema_version(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )
        manifest = get_manifest(project)
        assert manifest["schema_version"] == 1

    def test_manifest_entries_have_required_fields(self, hub: HubFixture, monkeypatch):
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)
        pub.publish(
            project=project,
            skill_ids=["brainstorming", "code-review"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )
        manifest = get_manifest(project)
        required = {"id", "type", "checksum", "published_at", "version"}
        for entry in manifest["entries"]:
            missing = required - set(entry.keys())
            assert not missing, f"Entry '{entry['id']}' missing: {missing}"

    def test_incremental_publish_preserves_existing_entries(self, hub: HubFixture, monkeypatch):
        """
        Publish skill A, sau đó publish skill B.
        Manifest phải chứa cả A và B, không xóa A.
        """
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        pub.publish(
            project=project,
            skill_ids=["code-review"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        manifest = get_manifest(project)
        ids = {e["id"] for e in manifest["entries"]}
        assert "brainstorming" in ids
        assert "code-review" in ids

    def test_manifest_updated_at_changes_on_republish(self, hub: HubFixture, monkeypatch):
        """updated_at trong manifest phải đổi sau mỗi lần publish."""
        import time
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )
        first_ts = get_manifest(project).get("updated_at")

        time.sleep(0.01)
        hub.modify_skill("brainstorming")
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=True, dry_run=False,
            no_librarian=True, no_manifest=False,
        )
        second_ts = get_manifest(project).get("updated_at")

        assert first_ts != second_ts


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 9: Validate-before-publish safety
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_ValidateBeforePublish:
    """
    Kịch bản: Trước khi publish cho team, curator chạy validate để
    chắc chắn library không có lỗi. Sau đó publish.
    """

    def test_validate_then_publish_workflow(self, hub: HubFixture, monkeypatch):
        """Validate pass → publish → verify."""
        monkeypatch.setattr(vl, "LIBRARY", hub.library)
        monkeypatch.setattr(vl, "CATALOG_FILE", hub.library / "catalog.json")
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        # Step 1: Validate
        exit_code = vl.run_validation(strict=False, output_json=False)
        assert exit_code == 0, "Library phải valid trước khi publish"

        # Step 2: Publish
        project = hub.make_project()
        pub.publish(
            project=project,
            skill_ids=HubFixture.SKILL_IDS[:3],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=False,
        )

        # Step 3: Verify
        installed = installed_skill_ids(project)
        for sid in HubFixture.SKILL_IDS[:3]:
            assert sid in installed

    def test_corrupt_library_fails_validation(self, hub: HubFixture, monkeypatch):
        """Library bị hỏng (thiếu SKILL.md) phải fail validate."""
        # Remove a SKILL.md to simulate corruption
        broken_skill = hub.library / "skills" / "brainstorming"
        (broken_skill / "SKILL.md").unlink()

        monkeypatch.setattr(vl, "LIBRARY", hub.library)
        monkeypatch.setattr(vl, "CATALOG_FILE", hub.library / "catalog.json")
        result = vl.check_skill_has_md()
        assert result.status == "fail"


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO 10: Multi-platform publishing
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario_MultiPlatform:
    """
    Kịch bản: Team dùng cả Claude Code và OpenCode.
    Skills phải publish vào đúng thư mục theo từng platform.
    """

    def test_claude_code_and_opencode_same_project(self, hub: HubFixture, monkeypatch):
        """Publish vào cùng project, hai platform khác nhau."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        # Publish to claude-code
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=True,
        )

        # Publish to opencode
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="opencode", force=False, dry_run=False,
            no_librarian=True, no_manifest=True,
        )

        # Both should exist
        assert (project / ".claude" / "skills" / "brainstorming" / "SKILL.md").exists()
        assert (project / ".opencode" / "skills" / "brainstorming" / "SKILL.md").exists()

    def test_platform_dirs_are_independent(self, hub: HubFixture, monkeypatch):
        """Files trong .claude/ và .opencode/ phải độc lập, không ảnh hưởng nhau."""
        project = hub.make_project()
        monkeypatch.setattr(pub, "LIBRARY", hub.library)

        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="claude-code", force=False, dry_run=False,
            no_librarian=True, no_manifest=True,
        )

        # Customize the claude-code version
        cc_file = project / ".claude" / "skills" / "brainstorming" / "SKILL.md"
        cc_file.write_text("Claude-specific customization", encoding="utf-8")

        # Publish to opencode — should not be affected
        pub.publish(
            project=project,
            skill_ids=["brainstorming"],
            stack_id=None, collection_id=None,
            platform="opencode", force=False, dry_run=False,
            no_librarian=True, no_manifest=True,
        )

        # Claude-code file still has customization
        assert cc_file.read_text() == "Claude-specific customization"
        # OpenCode file has library content
        oc_file = project / ".opencode" / "skills" / "brainstorming" / "SKILL.md"
        lib_content = (hub.library / "skills" / "brainstorming" / "SKILL.md").read_text()
        assert oc_file.read_text() == lib_content
