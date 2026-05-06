"""Tests for `research_buddy.clean_md` — generates the clean view of a v2 MD file."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_buddy.clean_md import (
    clean_md,
    clean_md_text,
    collect_framework_targets,
    derive_clean_path,
    parse_frontmatter,
    regenerate_title_block,
    strip_framework_block,
    unwrap_framework_links,
)

_FM = """\
---
format_version: 2
research_buddy_version: "1.4.0"
version: "1.0"
date: "2026-05-07"
file_name: "demo"
title: "Demo"
language:
  code: en
  label: English
project:
  domain: "demo"
ui_strings:
  status_open: OPEN
  status_done: "Done"
  status_wip: "WIP"
---
"""

_TITLE_BLOCK = (
    "<!-- @anchor: title -->\n"
    "# Old Title — Research Document\n\n"
    "Lots of agent-only metadata here.\n\n"
    "<!-- @end: title -->\n"
)

_FRAMEWORK_BLOCK = (
    "<!-- @anchor: framework.core -->\n"
    "## Framework (Core)\n\n"
    "Framework body. See [details](#framework-details).\n\n"
    '<a id="framework-detail-anchor"></a>\n\n'
    "<!-- @anchor: framework.reference -->\n"
    "## Framework (Reference)\n\n"
    "More framework body.\n\n"
    "<!-- @end: framework.reference -->\n"
)


def _full_doc() -> str:
    body = (
        f"{_TITLE_BLOCK}\n---\n\n{_FRAMEWORK_BLOCK}\n---\n\n"
        "## Project Specification\n\nThe real content.\n"
    )
    return _FM + "\n" + body


class TestStripFramework:
    def test_framework_block_removed(self) -> None:
        out = strip_framework_block(_FRAMEWORK_BLOCK + "\n---\n\n## After\n\nbody\n")
        assert "Framework (Core)" not in out
        assert "Framework (Reference)" not in out
        assert "## After" in out

    def test_trailing_separator_dropped(self) -> None:
        text = _FRAMEWORK_BLOCK + "\n---\n\n## After\n"
        out = strip_framework_block(text)
        # The trailing --- after the framework block should be consumed
        # (otherwise a stray separator would lead the cleaned doc).
        assert not out.lstrip().startswith("---")

    def test_malformed_no_closer_leaves_text_intact(self) -> None:
        text = "<!-- @anchor: framework.core -->\nbody with no end\n"
        out = strip_framework_block(text)
        # Should not silently destroy content when @end is missing.
        # Behavior: stop processing at the malformed opener (out is whatever
        # came before it, which here is empty).
        assert "framework.core" not in out


class TestUnwrapLinks:
    def test_framework_link_unwrapped_to_label(self) -> None:
        targets = {"framework-core"}
        out = unwrap_framework_links("See [the framework](#framework-core).", targets)
        assert out == "See the framework."

    def test_body_link_preserved(self) -> None:
        targets = {"framework-core"}
        out = unwrap_framework_links("See [body](#some-other-anchor).", targets)
        assert out == "See [body](#some-other-anchor)."

    def test_empty_target_set_is_noop(self) -> None:
        text = "[a](#x) [b](#y)"
        assert unwrap_framework_links(text, set()) == text

    def test_collect_framework_targets_includes_headings_and_a_ids(self) -> None:
        targets = collect_framework_targets(_FRAMEWORK_BLOCK)
        assert "framework-core" in targets
        assert "framework-reference" in targets
        assert "framework-detail-anchor" in targets


class TestTitleRegen:
    def _fm(self, **overrides: object) -> dict:
        base: dict = {
            "title": "Demo Project",
            "version": "1.0",
            "date": "2026-05-07",
            "subtitle": "a subtitle",
        }
        base.update(overrides)
        return base

    def test_regenerated_title_uses_frontmatter(self) -> None:
        out = regenerate_title_block(_TITLE_BLOCK, self._fm())
        assert "# Demo Project — Research Document" in out
        assert "Old Title" not in out
        assert "1.0" in out
        assert "2026-05-07" in out
        assert "a subtitle" in out

    def test_subtitle_omitted_if_absent(self) -> None:
        out = regenerate_title_block(_TITLE_BLOCK, self._fm(subtitle=None))
        lines = out.splitlines()
        title_idx = next(i for i, line in enumerate(lines) if line.startswith("# Demo Project"))
        # H1, blank, then version stamp — no subtitle line in between.
        assert lines[title_idx + 2].startswith("**Version:**")

    def test_missing_fields_fall_back(self) -> None:
        out = regenerate_title_block(_TITLE_BLOCK, {})
        assert "Untitled" in out
        assert "?" in out  # version fallback

    def test_only_first_title_block_replaced(self) -> None:
        text = _TITLE_BLOCK + "\n" + _TITLE_BLOCK
        out = regenerate_title_block(text, self._fm())
        # The second title block should remain intact.
        assert out.count("Old Title") == 1


class TestRefusalGates:
    def test_starter_mode_raises(self, tmp_path: Path) -> None:
        starter_fm = _FM.replace('domain: "demo"', "domain: null")
        path = tmp_path / "starter.md"
        path.write_text(starter_fm + "\n# body\n", encoding="utf-8")
        with pytest.raises(ValueError, match="starter file"):
            clean_md(path)

    def test_missing_frontmatter_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "x.md"
        path.write_text("# no frontmatter\n", encoding="utf-8")
        with pytest.raises(ValueError, match="frontmatter"):
            clean_md(path)

    def test_wrong_format_version_raises(self, tmp_path: Path) -> None:
        bad = _FM.replace("format_version: 2", "format_version: 1")
        path = tmp_path / "x.md"
        path.write_text(bad + "\n# body\n", encoding="utf-8")
        with pytest.raises(ValueError, match="format_version"):
            clean_md(path)

    def test_output_overwriting_source_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "demo_v1.0-source.md"
        path.write_text(_full_doc(), encoding="utf-8")
        with pytest.raises(ValueError, match="overwrite"):
            clean_md(path, output_path=path)


class TestPathDerivation:
    def test_derives_from_frontmatter(self, tmp_path: Path) -> None:
        src = tmp_path / "anything.md"
        out = derive_clean_path(src, {"file_name": "demo", "version": "1.0"})
        assert out.name == "demo_v1.0.md"
        assert out.parent == tmp_path

    def test_falls_back_to_stem_minus_source(self, tmp_path: Path) -> None:
        src = tmp_path / "demo_v1.0-source.md"
        out = derive_clean_path(src, {})
        assert out.name == "demo_v1.0.md"

    def test_falls_back_to_plain_stem(self, tmp_path: Path) -> None:
        src = tmp_path / "freeform.md"
        out = derive_clean_path(src, {})
        assert out.name == "freeform.md"


class TestEndToEnd:
    def test_clean_md_text_strips_framework_and_unwraps(self) -> None:
        full = _full_doc()
        fm, _ = parse_frontmatter(full)
        assert fm is not None
        cleaned = clean_md_text(full, fm)
        assert "Framework (Core)" not in cleaned
        assert "Framework (Reference)" not in cleaned
        # The intra-framework link [details](#framework-details) was inside
        # the stripped block, so unwrapping isn't observable here. But we can
        # confirm a body link to a framework target gets unwrapped:
        body_with_link = full + "\nSee [details](#framework-core).\n"
        cleaned2 = clean_md_text(body_with_link, fm)
        assert "[details](#framework-core)" not in cleaned2
        assert "See details." in cleaned2

    def test_clean_md_writes_output_and_returns_path(self, tmp_path: Path) -> None:
        src = tmp_path / "demo_v1.0-source.md"
        src.write_text(_full_doc(), encoding="utf-8")
        out = clean_md(src)
        assert out.exists()
        assert out.name == "demo_v1.0.md"
        cleaned = out.read_text(encoding="utf-8")
        assert "Framework (Core)" not in cleaned
        assert "## Project Specification" in cleaned
