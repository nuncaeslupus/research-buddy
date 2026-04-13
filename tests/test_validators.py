"""Tests for new semantic validators."""

from __future__ import annotations

from research_docs.validator import validate


class TestReferenceOrdering:
    def test_valid_references(self, starter_doc: dict) -> None:
        # Research tab -> Methodology section
        starter_doc["tabs"][1]["sections"]["Methodology"]["blocks"].append(
            {
                "type": "references",
                "items": [
                    {"version": "v1.1", "text": "Ref 1.1"},
                    {"version": "v1.0", "text": "Ref 1.0"},
                ],
            }
        )
        issues = validate(starter_doc)
        assert not any("REFERENCE ORDER" in i for i in issues)

    def test_invalid_references_version(self, starter_doc: dict) -> None:
        # Research tab -> Methodology section
        starter_doc["tabs"][1]["sections"]["Methodology"]["blocks"].append(
            {
                "type": "references",
                "items": [
                    {"version": "v1.0", "text": "Ref 1.0"},
                    {"version": "v1.1", "text": "Ref 1.1"},
                ],
            }
        )
        issues = validate(starter_doc)
        assert any("REFERENCE ORDER" in i for i in issues)

    def test_invalid_references_date(self, starter_doc: dict) -> None:
        # Research tab -> Methodology section
        starter_doc["tabs"][1]["sections"]["Methodology"]["blocks"].append(
            {
                "type": "references",
                "items": [
                    {"date": "2026-03-01", "text": "Old"},
                    {"date": "2026-04-01", "text": "New"},
                ],
            }
        )
        issues = validate(starter_doc)
        assert any("REFERENCE ORDER" in i for i in issues)

    def test_month_year_ordering(self, starter_doc: dict) -> None:
        # Research tab -> Methodology section
        starter_doc["tabs"][1]["sections"]["Methodology"]["blocks"].append(
            {
                "type": "references",
                "items": [
                    {"date": "April 2026", "text": "New"},
                    {"date": "March 2026", "text": "Old"},
                ],
            }
        )
        issues = validate(starter_doc)
        assert not any("REFERENCE ORDER" in i for i in issues)

    def test_invalid_month_year_ordering(self, starter_doc: dict) -> None:
        # Research tab -> Methodology section
        starter_doc["tabs"][1]["sections"]["Methodology"]["blocks"].append(
            {
                "type": "references",
                "items": [
                    {"date": "March 2026", "text": "Old"},
                    {"date": "April 2026", "text": "New"},
                ],
            }
        )
        issues = validate(starter_doc)
        assert any("REFERENCE ORDER" in i for i in issues)

    def test_non_string_date_ordering(self, starter_doc: dict) -> None:
        # Research tab -> Methodology section
        starter_doc["tabs"][1]["sections"]["Methodology"]["blocks"].append(
            {
                "type": "references",
                "items": [
                    {"date": 2026, "text": "Invalid type"},
                    {"date": "March 2026", "text": "Old"},
                ],
            }
        )
        # Should not crash, and should fail the descending check since (0,0,0) < (2026,3,0)
        issues = validate(starter_doc)
        assert any("REFERENCE ORDER" in i for i in issues)
