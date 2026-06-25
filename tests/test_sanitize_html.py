"""Tests for `research_buddy.sanitize_html` — the v2 render-time HTML sanitizer.

The sanitizer is the backstop for the v2 trust boundary: agent-authored
Markdown is rendered with raw-HTML passthrough, so the rendered fragments are
run through `sanitize_html` to strip active content while preserving the
documented Element catalog (status chips, inline SVG, tables, …).
"""

from __future__ import annotations

from research_buddy.sanitize_html import sanitize_html


class TestActiveContentStripped:
    def test_script_tag_and_content_removed(self) -> None:
        out = sanitize_html("<p>keep</p><script>steal()</script>")
        assert "<p>keep</p>" in out
        assert "script" not in out
        assert "steal()" not in out  # content gone, not just the tag

    def test_inline_event_handler_removed(self) -> None:
        out = sanitize_html('<img src="x" onerror="alert(1)">')
        assert "onerror" not in out
        assert "alert(1)" not in out
        assert "<img" in out  # the element itself survives

    def test_javascript_uri_removed_link_kept(self) -> None:
        out = sanitize_html('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in out
        assert ">click</a>" in out

    def test_data_uri_removed(self) -> None:
        out = sanitize_html('<a href="data:text/html,<script>alert(1)</script>">x</a>')
        assert "data:" not in out

    def test_vbscript_uri_removed(self) -> None:
        assert "vbscript:" not in sanitize_html('<a href="vbscript:msgbox(1)">x</a>')

    def test_iframe_removed(self) -> None:
        assert "<iframe" not in sanitize_html('<iframe src="https://evil"></iframe>')


class TestSvgSafety:
    def test_static_svg_preserved(self) -> None:
        svg = (
            '<svg viewBox="0 0 10 10"><path d="M0 0L10 10" fill="currentColor"></path>'
            '<text x="1" y="2">hi</text></svg>'
        )
        out = sanitize_html(svg)
        assert "<svg" in out and 'viewBox="0 0 10 10"' in out
        assert "<path" in out and 'd="M0 0L10 10"' in out
        assert ">hi</text>" in out

    def test_svg_script_removed(self) -> None:
        out = sanitize_html("<svg><script>bad()</script><circle r='2'></circle></svg>")
        assert "script" not in out and "bad()" not in out
        assert "<circle" in out  # legitimate shape kept

    def test_svg_event_handler_removed(self) -> None:
        out = sanitize_html('<svg onload="x()"><rect width="4" height="4"></rect></svg>')
        assert "onload" not in out
        assert "<rect" in out

    def test_svg_foreignobject_removed(self) -> None:
        # <foreignObject> re-enters the HTML namespace — a known XSS vector.
        out = sanitize_html(
            "<svg><foreignObject><img src=x onerror=alert(1)></foreignObject></svg>"
        )
        assert "foreignObject".lower() not in out.lower()
        assert "onerror" not in out

    def test_svg_animate_removed(self) -> None:
        # <animate> can rewrite an attribute to a javascript: URI at runtime.
        out = sanitize_html(
            '<svg><a><animate attributeName="href" to="javascript:alert(1)"></animate>'
            "<circle r='1'></circle></a></svg>"
        )
        assert "animate" not in out
        assert "javascript:" not in out


class TestLegitimatePrimitivesPreserved:
    def test_status_chip_preserved(self) -> None:
        for cls in ("rb-ok", "rb-bad", "rb-flag"):
            out = sanitize_html(f'<span class="{cls}">x</span>')
            assert f'class="{cls}"' in out

    def test_anchor_comment_preserved(self) -> None:
        # The framework's HTML-comment anchors must survive (strip_comments=False).
        out = sanitize_html("<!-- @anchor: references --><p>x</p>")
        assert "<!-- @anchor: references -->" in out

    def test_empty_anchor_target_preserved(self) -> None:
        out = sanitize_html('<a id="q-001"></a>')
        assert 'id="q-001"' in out

    def test_table_layout_preserved(self) -> None:
        html = (
            '<div class="table-wrap"><table class="t-fixed"><colgroup>'
            '<col style="width:32%"></colgroup><tbody><tr>'
            '<td class="nw">x</td></tr></tbody></table></div>'
        )
        out = sanitize_html(html)
        assert 'class="t-fixed"' in out
        assert 'style="width:32%"' in out  # the layout width survives the style filter
        assert 'class="nw"' in out

    def test_heading_id_preserved(self) -> None:
        out = sanitize_html('<h3 id="domain"><span class="num">1.3</span> Domain</h3>')
        assert 'id="domain"' in out
        assert 'class="num"' in out


class TestStyleFilter:
    def test_layout_width_kept_positioning_dropped(self) -> None:
        # Mirrors the table-layout `<col style="width:…">` the renderer emits.
        html = (
            "<table><colgroup>"
            '<col style="width:30%;position:fixed;top:0"></colgroup>'
            "<tbody><tr><td>x</td></tr></tbody></table>"
        )
        out = sanitize_html(html)
        assert "width:30%" in out  # presentational — kept
        assert "position" not in out  # layout/overlay tricks — dropped
        assert "top:0" not in out


class TestMisc:
    def test_empty_input(self) -> None:
        assert sanitize_html("") == ""

    def test_idempotent(self) -> None:
        html = '<svg viewBox="0 0 4 4"><circle r="1"></circle></svg><span class="rb-ok">y</span>'
        once = sanitize_html(html)
        assert sanitize_html(once) == once

    def test_no_rel_injected_on_internal_links(self) -> None:
        # link_rel=None: internal #anchor links stay clean.
        out = sanitize_html('<a href="#section">go</a>')
        assert "rel=" not in out
