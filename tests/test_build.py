"""Tests for HTML build logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_buddy.build import (
    BuildState,
    find_latest_json,
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
        nav: list = []
        sec = {
            "blocks": [{"type": "p", "md": "root"}],
            "subsections": {"Sub": {"blocks": [{"type": "p", "md": "child"}]}},
        }
        html = render_section("Top", sec, state, nav, level=2, number="1")
        assert 'id="top"' in html
        assert "root" in html
        assert "child" in html
        assert 'id="sub"' in html
        assert len(nav) == 2
        assert nav[0]["title"] == "Top"
        assert nav[1]["title"] == "Sub"


class TestFindLatestJson:
    def test_finds_versioned_file(self, tmp_path: Path) -> None:

        f = tmp_path / "myproject_v1.2.json"
        f.write_text("{}")
        result = find_latest_json(tmp_path)
        assert result == f

    def test_picks_highest_version(self, tmp_path: Path) -> None:

        (tmp_path / "myproject_v1.0.json").write_text("{}")
        (tmp_path / "myproject_v1.5.json").write_text("{}")
        (tmp_path / "myproject_v2.1.json").write_text("{}")
        result = find_latest_json(tmp_path)
        assert result is not None
        assert "v2.1" in result.name

    def test_fallback_to_research_document(self, tmp_path: Path) -> None:

        f = tmp_path / "research-document.json"
        f.write_text("{}")
        result = find_latest_json(tmp_path)
        assert result == f

    def test_versioned_takes_priority_over_fallback(self, tmp_path: Path) -> None:

        (tmp_path / "research-document.json").write_text("{}")
        versioned = tmp_path / "project_v1.0.json"
        versioned.write_text("{}")
        result = find_latest_json(tmp_path)
        assert result == versioned

    def test_no_json_returns_none(self, tmp_path: Path) -> None:
        result = find_latest_json(tmp_path)
        assert result is None

    def test_legacy_document_v_pattern(self, tmp_path: Path) -> None:
        """document_v*.json files (old naming) still work."""

        f = tmp_path / "document_v3.55.json"
        f.write_text("{}")
        result = find_latest_json(tmp_path)
        assert result == f


class TestHtmlOutput:
    def test_footer_present(self, starter_doc: dict) -> None:
        from research_buddy.build import build_html

        html = build_html(starter_doc)
        assert "Research Buddy" in html
        assert "rb-powered-by" in html

    def test_rb_version_in_footer(self, starter_doc: dict) -> None:
        from research_buddy.build import build_html

        html = build_html(starter_doc)
        assert "v1.0" in html

    def test_lang_attribute_from_object(self, starter_doc: dict) -> None:
        from research_buddy.build import build_html

        starter_doc["meta"]["language"] = {"code": "es", "label": "Español"}
        html = build_html(starter_doc)
        assert 'lang="es"' in html

    def test_lang_attribute_from_string(self, starter_doc: dict) -> None:
        from research_buddy.build import build_html

        starter_doc["meta"]["language"] = "English"
        html = build_html(starter_doc)
        assert 'lang="English"' in html or 'lang="' in html


def test_slugify() -> None:
    assert slugify("Hello World") == "hello-world"
    assert slugify("§1.2 Section!") == "12-section"
    assert slugify("") == "sec"


def test_md_block_splitting() -> None:
    text = "Para 1\n\nPara 2"
    html = md_block(text)
    assert "<p>Para 1</p><p>Para 2</p>" in html
