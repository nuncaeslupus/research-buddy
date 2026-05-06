"""Tests for `research_buddy.build_md` — v2 MD → HTML using v1 chrome."""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import pytest

from research_buddy.build_md import (
    _extract_nav_entries,
    _strip_frontmatter,
    build_md_html,
    split_into_tabs,
)

_FM = """\
---
format_version: 2
research_buddy_version: "1.4.0"
version: "1.0"
date: "2026-05-07"
file_name: "demo"
title: "Demo Project"
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


def _doc(body: str) -> str:
    return _FM + "\n" + body


class TestStripFrontmatter:
    def test_removes_yaml_block(self) -> None:
        out = _strip_frontmatter(_FM + "\nbody\n")
        assert "format_version" not in out
        assert "body" in out

    def test_no_frontmatter_passthrough(self) -> None:
        text = "# just a doc\n"
        assert _strip_frontmatter(text) == text


class TestBodySplit:
    def test_h2_splits_into_tabs(self) -> None:
        body = "## Tab A\n\nbody A\n\n## Tab B\n\nbody B\n"
        tabs = split_into_tabs(body)
        labels = [t[0] for t in tabs]
        assert labels == ["Tab A", "Tab B"]
        assert "body A" in tabs[0][1]
        assert "body B" in tabs[1][1]

    def test_content_before_first_h2_dropped(self) -> None:
        body = "preamble\n\n## Tab A\n\nbody A\n"
        tabs = split_into_tabs(body)
        assert len(tabs) == 1
        assert "preamble" not in tabs[0][1]

    def test_h2_inside_fenced_code_ignored(self) -> None:
        body = "## Real Tab\n\n```\n## Not a tab\n```\n\nstill in tab\n"
        tabs = split_into_tabs(body)
        assert len(tabs) == 1
        assert tabs[0][0] == "Real Tab"
        assert "## Not a tab" in tabs[0][1]

    def test_no_h2_returns_empty(self) -> None:
        assert split_into_tabs("just a paragraph\n") == []


class TestNavExtraction:
    def test_h3_and_h4_collected(self) -> None:
        entries = _extract_nav_entries("### Section One\n\ntext\n\n#### Sub\n")
        levels = [e["level"] for e in entries]
        titles = [e["title"] for e in entries]
        assert levels == [3, 4]
        assert titles == ["Section One", "Sub"]

    def test_h2_not_collected(self) -> None:
        # H2s become tab labels; sidebar nav only carries H3+.
        entries = _extract_nav_entries("## Nope\n\n### Yes\n")
        assert [e["title"] for e in entries] == ["Yes"]

    def test_anchor_ids_present(self) -> None:
        entries = _extract_nav_entries("### Hello World\n")
        assert entries[0]["id"] == "hello-world"


class TestRenderedHTML:
    def test_gfm_table_renders(self) -> None:
        html = build_md_html(_doc("## Tab\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"))
        assert "<table>" in html
        assert "<th>A</th>" in html
        assert "<td>1</td>" in html

    def test_raw_html_preserved(self) -> None:
        html = build_md_html(_doc('## Tab\n\n<a id="my-target"></a>\n\nbody\n'))
        assert '<a id="my-target"></a>' in html

    def test_html_comments_preserved(self) -> None:
        # Anchor markers (HTML comments) must survive — the validator looks
        # for them, and reading the rendered source view should match the MD.
        html = build_md_html(_doc("## Tab\n\n<!-- @anchor: foo -->\nbody\n<!-- @end: foo -->\n"))
        assert "<!-- @anchor: foo -->" in html
        assert "<!-- @end: foo -->" in html

    def test_fenced_code_class_for_hljs(self) -> None:
        html = build_md_html(_doc("## Tab\n\n```python\nprint('hi')\n```\n"))
        # markdown-it produces `class="language-python"` which hljs reads.
        assert "language-python" in html


class TestChromeIntegration:
    def test_includes_tab_bar_and_sidebar(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n\n## B\n\ny\n"))
        assert '<div id="tab-bar">' in html
        assert '<div id="sidebar">' in html
        assert '<div id="layout">' in html
        assert '<div id="main">' in html

    def test_includes_theme_toggle_and_fouc_bootstrap(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n"))
        assert 'id="theme-toggle"' in html
        assert "rb-theme" in html  # FOUC-prevention script reads this key

    def test_hljs_assets_inlined(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n"))
        assert "hljs.highlightAll" in html

    def test_rb_footer_inlined(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n"))
        assert "rb-powered-by" in html

    def test_tabs_inject_uses_unique_ids(self) -> None:
        # script.js has a /*TABS_INJECT*/ marker that must be replaced with
        # the JSON list of tab IDs the JS uses for switching.
        html = build_md_html(_doc("## A\n\nx\n\n## B\n\ny\n"))
        m = re.search(r"/\*TABS_INJECT\*/(\[.*?\])/\*END_INJECT\*/", html)
        assert m, "TABS_INJECT marker not replaced"
        ids = m.group(1)
        assert '"a"' in ids
        assert '"b"' in ids

    def test_doc_title_from_frontmatter(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n"))
        assert "<title>Demo Project — v1.0</title>" in html

    def test_lang_attribute_from_frontmatter(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n"))
        assert '<html lang="en">' in html

    def test_no_h2_falls_back_to_single_tab(self) -> None:
        # Defensive: a doc with no H2 must still render (single tab)
        # rather than producing an empty page.
        html = build_md_html(_doc("just a paragraph\n"))
        assert '<div id="tab-bar">' in html
        assert "just a paragraph" in html


class TestStarterRender:
    def test_bundled_starter_md_renders_without_framework(self) -> None:
        path = Path(str(resources.files("research_buddy") / "starter.md"))
        html = build_md_html(path.read_text(encoding="utf-8"))
        # Default mode strips the framework — the example should look like
        # the JSON-built starter.html, which never renders agent_guidelines.
        assert "Framework (Core)" not in html
        assert "Framework (Reference)" not in html
        # Project-content tabs do remain:
        assert "Project Specification" in html
        assert "Open Research Queue" in html
        assert '<div id="tab-bar">' in html
        assert '<div id="sidebar">' in html

    def test_starter_md_with_keep_framework(self) -> None:
        path = Path(str(resources.files("research_buddy") / "starter.md"))
        html = build_md_html(path.read_text(encoding="utf-8"), keep_framework=True)
        # Agent-facing view: framework tabs should be present.
        assert "Framework (Core)" in html
        assert "Framework (Reference)" in html


class TestThemeOverride:
    def test_theme_css_appended(self) -> None:
        html = build_md_html(_doc("## A\n\nx\n"), theme_css="/* CUSTOM */ body{color:red}")
        assert "/* CUSTOM */" in html
        assert "body{color:red}" in html


class TestBuildMdCli:
    """Integration: `research-buddy build foo.md` dispatches through cmd_build."""

    def test_build_md_via_main(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        # Without a framework block, the validator expects {file_name}_v{version}.md
        # (no -source suffix). The source-suffixed name is for files that
        # carry the framework — covered by test_build_md_starter_source below.
        src = tmp_path / "demo_v1.0.md"
        src.write_text(_doc("## Tab\n\nbody\n"), encoding="utf-8")
        rc = perform_build_md(src, tmp_path, no_versioning=True)
        assert rc == 0
        out = tmp_path / "demo.html"
        assert out.exists()
        assert "<title>Demo Project" in out.read_text(encoding="utf-8")

    def test_build_md_versioned_writes_to_versions_dir(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        (tmp_path / "versions").mkdir()
        src = tmp_path / "demo_v1.0.md"
        src.write_text(_doc("## Tab\n\nbody\n"), encoding="utf-8")
        rc = perform_build_md(src, tmp_path)
        assert rc == 0
        assert (tmp_path / "versions" / "demo_v1.0.html").exists()
        assert (tmp_path / "demo.html").exists()

    def test_build_md_returns_1_on_validation_error(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        # project mode + null required field → real validation error
        project_null_ver = _FM.replace('version: "1.0"', "version: null")
        src = tmp_path / "demo_v1.0.md"
        src.write_text(project_null_ver + "\n## A\n", encoding="utf-8")
        rc = perform_build_md(src, tmp_path, no_versioning=True)
        assert rc == 1


@pytest.fixture(autouse=True)
def _clear_md_renderer_cache() -> None:
    """The markdown-it renderer is module-cached. Tests don't share token state,
    but flushing the cache between modules avoids state-bleed surprises if a
    future test poked at the renderer's instance state."""
    from research_buddy.build_md import _md_renderer

    _md_renderer.cache_clear()
