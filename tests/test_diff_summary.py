"""Tests for the `diff-summary` command — mechanical Turn-2 summary block."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from research_buddy.bump import bump_md_text
from research_buddy.commands._shared import _load_starter_md_text
from research_buddy.commands.init import _set_frontmatter_scalar
from research_buddy.diff_summary import (
    build_downstream_action,
    build_summary,
    has_append_only_violation,
)


def _old_source() -> str:
    text = _load_starter_md_text()
    for k, v in [
        ("agent_state", "ready"),
        ("version", "1.0"),
        ("date", "2026-05-01"),
        ("file_name", "demo"),
        ("title", "Demo"),
    ]:
        text = _set_frontmatter_scalar(text, k, v)
    text = text.replace("  domain: null", '  domain: "ML"', 1)
    text = text.replace(
        "| Q-001 | {{queue.row1.topic}} | {{queue.row1.objective}} |",
        "| Q-001 | Chunk sizing | Optimal size? |",
        1,
    )
    return text.replace(
        "### v1.0: Project initialized — {{date}}", "### v1.0: init — 2026-05-01", 1
    )


def _new_source(old: str) -> str:
    """v1.1: bump (moves Q-001 → tracker, adds session) plus a new rule + DA."""
    new, _, _ = bump_md_text(old, "Q-001", "1.1", "2026-06-01")
    rule = (
        "<!-- @rule: R-CHUNK-1 -->\n"
        '<a id="r-chunk-1"></a>\n\n'
        "**R-CHUNK-1 VALIDATED MUST.** Chunk at 512 tokens.\n\n"
    )
    new = new.replace("<!-- @end: rules -->", rule + "<!-- @end: rules -->", 1)
    da = (
        "<!-- @da: DA-Q001-1 -->\n"
        '<a id="da-q001-1"></a>\n\n'
        "**DA-Q001-1.** Fixed 1024-token chunks. Rejected in v1.1.\n\n"
    )
    return new.replace("<!-- @end: discarded -->", da + "<!-- @end: discarded -->", 1)


class TestBuildSummary:
    def test_reports_all_mechanical_changes(self) -> None:
        old = _old_source()
        new = _new_source(old)
        summary = build_summary(old, new)

        assert summary.startswith("<!-- @summary-start -->")
        assert summary.rstrip().endswith("<!-- @summary-end -->")
        assert "{{Narrative" in summary  # agent-authored part left as placeholder
        assert "Version: v1.0 → v1.1" in summary
        assert "Q-001 → tracker" in summary
        assert "+R-CHUNK-1" in summary
        assert "+DA-Q001-1" in summary
        assert "+Q-001" in summary  # session note
        assert "Append-only invariant: PASS" in summary

    def test_revised_rule_flagged(self) -> None:
        old = _new_source(_old_source())  # has R-CHUNK-1
        new = old.replace("Chunk at 512 tokens.", "Chunk at 256 tokens.", 1)
        summary = build_summary(old, new)
        assert "revised R-CHUNK-1" in summary

    def test_append_only_violation_detected(self) -> None:
        old = _new_source(_old_source())  # has DA-Q001-1
        # Remove the DA — an append-only violation.
        new = old.replace(
            "<!-- @da: DA-Q001-1 -->\n"
            '<a id="da-q001-1"></a>\n\n'
            "**DA-Q001-1.** Fixed 1024-token chunks. Rejected in v1.1.\n\n",
            "",
            1,
        )
        assert has_append_only_violation(old, new)
        assert "Append-only invariant: FAIL" in build_summary(old, new)


class TestBuildDownstreamAction:
    def test_no_new_rules_returns_none(self) -> None:
        old = _old_source()
        new, _, _ = bump_md_text(old, "Q-001", "1.1", "2026-06-01")
        assert build_downstream_action(old, new) is None

    def test_new_rule_produces_checklist(self) -> None:
        old = _old_source()
        new = _new_source(old)  # adds R-CHUNK-1
        block = build_downstream_action(old, new)
        assert block is not None
        assert "<!-- downstream-action-start -->" in block
        assert "<!-- downstream-action-end -->" in block
        assert "[R-CHUNK-1](#r-chunk-1)" in block
        assert "{{downstream files or specs to update}}" in block
        assert "v1.1" in block

    def test_revised_rule_not_included(self) -> None:
        old = _new_source(_old_source())  # already has R-CHUNK-1
        new = old.replace("Chunk at 512 tokens.", "Chunk at 256 tokens.", 1)
        assert build_downstream_action(old, new) is None

    def test_command_prints_downstream_block(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from research_buddy.commands.diff_summary import cmd_diff_summary

        old_text = _old_source()
        old = tmp_path / "demo_v1.0-source.md"
        new = tmp_path / "demo_v1.1-source.md"
        old.write_text(old_text, encoding="utf-8")
        new.write_text(_new_source(old_text), encoding="utf-8")
        cmd_diff_summary(Namespace(old=str(old), new=str(new)))
        out = capsys.readouterr().out
        assert "downstream-action-start" in out
        assert "[R-CHUNK-1](#r-chunk-1)" in out


class TestDiffSummaryCommand:
    def _args(self, old: Path, new: Path) -> Namespace:
        return Namespace(old=str(old), new=str(new))

    def test_returns_0_and_prints(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from research_buddy.commands.diff_summary import cmd_diff_summary

        old = tmp_path / "demo_v1.0-source.md"
        new = tmp_path / "demo_v1.1-source.md"
        old_text = _old_source()
        old.write_text(old_text, encoding="utf-8")
        new.write_text(_new_source(old_text), encoding="utf-8")

        rc = cmd_diff_summary(self._args(old, new))
        assert rc == 0
        assert "@summary-start" in capsys.readouterr().out

    def test_returns_1_on_violation(self, tmp_path: Path) -> None:
        from research_buddy.commands.diff_summary import cmd_diff_summary

        old_text = _new_source(_old_source())
        new_text = old_text.replace("**DA-Q001-1.**", "", 1).replace(
            "<!-- @da: DA-Q001-1 -->", "", 1
        )
        old = tmp_path / "demo_v1.1-source.md"
        new = tmp_path / "demo_v1.2-source.md"
        old.write_text(old_text, encoding="utf-8")
        new.write_text(new_text, encoding="utf-8")
        assert cmd_diff_summary(self._args(old, new)) == 1

    def test_non_md_returns_2(self, tmp_path: Path) -> None:
        from research_buddy.commands.diff_summary import cmd_diff_summary

        j = tmp_path / "x.json"
        j.write_text("{}", encoding="utf-8")
        md = tmp_path / "y.md"
        md.write_text(_old_source(), encoding="utf-8")
        assert cmd_diff_summary(self._args(j, md)) == 2
