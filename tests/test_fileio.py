"""Tests for `research_buddy.fileio` — shared encoding-guard + atomic-write helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_buddy.fileio import FileReadError, atomic_write, read_text_or_error


class TestReadTextOrError:
    def test_reads_valid_utf8(self, tmp_path: Path) -> None:
        p = tmp_path / "ok.md"
        p.write_text("héllo wörld — ✓\n", encoding="utf-8")
        assert read_text_or_error(p) == "héllo wörld — ✓\n"

    def test_invalid_utf8_raises_filereaderror(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.md"
        # 0xFF is never a valid UTF-8 lead byte.
        p.write_bytes(b"ok\xfftext")
        with pytest.raises(FileReadError):
            read_text_or_error(p)

    def test_error_message_names_the_file_and_encoding(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.md"
        p.write_bytes(b"\xff\xfe\x00")
        with pytest.raises(FileReadError) as exc:
            read_text_or_error(p)
        msg = str(exc.value)
        assert "bad.md" in msg
        assert "invalid UTF-8 encoding" in msg

    def test_empty_file_reads_as_empty_string(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.md"
        p.write_text("", encoding="utf-8")
        assert read_text_or_error(p) == ""


class TestAtomicWrite:
    def test_writes_content(self, tmp_path: Path) -> None:
        p = tmp_path / "out.md"
        atomic_write(p, "content\n")
        assert p.read_text(encoding="utf-8") == "content\n"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        p = tmp_path / "out.md"
        p.write_text("old\n", encoding="utf-8")
        atomic_write(p, "new\n")
        assert p.read_text(encoding="utf-8") == "new\n"

    def test_round_trips_non_ascii(self, tmp_path: Path) -> None:
        p = tmp_path / "out.md"
        atomic_write(p, "café — ✓\n")
        assert p.read_text(encoding="utf-8") == "café — ✓\n"

    def test_leaves_no_tmp_sibling_on_success(self, tmp_path: Path) -> None:
        p = tmp_path / "out.md"
        atomic_write(p, "content\n")
        assert not (tmp_path / "out.md.tmp").exists()
        # Nothing but the target should remain.
        assert [c.name for c in tmp_path.iterdir()] == ["out.md"]

    def test_cleans_up_tmp_when_rename_fails(self, tmp_path: Path, monkeypatch) -> None:
        p = tmp_path / "out.md"
        p.write_text("original\n", encoding="utf-8")

        def boom(self: Path, target: Path) -> None:
            raise OSError("rename failed")

        monkeypatch.setattr(Path, "replace", boom)
        with pytest.raises(OSError, match="rename failed"):
            atomic_write(p, "new\n")

        # The temp file written before the failed rename is cleaned up …
        assert not (tmp_path / "out.md.tmp").exists()
        # … and the original target is left untouched.
        assert p.read_text(encoding="utf-8") == "original\n"
