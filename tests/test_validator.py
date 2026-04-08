"""Tests for schema validation."""

from __future__ import annotations

from research_docs.validator import validate


class TestSchemaValidation:
    def test_valid_starter(self, starter_doc: dict) -> None:
        errors = validate(starter_doc)
        assert errors == []

    def test_missing_meta(self) -> None:
        errors = validate({"tabs": []})
        assert any("meta" in e for e in errors)

    def test_missing_tabs(self) -> None:
        errors = validate({"meta": {"version": "1", "date": "now"}})
        assert any("tabs" in e for e in errors)

    def test_invalid_block_type(self, starter_doc: dict) -> None:
        # Research tab -> Reasoning Journey section
        starter_doc["tabs"][1]["sections"]["Reasoning Journey"]["blocks"].append({"type": "bogus"})
        errors = validate(starter_doc)
        assert any("bogus" in e for e in errors)


class TestFullValidation:
    def test_combined(self, starter_doc: dict) -> None:
        issues = validate(starter_doc)
        assert issues == []


class TestStarterDocIntegrity:
    def test_starter_sections_and_subtitles(self, starter_doc: dict) -> None:
        # Check first tab first section
        overview = starter_doc["tabs"][0]
        # The first section title should match meta.title in init,
        # but in raw STARTER_DOCUMENT it is "Project Objective"
        first_title = next(iter(overview["sections"].keys()))
        assert overview["sections"][first_title]["subtitle"] == "Primary goals and project scope"

        # Check research tab sections
        research = starter_doc["tabs"][1]
        assert "Methodology" in research["sections"]
        assert research["sections"]["Methodology"]["subtitle"] == (
            "Standards for sourcing and validating information"
        )

        assert "Reasoning Journey" in research["sections"]
        assert research["sections"]["Reasoning Journey"]["subtitle"] == "How We Arrived Here"

        assert "Research Tracker" in research["sections"]
        assert research["sections"]["Research Tracker"]["subtitle"] == "Living Status Board"

        # Check design tab
        design = starter_doc["tabs"][3]
        assert "System Architecture" in design["sections"]
        assert (
            design["sections"]["System Architecture"]["subtitle"]
            == "Component interaction and data flow"
        )

        # Check implementation tab
        impl = starter_doc["tabs"][4]
        assert "Build Guide" in impl["sections"]
        assert impl["sections"]["Build Guide"]["subtitle"] == "Steps to deploy the current design"
