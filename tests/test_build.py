"""Tests for HTML build logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_docs.build import (
    BuildState,
    md,
    md_block,
    r_callout,
    r_code,
    r_h3,
    r_heading,
    r_p,
    r_paragraph,
    r_table,
    render_blocks,
    render_section,
    slugify,
)


class TestMarkdownInlining:
    def test_bold_italic(self) -> None:
        assert md("***bold-italic***") == "<strong><em>bold-italic</em></strong>"
        assert md("**bold**") == "<strong>bold</strong>"
        assert md("*italic*") == "<em>italic</em>"

    def test_inline_code(self) -> None:
        assert md("`code`") == "<code>code</code>"

    def test_xlink(self) -> None:
        text = "[Label](#target){tab=research}"
        html = md(text)
        assert 'class="xlink"' in html
        assert 'data-tab="research"' in html
        assert 'href="#target"' in html

    def test_tags(self) -> None:
        assert md("[tag:phase-1]P1[/tag]") == '<span class="tag phase-1">P1</span>'
        # invalid tag class defaults to tag-blue
        assert md("[tag:invalid]X[/tag]") == '<span class="tag tag-blue">X</span>'


class TestBlockRenderers:
    @pytest.fixture
    def state(self) -> BuildState:
        return BuildState()

    def test_p(self, state: BuildState) -> None:
        assert r_p({"md": "hello"}, state) == "<p>hello</p>\n"

    def test_h3_with_id(self, state: BuildState) -> None:
        html = r_h3({"md": "Title", "id": "s1"}, state)
        assert 'id="s1"' in html
        assert "Title" in html

    def test_heading_level_4(self, state: BuildState) -> None:
        html = r_heading({"level": 4, "content": "Sub"}, state)
        assert "h4" in html.lower()
        assert "Sub" in html

    def test_paragraph_block(self, state: BuildState) -> None:
        html = r_paragraph({"content": "Text here"}, state)
        assert "<p>Text here</p>" in html

    def test_code(self, state: BuildState) -> None:
        html = r_code({"text": "x = 1", "lang": "python"}, state)
        assert 'data-lang="python"' in html
        assert "x = 1" in html

    def test_callout(self, state: BuildState) -> None:
        html = r_callout({"md": "Note", "variant": "amber", "title": "Warning"}, state)
        assert 'class="callout amber"' in html
        assert "Warning" in html

    def test_table(self, state: BuildState) -> None:
        html = r_table({"headers": ["A", "B"], "rows": [["1", "2"]]}, state)
        assert "table" in html.lower()
        assert "A" in html
        assert "1" in html

    def test_unknown_block_renders_comment(self, state: BuildState) -> None:
        html = render_blocks([{"type": "nonexistent"}], state)
        assert "<!-- unknown block type: nonexistent -->" in html


class TestSectionRendering:
    def test_recursive_render(self) -> None:
        state = BuildState()
        nav = []
        sec = {
            "blocks": [{"type": "p", "md": "root"}],
            "subsections": {
                "Sub": {
                    "blocks": [{"type": "p", "md": "child"}]
                }
            }
        }
        html = render_section("Top", sec, state, nav, level=2, number="1")
        assert 'id="top"' in html
        assert "root" in html
        assert "child" in html
        assert 'id="sub"' in html
        # Nav should have 2 entries
        assert len(nav) == 2
        assert nav[0]["title"] == "Top"
        assert nav[1]["title"] == "Sub"


def test_slugify() -> None:
    assert slugify("Hello World") == "hello-world"
    assert slugify("§1.2 Section!") == "12-section"
    assert slugify("") == "sec"


def test_md_block_splitting() -> None:
    text = "Para 1\n\nPara 2"
    html = md_block(text)
    assert "<p>Para 1</p><p>Para 2</p>" in html
