#!/usr/bin/env python3
"""Unit tests for detect-project.py"""

from pathlib import Path
from conftest import load_script

dp = load_script("detect-project")


# ── extract_signals ───────────────────────────────────────────────────────────

class TestExtractSignals:
    def test_empty_project_no_signals(self, tmp_path):
        signals = dp.extract_signals(tmp_path)
        assert signals["technologies"] == []
        assert signals["domains"] == []

    def test_package_json_detects_typescript(self, tmp_path):
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "typescript" in signals["technologies"] or "javascript" in signals["technologies"]

    def test_go_mod_detects_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module myapp\n", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "go" in signals["technologies"]

    def test_requirements_txt_detects_python(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "python" in signals["technologies"]

    def test_dockerfile_detects_docker_and_devops(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM ubuntu\n", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "docker" in signals["technologies"]
        assert "devops" in signals["domains"]

    def test_package_xml_detects_ros2(self, tmp_path):
        (tmp_path / "package.xml").write_text("<package/>", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "ros2" in signals["technologies"]
        assert "robotics" in signals["domains"]

    def test_content_signal_react_in_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"react": "^18.0.0"}', encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "react" in signals["technologies"]
        assert "web-frontend" in signals["domains"]

    def test_content_signal_pytorch_in_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("torch==2.0\ntorchvision\n", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "pytorch" in signals["technologies"]
        assert "ai-ml" in signals["domains"]

    def test_cmake_with_ros2_content(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("ament_cmake\nrclcpp\n", encoding="utf-8")
        signals = dp.extract_signals(tmp_path)
        assert "ros2" in signals["technologies"]
        assert "robotics" in signals["domains"]


# ── score_stack ───────────────────────────────────────────────────────────────

class TestScoreStack:
    def test_perfect_tech_match(self):
        stack = {
            "project_signals": {
                "technologies": ["python", "pytorch"],
                "domains": ["ai-ml"],
            }
        }
        signals = {"technologies": ["python", "pytorch"], "domains": ["ai-ml"]}
        score = dp.score_stack(stack, signals)
        assert score == 100.0

    def test_no_match_returns_zero(self):
        stack = {
            "project_signals": {
                "technologies": ["rust"],
                "domains": ["systems"],
            }
        }
        signals = {"technologies": ["python"], "domains": ["web-backend"]}
        score = dp.score_stack(stack, signals)
        assert score == 0.0

    def test_partial_match(self):
        stack = {
            "project_signals": {
                "technologies": ["python", "pytorch"],
                "domains": ["ai-ml"],
            }
        }
        # Only one of two technologies matched
        signals = {"technologies": ["python"], "domains": ["ai-ml"]}
        score = dp.score_stack(stack, signals)
        assert 0 < score < 100

    def test_empty_stack_signals(self):
        stack = {"project_signals": {"technologies": [], "domains": []}}
        signals = {"technologies": ["python"], "domains": ["web-backend"]}
        score = dp.score_stack(stack, signals)
        assert score == 0.0


# ── find_best_stack ───────────────────────────────────────────────────────────

class TestFindBestStack:
    def _make_catalog(self):
        return {
            "stacks": [
                {
                    "id": "ml-research-pytorch",
                    "project_signals": {
                        "technologies": ["python", "pytorch"],
                        "domains": ["ai-ml"],
                    },
                },
                {
                    "id": "web-fullstack-typescript",
                    "project_signals": {
                        "technologies": ["typescript", "react"],
                        "domains": ["web-frontend", "web-backend"],
                    },
                },
            ]
        }

    def test_no_signals_returns_none(self):
        catalog = self._make_catalog()
        stack_id, score = dp.find_best_stack(catalog, {"technologies": [], "domains": []})
        assert stack_id is None
        assert score == 0.0

    def test_matches_pytorch_stack(self):
        catalog = self._make_catalog()
        signals = {"technologies": ["python", "pytorch"], "domains": ["ai-ml"]}
        stack_id, score = dp.find_best_stack(catalog, signals)
        assert stack_id == "ml-research-pytorch"
        assert score > 20.0

    def test_matches_typescript_stack(self):
        catalog = self._make_catalog()
        signals = {"technologies": ["typescript", "react"], "domains": ["web-frontend"]}
        stack_id, score = dp.find_best_stack(catalog, signals)
        assert stack_id == "web-fullstack-typescript"
        assert score > 20.0

    def test_low_score_returns_none(self):
        catalog = self._make_catalog()
        # Only a weak partial signal
        signals = {"technologies": ["go"], "domains": []}
        stack_id, score = dp.find_best_stack(catalog, signals)
        assert stack_id is None
