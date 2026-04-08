"""Test cases for error handling and validation."""

from __future__ import annotations

from research_docs.validator import validate


def test_missing_version() -> None:
    # metadata is missing 'version'
    bad_doc = {
        "meta": {"date": "April 2026", "title": "Test"},
        "tabs": [],
    }
    issues = validate(bad_doc)
    assert len(issues) > 0


def test_invalid_tab_structure() -> None:
    # tab is missing 'id'
    bad_doc = {
        "meta": {"version": "1.0", "date": "now", "title": "T"},
        "tabs": [{"label": "Overview", "sections": {}}],
    }
    issues = validate(bad_doc)
    assert any("id" in i.lower() for i in issues)
