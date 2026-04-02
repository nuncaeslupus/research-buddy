"""Tests for the build engine."""

from __future__ import annotations

from research_docs.build import (
    build_html,
    md,
    r_callout,
    r_code,
    r_h3,
    r_heading,
    r_p,
    r_paragraph,
    r_table,
    render_blocks,
)


class TestInlineMarkdown:
    def test_bold(self) -> None:
        assert md("**hello**") == "<strong>hello</strong>"

    def test_italic(self) -> None:
        assert md("*hello*") == "<em>hello</em>"

    def test_inline_code(self) -> None:
        assert md("`foo`") == "<code>foo</code>"

    def test_inline_code_escapes_html(self) -> None:
        assert md("`<div>`") == "<code>&lt;div&gt;</code>"

    def test_link(self) -> None:
        assert md("[text](http://x.com)") == '<a href="http://x.com">text</a>'

    def test_xlink(self) -> None:
        result = md("[label](s1){tab=theory}")
        assert 'class="xlink"' in result
        assert 'data-tab="theory"' in result

    def test_empty(self) -> None:
        assert md("") == ""


class TestBlockRenderers:
    def test_p(self) -> None:
        assert r_p({"md": "hello"}) == "<p>hello</p>\n"

    def test_h3_with_id(self) -> None:
        html = r_h3({"md": "Title", "id": "s1"})
        assert 'id="s1"' in html
        assert "<h3" in html

    def test_heading_level_4(self) -> None:
        html = r_heading({"level": 4, "content": "Sub"})
        assert "<h4>" in html
        assert "Sub" in html

    def test_paragraph_block(self) -> None:
        html = r_paragraph({"content": "Text here"})
        assert "<p>Text here</p>" in html

    def test_code(self) -> None:
        html = r_code({"text": "x = 1", "lang": "python"})
        assert "language-python" in html
        assert "x = 1" in html

    def test_callout(self) -> None:
        html = r_callout({"md": "Note", "variant": "amber", "title": "Warning"})
        assert "callout amber" in html
        assert "Warning" in html

    def test_table(self) -> None:
        html = r_table({"headers": ["A", "B"], "rows": [["1", "2"]]})
        assert "<th>A</th>" in html
        assert ">1</td>" in html

    def test_unknown_block_renders_comment(self) -> None:
        html = render_blocks([{"type": "nonexistent"}])
        assert "<!-- unknown block type: nonexistent -->" in html


class TestBuildHtml:
    def test_produces_html(self, starter_doc: dict) -> None:
        html = build_html(starter_doc)
        assert "<!DOCTYPE html>" in html
        assert "My Research Document" in html

    def test_meta_title_in_output(self, starter_doc: dict) -> None:
        starter_doc["meta"]["title"] = "Custom Title"
        html = build_html(starter_doc)
        assert "<title>Custom Title" in html

    def test_theme_css_injected(self, starter_doc: dict) -> None:
        html = build_html(starter_doc, theme_css=":root { --bg: #fff; }")
        assert "Theme overrides" in html
        assert "--bg: #fff" in html

    def test_no_theme_by_default(self, starter_doc: dict) -> None:
        html = build_html(starter_doc)
        assert "Theme overrides" not in html
