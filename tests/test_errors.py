"""Tests for error handling and edge cases."""

from __future__ import annotations

from research_buddy.validator import validate


def test_missing_version() -> None:
    bad_doc = {
        "meta": {"date": "April 2026", "title": "Test"},
        "tabs": [],
    }
    issues = validate(bad_doc)
    assert len(issues) > 0


def test_invalid_tab_structure() -> None:
    bad_doc = {
        "meta": {"version": "1.0", "date": "now", "title": "T", "research_buddy_version": "1.0"},
        "tabs": [{"label": "Overview", "sections": {}}],
    }
    issues = validate(bad_doc)
    assert any("id" in i.lower() for i in issues)


def test_missing_rb_version() -> None:
    doc = {
        "meta": {"version": "1.0", "date": "April 2026", "title": "T"},
        "tabs": [{"id": "overview", "label": "Overview", "sections": {}}],
    }
    issues = validate(doc)
    assert any("research_buddy_version" in i for i in issues)


def test_language_as_string_accepted() -> None:
    doc = {
        "meta": {
            "version": "1.0",
            "date": "April 2026",
            "title": "T",
            "research_buddy_version": "1.0",
            "language": "English",
        },
        "tabs": [{"id": "overview", "label": "Overview", "sections": {}}],
    }
    issues = validate(doc)
    assert not any("[meta.language]" in i for i in issues)


def test_language_as_object_accepted() -> None:
    doc = {
        "meta": {
            "version": "1.0",
            "date": "April 2026",
            "title": "T",
            "research_buddy_version": "1.0",
            "language": {"code": "es", "label": "Español"},
        },
        "tabs": [{"id": "overview", "label": "Overview", "sections": {}}],
    }
    issues = validate(doc)
    assert not any("[meta.language]" in i for i in issues)


def test_language_object_without_code_rejected() -> None:
    doc = {
        "meta": {
            "version": "1.0",
            "date": "April 2026",
            "title": "T",
            "research_buddy_version": "1.0",
            "language": {"label": "English"},
        },
        "tabs": [{"id": "overview", "label": "Overview", "sections": {}}],
    }
    issues = validate(doc)
    assert any("code" in i for i in issues)
