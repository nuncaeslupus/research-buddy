"""Tests for schema validation."""

from __future__ import annotations

from research_docs.schema import validate, validate_links, validate_schema


class TestSchemaValidation:
    def test_valid_starter(self, starter_doc: dict) -> None:
        errors = validate_schema(starter_doc)
        assert errors == []

    def test_missing_meta(self) -> None:
        errors = validate_schema({"tabs": [], "sections": {}})
        assert any("meta" in e for e in errors)

    def test_missing_tabs(self) -> None:
        errors = validate_schema({"meta": {"version": "1", "date": "now"}, "sections": {}})
        assert any("tabs" in e for e in errors)

    def test_invalid_block_type(self, starter_doc: dict) -> None:
        starter_doc["sections"]["s1"]["blocks"].append({"type": "bogus"})
        errors = validate_schema(starter_doc)
        assert any("bogus" in e for e in errors)


class TestLinkValidation:
    def test_valid_starter(self, starter_doc: dict) -> None:
        warnings = validate_links(starter_doc)
        assert warnings == []

    def test_broken_nav_link(self, starter_doc: dict) -> None:
        starter_doc["tabs"][1]["nav"][0]["items"].append(
            {"href": "nonexistent", "label": "Bad Link"}
        )
        warnings = validate_links(starter_doc)
        assert any("BROKEN LINK" in w for w in warnings)

    def test_missing_section(self, starter_doc: dict) -> None:
        starter_doc["tabs"][1]["sections"].append("no-such-section")
        warnings = validate_links(starter_doc)
        assert any("MISSING SECTION" in w for w in warnings)

    def test_orphan_section(self, starter_doc: dict) -> None:
        starter_doc["sections"]["orphan"] = {"blocks": []}
        warnings = validate_links(starter_doc)
        assert any("ORPHAN" in w for w in warnings)

    def test_duplicate_id(self, starter_doc: dict) -> None:
        starter_doc["sections"]["s1"]["blocks"].append({"type": "h3", "id": "ov-intro", "md": "x"})
        warnings = validate_links(starter_doc)
        assert any("DUPLICATE" in w for w in warnings)


class TestFullValidation:
    def test_combined(self, starter_doc: dict) -> None:
        issues = validate(starter_doc)
        assert issues == []
