#!/usr/bin/env python3
"""Unit tests for build-catalog.py"""

import yaml
from pathlib import Path
from conftest import load_script

bc = load_script("build-catalog")


# ── parse_frontmatter ─────────────────────────────────────────────────────────

class TestParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        f = tmp_path / "skill.md"
        f.write_text("---\nname: Test\ndescription: Use when testing\n---\nBody text", encoding="utf-8")
        fm, body = bc.parse_frontmatter(f)
        assert fm["name"] == "Test"
        assert fm["description"] == "Use when testing"
        assert "Body text" in body

    def test_no_frontmatter(self, tmp_path):
        f = tmp_path / "skill.md"
        f.write_text("Just body text", encoding="utf-8")
        fm, body = bc.parse_frontmatter(f)
        assert fm == {}
        assert "Just body text" in body

    def test_empty_frontmatter(self, tmp_path):
        f = tmp_path / "skill.md"
        f.write_text("---\n---\nBody", encoding="utf-8")
        fm, body = bc.parse_frontmatter(f)
        assert fm == {}
        assert "Body" in body


# ── infer_cost ────────────────────────────────────────────────────────────────

class TestInferCost:
    def test_light_file(self, tmp_path):
        f = tmp_path / "small.md"
        f.write_bytes(b"x" * 100)
        assert bc.infer_cost(f) == "light"

    def test_medium_file(self, tmp_path):
        f = tmp_path / "medium.md"
        f.write_bytes(b"x" * 10_000)
        assert bc.infer_cost(f) == "medium"

    def test_heavy_file(self, tmp_path):
        f = tmp_path / "heavy.md"
        f.write_bytes(b"x" * 25_000)
        assert bc.infer_cost(f) == "heavy"

    def test_boundary_light_medium(self, tmp_path):
        f = tmp_path / "boundary.md"
        f.write_bytes(b"x" * 4_999)
        assert bc.infer_cost(f) == "light"
        f.write_bytes(b"x" * 5_000)
        assert bc.infer_cost(f) == "medium"

    def test_boundary_medium_heavy(self, tmp_path):
        f = tmp_path / "boundary.md"
        f.write_bytes(b"x" * 19_999)
        assert bc.infer_cost(f) == "medium"
        f.write_bytes(b"x" * 20_000)
        assert bc.infer_cost(f) == "heavy"


# ── infer_stability ───────────────────────────────────────────────────────────

class TestInferStability:
    def test_stable_by_default(self):
        assert bc.infer_stability({}, "Normal content", "stable") == "stable"

    def test_experimental_keyword(self):
        assert bc.infer_stability({}, "this is experimental", "stable") == "experimental"

    def test_wip_keyword(self):
        assert bc.infer_stability({}, "WIP: not ready", "stable") == "experimental"

    def test_draft_keyword(self):
        assert bc.infer_stability({}, "draft version", "stable") == "experimental"

    def test_beta_keyword(self):
        assert bc.infer_stability({}, "beta release", "stable") == "beta"

    def test_source_stability_propagated(self):
        assert bc.infer_stability({}, "clean content", "experimental") == "experimental"

    def test_experimental_overrides_source(self):
        # Body signal takes precedence over source
        assert bc.infer_stability({}, "experimental feature", "stable") == "experimental"


# ── infer_complexity ──────────────────────────────────────────────────────────

class TestInferComplexity:
    def test_intermediate_by_default(self):
        assert bc.infer_complexity({}, "Normal description") == "intermediate"

    def test_advanced(self):
        assert bc.infer_complexity({}, "Advanced techniques for expert users") == "advanced"

    def test_beginner(self):
        assert bc.infer_complexity({}, "Simple and basic introduction") == "beginner"

    def test_sophisticated_triggers_advanced(self):
        assert bc.infer_complexity({}, "sophisticated approach") == "advanced"

    def test_introductory_triggers_beginner(self):
        assert bc.infer_complexity({}, "introductory tutorial") == "beginner"


# ── infer_usage_pattern ───────────────────────────────────────────────────────

class TestInferUsagePattern:
    def test_always_on_from_preamble_tier(self):
        result = bc.infer_usage_pattern({"preamble-tier": 1}, "myskill", "body", "skill")
        assert result == "always-on"

    def test_always_on_from_preamble_tier_camel(self):
        result = bc.infer_usage_pattern({"preambleTier": 1}, "myskill", "body", "skill")
        assert result == "always-on"

    def test_before_implementation_plan(self):
        result = bc.infer_usage_pattern({}, "plan-architecture", "body", "skill")
        assert result == "before-implementation"

    def test_before_implementation_brainstorm(self):
        result = bc.infer_usage_pattern({}, "brainstorm-ideas", "body", "skill")
        assert result == "before-implementation"

    def test_after_implementation_review(self):
        result = bc.infer_usage_pattern({}, "code-review", "body", "skill")
        assert result == "after-implementation"

    def test_after_implementation_verify(self):
        result = bc.infer_usage_pattern({}, "verify-tests", "body", "skill")
        assert result == "after-implementation"

    def test_session_hook_from_body(self):
        result = bc.infer_usage_pattern({}, "myhook", "Runs at session start automatically", "skill")
        assert result == "session-hook"

    def test_on_demand_for_command_type(self):
        result = bc.infer_usage_pattern({}, "mycommand", "body", "command")
        assert result == "on-demand"

    def test_during_implementation_default(self):
        result = bc.infer_usage_pattern({}, "myskill", "body", "skill")
        assert result == "during-implementation"


# ── infer_from_text ───────────────────────────────────────────────────────────

class TestInferFromText:
    def test_empty_text(self):
        result = bc.infer_from_text("", "", "")
        assert result["domains"] == []
        assert result["technologies"] == []
        assert result["phases"] == []

    def test_returns_dict_with_required_keys(self):
        result = bc.infer_from_text("some", "text", "")
        assert set(result.keys()) == {"domains", "technologies", "phases"}

    def test_very_long_text_no_error(self):
        result = bc.infer_from_text("", "", "word " * 10_000)
        assert isinstance(result, dict)

    def test_primary_hit_beats_secondary_noise(self):
        # A single incidental body mention shouldn't tag a domain; a
        # name/description mention should, even without repetition.
        result = bc.infer_from_text("robotics helper", "Use when working with ROS2 nodes", "some unrelated body")
        assert "robotics" in result["domains"]

    def test_secondary_alone_needs_two_hits(self):
        result = bc.infer_from_text("myskill", "generic description", "mentions docker once")
        assert "devops" not in result["domains"]

    def test_capped_at_top_n(self):
        # Body mentioning many domains' keywords should still cap the result.
        noisy_body = " ".join(kw for kws in bc.DOMAIN_KEYWORDS.values() for kw in kws[:2] * 2)
        result = bc.infer_from_text("x", "y", noisy_body)
        assert len(result["domains"]) <= 4


# ── extract_relevance_keywords ────────────────────────────────────────────────

class TestExtractRelevanceKeywords:
    def test_max_60_keywords(self):
        keywords = bc.extract_relevance_keywords(
            "test skill", "testing description", "body " * 500,
            ["workflow"], ["python"], ["testing"]
        )
        assert len(keywords) <= 60

    def test_sorted_output(self):
        keywords = bc.extract_relevance_keywords(
            "test", "desc", "body", [], [], []
        )
        assert keywords == sorted(keywords)

    def test_includes_domain_labels(self):
        keywords = bc.extract_relevance_keywords(
            "test", "desc", "body", ["robotics"], [], []
        )
        assert "robotics" in keywords

    def test_includes_tech_labels(self):
        keywords = bc.extract_relevance_keywords(
            "test", "desc", "body", [], ["python"], []
        )
        assert "python" in keywords

    def test_excludes_stop_words(self):
        keywords = bc.extract_relevance_keywords(
            "the and for with", "desc", "body", [], [], []
        )
        for word in ["the", "and", "for", "with"]:
            assert word not in keywords

    def test_min_word_length_3(self):
        keywords = bc.extract_relevance_keywords(
            "ab xy z", "desc", "body", [], [], []
        )
        # Words shorter than 3 chars should not appear
        for kw in keywords:
            assert len(kw) >= 3


# ── build_entry integration ───────────────────────────────────────────────────

class TestBuildEntry:
    def _make_library(self, tmp_path: Path) -> Path:
        lib = tmp_path / "library"
        (lib / "skills" / "my-skill").mkdir(parents=True)
        (lib / "provenance").mkdir(parents=True)
        (lib / "enrichment").mkdir(parents=True)
        (lib / "skills" / "my-skill" / "SKILL.md").write_text(
            "---\nname: My Skill\ndescription: Use when testing code\n---\nBody text",
            encoding="utf-8"
        )
        return lib

    def test_build_entry_basic(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(bc, "LIBRARY", lib)
        skill_file = lib / "skills" / "my-skill" / "SKILL.md"
        entry = bc.build_entry("my-skill", "skill", skill_file)

        assert entry["id"] == "my-skill"
        assert entry["name"] == "My Skill"
        assert entry["type"] == "skill"
        assert entry["description"] == "Use when testing code"
        assert "keywords" in entry
        assert isinstance(entry["domains"], list)
        assert isinstance(entry["technologies"], list)
        assert isinstance(entry["phases"], list)

    def test_build_entry_defaults(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(bc, "LIBRARY", lib)
        skill_file = lib / "skills" / "my-skill" / "SKILL.md"
        entry = bc.build_entry("my-skill", "skill", skill_file)

        assert entry["source"] == "unknown"
        assert entry["library_version"] == "1.0"
        assert entry["cost"] in ("light", "medium", "heavy")
        assert entry["stability"] in ("stable", "experimental", "beta")

    def test_build_entry_with_provenance(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(bc, "LIBRARY", lib)
        prov_file = lib / "provenance" / "my-skill.yaml"
        prov_file.write_text(
            yaml.dump({"source_project": "superpowers", "library_version": "2.0"}),
            encoding="utf-8"
        )
        skill_file = lib / "skills" / "my-skill" / "SKILL.md"
        entry = bc.build_entry("my-skill", "skill", skill_file)

        assert entry["source"] == "superpowers"
        assert entry["library_version"] == "2.0"

    def test_build_entry_with_enrichment_override(self, tmp_path, monkeypatch):
        lib = self._make_library(tmp_path)
        monkeypatch.setattr(bc, "LIBRARY", lib)
        enrich_file = lib / "enrichment" / "my-skill.yaml"
        enrich_file.write_text(
            yaml.dump({
                "domains": ["robotics"],
                "technologies": ["cpp"],
                "complexity": "advanced",
                "usage_pattern": "always-on",
            }),
            encoding="utf-8"
        )
        skill_file = lib / "skills" / "my-skill" / "SKILL.md"
        entry = bc.build_entry("my-skill", "skill", skill_file)

        assert "robotics" in entry["domains"]
        assert "cpp" in entry["technologies"]
        assert entry["complexity"] == "advanced"
        assert entry["usage_pattern"] == "always-on"
