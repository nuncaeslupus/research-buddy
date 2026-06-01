"""Tests for the `locate` command — find the live `@end: <anchor>` marker."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from research_buddy.commands._shared import _load_starter_md_text
from research_buddy.commands.locate import _normalize_anchor, cmd_locate, find_end_marker


class TestNormalizeAnchor:
    def test_variants(self) -> None:
        assert _normalize_anchor("rules") == "rules"
        assert _normalize_anchor("@end: rules") == "rules"
        assert _normalize_anchor("<!-- @end: rules -->") == "rules"
        assert _normalize_anchor("@anchor: framework.core") == "framework.core"


class TestFindEndMarker:
    def test_finds_only_live_full_line_marker(self) -> None:
        text = (
            "intro mentions `<!-- @end: rules -->` inline, not a real marker\n"
            "```\n<!-- @end: rules -->\n```\n"  # fenced — must be skipped
            "real content\n"
            "<!-- @end: rules -->\n"  # the live marker
        )
        hits = find_end_marker(text.splitlines(), "rules")
        assert hits == [5]  # 0-based index of the final, full-line, unfenced marker

    def test_starter_has_unique_live_marker(self) -> None:
        lines = _load_starter_md_text().splitlines()
        for anchor in ("rules", "discarded", "sessions", "framework.reference", "queue"):
            assert len(find_end_marker(lines, anchor)) == 1


class TestLocateCommand:
    def _args(self, path: Path, anchor: str, context: int = 2) -> Namespace:
        return Namespace(path=str(path), anchor=anchor, context=context)

    def test_prints_marker_and_returns_0(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        src = tmp_path / "demo.md"
        src.write_text(_load_starter_md_text(), encoding="utf-8")
        rc = cmd_locate(self._args(src, "rules"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "<!-- @end: rules -->" in out
        assert "→" in out  # the marker line is flagged

    def test_unknown_anchor_returns_2(self, tmp_path: Path) -> None:
        src = tmp_path / "demo.md"
        src.write_text(_load_starter_md_text(), encoding="utf-8")
        assert cmd_locate(self._args(src, "nope")) == 2

    def test_non_md_returns_2(self, tmp_path: Path) -> None:
        j = tmp_path / "x.json"
        j.write_text("{}", encoding="utf-8")
        assert cmd_locate(self._args(j, "rules")) == 2

    def test_missing_file_returns_2(self, tmp_path: Path) -> None:
        assert cmd_locate(self._args(tmp_path / "nope.md", "rules")) == 2


class TestLocateViaMain:
    def test_dispatch(self, tmp_path: Path) -> None:
        import sys
        from unittest.mock import patch

        from research_buddy.main import main

        src = tmp_path / "demo.md"
        src.write_text(_load_starter_md_text(), encoding="utf-8")
        argv = ["research-buddy", "locate", str(src), "@end: sessions"]
        with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
