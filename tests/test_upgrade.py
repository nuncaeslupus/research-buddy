"""Tests for the `upgrade` command and its core logic."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research_buddy import __version__
from research_buddy.main import cmd_upgrade
from research_buddy.upgrade import stamp_format_note, upgrade_doc


class _Args:
    """Minimal argparse.Namespace substitute for cmd_upgrade."""

    def __init__(self, **kwargs: object) -> None:
        self.apply = False
        self.no_validate = False
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestUpgradeDoc:
    def test_replaces_framework(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["framework"]["about"] = "stale project text"

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert (
            upgraded["agent_guidelines"]["framework"]
            == starter_doc["agent_guidelines"]["framework"]
        )

    def test_replaces_session_protocol(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["session_protocol"] = {"custom_key": "old"}

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert (
            upgraded["agent_guidelines"]["session_protocol"]
            == starter_doc["agent_guidelines"]["session_protocol"]
        )

    def test_preserves_session_zero_note(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["session_protocol"]["session_zero"]["note"] = (
            "Initialized 2026-04-01 — do not re-run session_zero."
        )

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert (
            upgraded["agent_guidelines"]["session_protocol"]["session_zero"]["note"]
            == "Initialized 2026-04-01 — do not re-run session_zero."
        )

    def test_no_note_added_when_input_had_none(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["session_protocol"]["session_zero"].pop("note", None)

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        session_zero = upgraded["agent_guidelines"]["session_protocol"]["session_zero"]
        assert "note" not in session_zero

    def test_leaves_project_specific_untouched(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["project_specific"]["domain"] = "quant finance / ML"
        doc["agent_guidelines"]["project_specific"]["custom_rule"] = "keep me"

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        ps = upgraded["agent_guidelines"]["project_specific"]
        assert ps["domain"] == "quant finance / ML"
        assert ps["custom_rule"] == "keep me"

    def test_bumps_research_buddy_version(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["meta"]["research_buddy_version"] = "0.9.0"

        upgraded, changes, _ = upgrade_doc(doc, starter_doc, __version__)

        assert upgraded["meta"]["research_buddy_version"] == __version__
        assert any("research_buddy_version" in c for c in changes)

    def test_reports_added_and_removed_keys(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        # Remove a framework key → becomes "added" on upgrade.
        doc["agent_guidelines"]["framework"].pop("second_opinion_review", None)
        # Add a framework key that isn't in the starter → becomes "removed".
        doc["agent_guidelines"]["framework"]["project_only_rule"] = "mine"
        # Same for session_protocol.
        doc["agent_guidelines"]["session_protocol"]["custom_gate"] = "mine"

        _, _, diffs = upgrade_doc(doc, starter_doc, __version__)

        assert "second_opinion_review" in diffs["framework_added"]
        assert "project_only_rule" in diffs["framework_removed"]
        assert "custom_gate" in diffs["session_protocol_removed"]

    def test_idempotent_on_fresh_starter(self, starter_doc: dict) -> None:
        # Fresh starter already matches itself at the current version.
        upgraded, _, _ = upgrade_doc(starter_doc, starter_doc, __version__)
        assert upgraded == starter_doc

    def test_creates_agent_guidelines_when_missing(self, starter_doc: dict) -> None:
        doc = {"meta": {"version": "1.0"}, "tabs": []}

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert (
            upgraded["agent_guidelines"]["framework"]
            == starter_doc["agent_guidelines"]["framework"]
        )

    def test_tolerates_non_dict_framework(self, starter_doc: dict) -> None:
        # A malformed doc where framework is a string, not a dict, must not crash.
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["framework"] = "legacy string"

        upgraded, _, diffs = upgrade_doc(doc, starter_doc, __version__)

        assert isinstance(upgraded["agent_guidelines"]["framework"], dict)
        assert diffs["framework_removed"] == []


class TestUpgradeReorder:
    """Reorder-only changes must produce a write — `dict ==` ignores key order
    but a doc with `agent_guidelines` at the end is structurally wrong even
    when its values are correct."""

    def test_moves_agent_guidelines_to_top(self, starter_doc: dict) -> None:
        doc = {
            "meta": copy.deepcopy(starter_doc["meta"]),
            "tabs": copy.deepcopy(starter_doc["tabs"]),
            "agent_guidelines": copy.deepcopy(starter_doc["agent_guidelines"]),
        }
        assert next(iter(doc.keys())) != "agent_guidelines"  # precondition

        upgraded, changes, _ = upgrade_doc(doc, starter_doc, __version__)

        assert next(iter(upgraded.keys())) == "agent_guidelines"
        assert any("reordered" in c for c in changes)

    def test_orders_top_level_canonical(self, starter_doc: dict) -> None:
        doc = {
            "tabs": copy.deepcopy(starter_doc["tabs"]),
            "changelog": copy.deepcopy(starter_doc.get("changelog", {})),
            "meta": copy.deepcopy(starter_doc["meta"]),
            "agent_guidelines": copy.deepcopy(starter_doc["agent_guidelines"]),
        }

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert list(upgraded.keys()) == ["agent_guidelines", "meta", "tabs", "changelog"]

    def test_preserves_top_level_extras_at_end(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["custom_extension"] = {"keep": "me"}

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        keys = list(upgraded.keys())
        assert keys[: len(("agent_guidelines", "meta", "tabs", "changelog"))] == [
            "agent_guidelines",
            "meta",
            "tabs",
            "changelog",
        ]
        assert "custom_extension" in keys[4:]
        assert upgraded["custom_extension"] == {"keep": "me"}

    def test_orders_agent_guidelines_children(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        ag = doc["agent_guidelines"]
        # Reverse the children
        doc["agent_guidelines"] = {
            "project_specific": ag["project_specific"],
            "session_protocol": ag["session_protocol"],
            "framework": ag["framework"],
        }

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert list(upgraded["agent_guidelines"].keys()) == [
            "framework",
            "session_protocol",
            "project_specific",
        ]

    def test_orders_meta_keys_match_starter(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        starter_meta_keys = list(starter_doc["meta"].keys())
        # Scramble meta key order
        doc["meta"] = dict(reversed(list(doc["meta"].items())))

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert list(upgraded["meta"].keys()) == starter_meta_keys

    def test_meta_extras_preserved_at_end(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["meta"] = {"format_note": "old note", **doc["meta"]}

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        keys = list(upgraded["meta"].keys())
        canonical = list(starter_doc["meta"].keys())
        assert keys[: len(canonical)] == canonical
        assert "format_note" in keys[len(canonical) :]
        assert upgraded["meta"]["format_note"] == "old note"

    def test_orders_project_specific_keys_match_starter(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        starter_ps_keys = list(starter_doc["agent_guidelines"]["project_specific"].keys())
        # Scramble project_specific key order
        ps = doc["agent_guidelines"]["project_specific"]
        doc["agent_guidelines"]["project_specific"] = dict(reversed(list(ps.items())))

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        assert list(upgraded["agent_guidelines"]["project_specific"].keys()) == starter_ps_keys

    def test_project_specific_values_preserved_during_reorder(self, starter_doc: dict) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["agent_guidelines"]["project_specific"]["domain"] = "project domain"
        doc["agent_guidelines"]["project_specific"]["custom_field"] = "keep me"
        # Now scramble
        ps = doc["agent_guidelines"]["project_specific"]
        doc["agent_guidelines"]["project_specific"] = dict(reversed(list(ps.items())))

        upgraded, _, _ = upgrade_doc(doc, starter_doc, __version__)

        out_ps = upgraded["agent_guidelines"]["project_specific"]
        assert out_ps["domain"] == "project domain"
        assert out_ps["custom_field"] == "keep me"

    def test_reorder_only_change_triggers_write(self, tmp_project: Path) -> None:
        """Reorder-only change (no value differences) must still be detected
        as a real change — otherwise downstream files with the wrong
        structure can never be fixed by upgrade."""
        doc_path = next((tmp_project / "source").glob("*_v*.json"))
        with doc_path.open() as f:
            doc = json.load(f)
        # Move agent_guidelines to the end without touching values.
        scrambled = {
            "meta": doc["meta"],
            "tabs": doc["tabs"],
            "changelog": doc.get("changelog", {}),
            "agent_guidelines": doc["agent_guidelines"],
        }
        with doc_path.open("w") as f:
            json.dump(scrambled, f)

        result = cmd_upgrade(_Args(paths=[str(tmp_project)], apply=True))

        assert result == 0
        with doc_path.open() as f:
            written = json.load(f)
        assert next(iter(written.keys())) == "agent_guidelines"


class TestStampFormatNote:
    def test_appends_dated_entry(self) -> None:
        doc: dict = {"meta": {"version": "1.2"}}
        entry = stamp_format_note(doc, "9.9.9")

        note = doc["meta"]["format_note"]
        assert entry in note
        assert "v1.2" in note
        assert "9.9.9" in note

    def test_preserves_existing_format_note(self) -> None:
        doc: dict = {"meta": {"version": "1.2", "format_note": "prior entry."}}
        stamp_format_note(doc, "9.9.9")
        assert doc["meta"]["format_note"].startswith("prior entry.")

    def test_entries_separated_by_newline(self) -> None:
        doc: dict = {"meta": {"version": "1.2", "format_note": "prior entry."}}
        stamp_format_note(doc, "9.9.9")
        assert "\n" in doc["meta"]["format_note"]


class TestUpgradeCli:
    def _doc_path(self, project: Path) -> Path:
        return next((project / "source").glob("*_v*.json"))

    def test_dry_run_returns_1_when_stale(self, tmp_project: Path) -> None:
        doc_path = self._doc_path(tmp_project)
        with doc_path.open() as f:
            doc = json.load(f)
        doc["meta"]["research_buddy_version"] = "0.0.1"
        with doc_path.open("w") as f:
            json.dump(doc, f)
        mtime_before = doc_path.stat().st_mtime_ns

        result = cmd_upgrade(_Args(paths=[str(tmp_project)]))

        assert result == 1
        assert doc_path.stat().st_mtime_ns == mtime_before  # no write

    def test_apply_writes_and_returns_0(self, tmp_project: Path) -> None:
        doc_path = self._doc_path(tmp_project)
        with doc_path.open() as f:
            doc = json.load(f)
        doc["meta"]["research_buddy_version"] = "0.0.1"
        with doc_path.open("w") as f:
            json.dump(doc, f)

        result = cmd_upgrade(_Args(paths=[str(tmp_project)], apply=True))

        assert result == 0
        with doc_path.open() as f:
            written = json.load(f)
        assert written["meta"]["research_buddy_version"] == __version__
        assert "template refresh" in written["meta"]["format_note"]

    def test_apply_idempotent_returns_0_no_write(self, tmp_project: Path) -> None:
        doc_path = self._doc_path(tmp_project)
        # tmp_project writes the fresh starter, so rb_version already matches.
        mtime_before = doc_path.stat().st_mtime_ns

        result = cmd_upgrade(_Args(paths=[str(tmp_project)], apply=True))

        assert result == 0
        assert doc_path.stat().st_mtime_ns == mtime_before

    def test_apply_preserves_project_specific_customizations(self, tmp_project: Path) -> None:
        doc_path = self._doc_path(tmp_project)
        with doc_path.open() as f:
            doc = json.load(f)
        doc["agent_guidelines"]["project_specific"]["domain"] = "custom domain"
        doc["meta"]["research_buddy_version"] = "0.0.1"
        with doc_path.open("w") as f:
            json.dump(doc, f)

        result = cmd_upgrade(_Args(paths=[str(tmp_project)], apply=True))

        assert result == 0
        with doc_path.open() as f:
            written = json.load(f)
        assert written["agent_guidelines"]["project_specific"]["domain"] == "custom domain"

    def test_apply_reports_validation_failure(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc_path = self._doc_path(tmp_project)
        with doc_path.open() as f:
            doc = json.load(f)
        doc["meta"]["research_buddy_version"] = "0.0.1"
        with doc_path.open("w") as f:
            json.dump(doc, f)

        def fake_validate(d: dict) -> list[str]:
            return ["synthetic validation error for testing"]

        monkeypatch.setattr("research_buddy.main.validate", fake_validate)

        result = cmd_upgrade(_Args(paths=[str(tmp_project)], apply=True))

        assert result == 2

    def test_no_validate_skips_validation(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc_path = self._doc_path(tmp_project)
        with doc_path.open() as f:
            doc = json.load(f)
        doc["meta"]["research_buddy_version"] = "0.0.1"
        with doc_path.open("w") as f:
            json.dump(doc, f)

        called: list[int] = []

        def tripwire(d: dict) -> list[str]:
            called.append(1)
            return []

        monkeypatch.setattr("research_buddy.main.validate", tripwire)

        result = cmd_upgrade(_Args(paths=[str(tmp_project)], apply=True, no_validate=True))

        assert result == 0
        assert called == []

    def test_rejects_non_versioned_path(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "nothing-here"
        empty_dir.mkdir()

        # _resolve_source() on a directory with no source/ or *_v*.json returns None.
        result = cmd_upgrade(_Args(paths=[str(empty_dir)]))

        assert result == 2

    def test_uses_starter_template_loader(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: cmd_upgrade must fetch starter via _load_starter_template.

        If starter loading fails, we must exit 2 rather than crashing.
        """

        def boom() -> dict:
            raise RuntimeError("starter.json missing")

        monkeypatch.setattr("research_buddy.main._load_starter_template", boom)

        result = cmd_upgrade(_Args(paths=[str(tmp_project)]))

        assert result == 2
