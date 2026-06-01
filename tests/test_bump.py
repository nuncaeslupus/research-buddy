"""Tests for the `bump` command — mechanical Turn-2 edits for a queue item.

`bump` takes a v2 source + a Q-NNN ID and emits the next version with the
boilerplate done (frontmatter, queue→tracker move, session/changelog/references
stubs) and `{{placeholders}}` for the agent. The headline guarantee is that
`--apply` output passes `validate_md` against the input as `--prior`.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from research_buddy.bump import (
    BumpError,
    append_tracker_row,
    next_minor_version,
    pop_queue_row,
)
from research_buddy.commands._shared import _load_starter_md_text
from research_buddy.commands.init import _set_frontmatter_scalar
from research_buddy.validator_md import validate_md


def _make_source(tmp_path: Path, version: str = "1.0") -> Path:
    """Write a minimally-filled, validate-clean v2 source file with one open
    queue row (Q-001) and return its path."""
    text = _load_starter_md_text()
    text = _set_frontmatter_scalar(text, "agent_state", "ready")
    text = _set_frontmatter_scalar(text, "version", version)
    text = _set_frontmatter_scalar(text, "date", "2026-05-01")
    text = _set_frontmatter_scalar(text, "file_name", "demo")
    text = _set_frontmatter_scalar(text, "title", "Demo")
    # Nested frontmatter + body placeholders the validator/bump care about.
    text = text.replace("  domain: null", '  domain: "Test domain"', 1)
    text = text.replace(
        "| Q-001 | {{queue.row1.topic}} | {{queue.row1.objective}} |",
        "| Q-001 | Chunk sizing | What is the optimal chunk size? |",
        1,
    )
    text = text.replace(
        "### v1.0: Project initialized — {{date}}",
        "### v1.0: Project initialized — 2026-05-01",
        1,
    )
    src = tmp_path / f"demo_v{version}-source.md"
    src.write_text(text, encoding="utf-8")
    return src


def _bump_args(path: Path, queue_id: str, **kw: object) -> Namespace:
    base = {"apply": False, "force": False, "no_validate": False}
    base.update(kw)
    return Namespace(path=str(path), queue_id=queue_id, **base)


class TestNextMinorVersion:
    def test_simple_bump(self) -> None:
        assert next_minor_version("1.0") == "1.1"
        assert next_minor_version("2.5") == "2.6"

    def test_drops_patch_component(self) -> None:
        assert next_minor_version("1.0.3") == "1.1"

    def test_major_only(self) -> None:
        assert next_minor_version("3") == "3.1"

    def test_unparseable_raises(self) -> None:
        with pytest.raises(BumpError):
            next_minor_version("nope")


class TestTableHelpers:
    def test_pop_queue_row_returns_topic_and_removes(self) -> None:
        body = (
            "\n| ID | Topic | Objective |\n|----|----|----|\n"
            "| Q-001 | Alpha | qa |\n| Q-002 | Beta | qb |\n"
        )
        new_body, topic = pop_queue_row(body, "Q-002")
        assert topic == "Beta"
        assert "Q-002" not in new_body
        assert "Q-001" in new_body

    def test_pop_queue_row_skips_comment_examples(self) -> None:
        body = "\n| ID | Topic |\n|----|----|\n| Q-001 | Real |\n<!--\n| Q-EX1 | Example |\n-->\n"
        new_body, topic = pop_queue_row(body, "Q-001")
        assert topic == "Real"
        # The example row inside the comment is untouched.
        assert "Q-EX1" in new_body

    def test_pop_queue_row_unknown_raises(self) -> None:
        body = "\n| ID | Topic |\n|----|----|\n| Q-001 | Real |\n"
        with pytest.raises(BumpError):
            pop_queue_row(body, "Q-099")

    def test_append_tracker_row_after_last_row(self) -> None:
        body = "\n| ID | T | F | V |\n|--|--|--|--|\n| T-000 | init | done | v1.0 |\n\n"
        out = append_tracker_row(body, "| Q-001 | x | y | v1.1 |")
        lines = [ln for ln in out.splitlines() if ln.strip().startswith("|")]
        assert lines[-1] == "| Q-001 | x | y | v1.1 |"


class TestBumpCommand:
    def test_dry_run_writes_nothing(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from research_buddy.commands.bump import cmd_bump

        src = _make_source(tmp_path)
        rc = cmd_bump(_bump_args(src, "Q-001"))
        assert rc == 0
        assert not (tmp_path / "demo_v1.1-source.md").exists()
        out = capsys.readouterr().out
        assert "dry-run" in out
        assert "Chunk sizing" in out  # topic surfaced

    def test_apply_writes_validate_clean_next_version(self, tmp_path: Path) -> None:
        from research_buddy.commands.bump import cmd_bump

        src = _make_source(tmp_path)
        rc = cmd_bump(_bump_args(src, "Q-001", apply=True))
        assert rc == 0

        out_path = tmp_path / "demo_v1.1-source.md"
        assert out_path.is_file()

        # The headline guarantee: the bumped file validates against its prior.
        issues = validate_md(out_path, prior=src)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == [], f"unexpected validation errors: {errors}"

        new_text = out_path.read_text(encoding="utf-8")
        assert 'version: "1.1"' in new_text
        assert "<!-- @session: Q-001 -->" in new_text
        assert '<a id="q-001"></a>' in new_text
        assert "### v1.1:" in new_text  # changelog
        assert "### v1.1 —" in new_text  # references
        # Q-001 left the queue and entered the tracker.
        from research_buddy.bump import _get_section_body

        assert "Q-001" not in _get_section_body(new_text, "queue")
        assert "Q-001" in _get_section_body(new_text, "tracker")

    def test_unknown_queue_id_returns_2(self, tmp_path: Path) -> None:
        from research_buddy.commands.bump import cmd_bump

        src = _make_source(tmp_path)
        assert cmd_bump(_bump_args(src, "Q-099", apply=True)) == 2
        assert not (tmp_path / "demo_v1.1-source.md").exists()

    def test_starter_file_refused(self, tmp_path: Path) -> None:
        from research_buddy.commands.bump import cmd_bump

        starter = tmp_path / "research-document.md"
        starter.write_text(_load_starter_md_text(), encoding="utf-8")
        assert cmd_bump(_bump_args(starter, "Q-001", apply=True)) == 2

    def test_existing_output_guarded_without_force(self, tmp_path: Path) -> None:
        from research_buddy.commands.bump import cmd_bump

        src = _make_source(tmp_path)
        (tmp_path / "demo_v1.1-source.md").write_text("pre-existing\n", encoding="utf-8")
        assert cmd_bump(_bump_args(src, "Q-001", apply=True)) == 2
        # Untouched without --force.
        assert (tmp_path / "demo_v1.1-source.md").read_text() == "pre-existing\n"
        # --force overwrites.
        assert cmd_bump(_bump_args(src, "Q-001", apply=True, force=True)) == 0
        assert "pre-existing" not in (tmp_path / "demo_v1.1-source.md").read_text()

    def test_non_md_rejected(self, tmp_path: Path) -> None:
        from research_buddy.commands.bump import cmd_bump

        j = tmp_path / "x.json"
        j.write_text("{}", encoding="utf-8")
        assert cmd_bump(_bump_args(j, "Q-001")) == 2


class TestBumpViaMain:
    def test_dispatch(self, tmp_path: Path) -> None:
        import sys
        from unittest.mock import patch

        from research_buddy.main import main

        src = _make_source(tmp_path)
        argv = ["research-buddy", "bump", str(src), "Q-001", "--apply"]
        with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        assert (tmp_path / "demo_v1.1-source.md").is_file()
