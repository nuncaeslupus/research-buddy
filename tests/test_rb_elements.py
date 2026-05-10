"""Tests for the v2 element-catalog renderers — admonitions, rb-verdict,
rb-cards, rb-banner, references-anchor styling, frontmatter banners, and
status chips."""

from __future__ import annotations

from research_buddy.build_md import (
    _expand_admonitions,
    _md_renderer,
    _references_tab_index,
    _render_banner,
    _render_cards,
    _render_frontmatter_banners,
    _render_verdict,
    _transform_rb_fences,
    build_md_html,
)

_FM = """\
---
doc_format_version: 2
research_buddy_version: "1.7.0"
version: "1.0"
date: "2026-05-10"
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


class TestAdmonitionExpansion:
    def test_note_kind_expands(self) -> None:
        src = "> [!NOTE]\n> body line\n"
        out = _expand_admonitions(src)
        assert '<div class="callout note">' in out
        assert "NOTE" in out
        assert "body line" in out

    def test_all_seven_kinds_supported(self) -> None:
        kinds = ["NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION", "LIMITATION", "HYPOTHESIS"]
        for kind in kinds:
            src = f"> [!{kind}]\n> body\n"
            out = _expand_admonitions(src)
            assert f"{kind}" in out
            assert "callout" in out

    def test_unknown_kind_left_as_blockquote(self) -> None:
        # Unknown kinds remain as plain blockquotes — they're not catalog
        # elements, so the renderer must not invent semantics for them.
        src = "> [!FOO]\n> body\n"
        out = _expand_admonitions(src)
        assert "callout" not in out
        assert "[!FOO]" in out

    def test_inside_fenced_code_left_alone(self) -> None:
        # Lines inside ``` fences must never be rewritten — that would
        # corrupt code samples that happen to contain admonition syntax.
        src = "```\n> [!NOTE]\n> not really\n```\n"
        out = _expand_admonitions(src)
        assert "callout" not in out

    def test_admonition_body_is_markdown(self) -> None:
        # Body is plain MD wrapped in a div — markdown-it parses it normally.
        html = build_md_html(_doc("## Tab\n\n> [!TIP]\n> Use **bold** and `code`.\n"))
        assert "<strong>bold</strong>" in html
        assert "<code>code</code>" in html
        assert '<div class="callout tip">' in html

    def test_two_admonitions_in_a_row(self) -> None:
        src = "> [!NOTE]\n> first\n\n> [!WARNING]\n> second\n"
        out = _expand_admonitions(src)
        assert out.count('class="callout note"') == 1
        assert out.count('class="callout warning"') == 1


class TestVerdictRenderer:
    def test_supports_kind(self) -> None:
        md = _md_renderer()
        out = _render_verdict(md, "supports", "Two Tier-1 sources support.")
        assert 'class="rb-verdict supports"' in out
        assert "SUPPORTS" in out
        assert "Two Tier-1 sources support." in out

    def test_all_four_kinds(self) -> None:
        md = _md_renderer()
        for k in ("supports", "contradicts", "unverifiable", "silent"):
            out = _render_verdict(md, k, "x")
            assert f'class="verdict-badge {k}"' in out

    def test_inline_markdown_in_body(self) -> None:
        md = _md_renderer()
        out = _render_verdict(md, "contradicts", "**Tier-1** silence.")
        assert "<strong>Tier-1</strong>" in out

    def test_via_fenced_block(self) -> None:
        body = "## Tab\n\n```rb-verdict supports\nTwo Tier-1 sources support.\n```\n"
        html = build_md_html(_doc(body))
        assert 'class="rb-verdict supports"' in html
        assert "SUPPORTS" in html
        # The original fenced code should not also leak through as a
        # `<pre><code class="language-rb-verdict">` block.
        assert "language-rb-verdict" not in html

    def test_unknown_verdict_kind_falls_back_to_code_block(self) -> None:
        # Unknown kind → not in catalog → fence renders as standard code,
        # not as a verdict. Fail-closed semantics.
        body = "## Tab\n\n```rb-verdict nope\nbody\n```\n"
        html = build_md_html(_doc(body))
        # No `<div class="rb-verdict …">` block was emitted — the fenced
        # block fell through to the default code-block renderer.
        assert 'class="rb-verdict ' not in html


class TestCardsRenderer:
    def test_two_cards_two_column_grid(self) -> None:
        md = _md_renderer()
        body = "- title: A\n  body: alpha\n- title: B\n  body: beta\n"
        out = _render_cards(md, body)
        assert 'class="card-grid"' in out
        assert "card-grid three" not in out
        assert ">A<" in out and "alpha" in out
        assert ">B<" in out and "beta" in out

    def test_three_cards_use_three_column_grid(self) -> None:
        md = _md_renderer()
        body = "- title: A\n  body: x\n- title: B\n  body: y\n- title: C\n  body: z\n"
        out = _render_cards(md, body)
        assert 'class="card-grid three"' in out

    def test_card_icon_optional(self) -> None:
        md = _md_renderer()
        body = "- title: A\n  body: x\n  icon: 🔬\n"
        out = _render_cards(md, body)
        assert "🔬" in out

    def test_invalid_yaml_falls_back(self) -> None:
        md = _md_renderer()
        out = _render_cards(md, "not: valid: yaml:\n  bad")
        assert "<pre>" in out  # graceful fallback rather than crash

    def test_multiparagraph_body_does_not_nest_p_in_p(self) -> None:
        # Regression for Gemini PR #81 review: wrapping a multi-paragraph
        # rendered body in <p> produced invalid <p><p>…</p><p>…</p></p>.
        # The fix puts the rendered body inside a <div class="card-body">
        # so the inner <p> tags stay at the right nesting level.
        md = _md_renderer()
        body = "- title: T\n  body: |\n    First paragraph.\n\n    Second paragraph.\n"
        out = _render_cards(md, body)
        assert "<p><p>" not in out  # no double-open
        assert "</p></p>" not in out  # no double-close
        assert "First paragraph." in out and "Second paragraph." in out

    def test_via_fenced_block(self) -> None:
        body = (
            "## Tab\n\n```rb-cards\n"
            "- title: First\n  body: alpha\n"
            "- title: Second\n  body: beta\n"
            "```\n"
        )
        html = build_md_html(_doc(body))
        assert 'class="card-grid"' in html
        assert "First" in html and "alpha" in html


class TestBannerRenderer:
    def test_usage_banner(self) -> None:
        md = _md_renderer()
        body = "title: How to use\nitems:\n  - First\n  - Second\n"
        out = _render_banner(md, "usage", body)
        assert 'class="usage-banner"' in out
        assert "How to use" in out
        assert "First" in out and "Second" in out

    def test_agnostic_banner(self) -> None:
        md = _md_renderer()
        out = _render_banner(md, "agnostic", "title: X\nbody: works for any domain.\n")
        assert 'class="agnostic"' in out
        assert "works for any domain" in out

    def test_cc_banner(self) -> None:
        md = _md_renderer()
        out = _render_banner(md, "cc", "title: License\nbody: CC-BY-4.0\n")
        assert 'class="cc-banner"' in out
        assert "CC-BY-4.0" in out

    def test_unknown_banner_kind_falls_back(self) -> None:
        md = _md_renderer()
        out = _render_banner(md, "frobnicate", "title: x\n")
        assert "<pre>" in out

    def test_agnostic_multiparagraph_no_nested_p(self) -> None:
        # Same Gemini-flagged nesting issue as cards, but for agnostic /cc
        # banners. Body now sits in `<div class="banner-body">`.
        md = _md_renderer()
        body = "title: X\nbody: |\n  Para one.\n\n  Para two.\n"
        out = _render_banner(md, "agnostic", body)
        assert "<p><p>" not in out and "</p></p>" not in out
        assert "Para one." in out and "Para two." in out

    def test_cc_multiparagraph_no_nested_p(self) -> None:
        md = _md_renderer()
        body = "title: License\nbody: |\n  Line A.\n\n  Line B.\n"
        out = _render_banner(md, "cc", body)
        assert "<p><p>" not in out and "</p></p>" not in out
        assert "Line A." in out and "Line B." in out

    def test_via_fenced_block(self) -> None:
        body = "## Tab\n\n```rb-banner usage\ntitle: How to use\nitems:\n  - First step\n```\n"
        html = build_md_html(_doc(body))
        assert 'class="usage-banner"' in html
        assert "First step" in html


class TestFrontmatterBanners:
    def test_banners_render_above_first_tab(self) -> None:
        banner_yaml = (
            'title: "Demo Project"\n'
            "banners:\n"
            "  - kind: usage\n"
            "    title: Quick start\n"
            "    items:\n"
            "      - Step one\n"
        )
        fm = _FM.replace('title: "Demo Project"', banner_yaml)
        html = build_md_html(fm + "\n## Tab A\n\nbody A\n\n## Tab B\n\nbody B\n")
        # Banner appears once, in the first tab only.
        assert html.count('class="usage-banner"') == 1
        # Inside the first tab content (before "## Tab B" rendered text).
        first_tab_idx = html.find("Tab A")
        second_tab_idx = html.find("body B")
        banner_idx = html.find('class="usage-banner"')
        assert first_tab_idx < banner_idx < second_tab_idx

    def test_unknown_kind_skipped_silently(self) -> None:
        md = _md_renderer()
        out = _render_frontmatter_banners(md, [{"kind": "foo", "title": "x"}])
        assert out == ""

    def test_non_list_returns_empty(self) -> None:
        md = _md_renderer()
        assert _render_frontmatter_banners(md, None) == ""
        assert _render_frontmatter_banners(md, "scalar") == ""


class TestReferencesAnchor:
    def test_class_added_to_following_list(self) -> None:
        body = "## Tab\n\n<!-- @anchor: references -->\n\n- First reference\n- Second reference\n"
        html = build_md_html(_doc(body))
        assert '<ul class="references">' in html

    def test_class_only_attaches_once(self) -> None:
        # If the anchor is followed by a list and then another list, only the
        # first list is treated as references.
        body = (
            "## Tab\n\n<!-- @anchor: references -->\n\n- Ref one\n\nSome prose.\n\n- Other list\n"
        )
        html = build_md_html(_doc(body))
        assert html.count('<ul class="references">') == 1

    def test_no_anchor_means_no_class(self) -> None:
        html = build_md_html(_doc("## Tab\n\n- a\n- b\n"))
        assert 'class="references"' not in html

    def test_anchor_before_h2_armed_at_tab_start(self) -> None:
        # The framework convention places `<!-- @anchor: NAME -->` *before*
        # the `## NAME` heading. The split drops it from the next tab body, so
        # `_references_tab_index` recovers the mapping.
        body = (
            "## First\n\nx\n\n"
            "<!-- @anchor: references -->\n"
            "## References\n\n"
            "### v1.0 — 2026-05-10\n\n"
            "- Cited paper\n"
        )
        assert _references_tab_index(body) == 1
        html = build_md_html(_doc(body))
        assert '<ul class="references">' in html

    def test_no_references_anchor_in_body(self) -> None:
        assert _references_tab_index("## A\n\nx\n\n## B\n\ny\n") is None

    def test_anchor_inside_fence_ignored(self) -> None:
        body = "## A\n\n```\n<!-- @anchor: references -->\n```\n\n## B\n\n- a\n"
        assert _references_tab_index(body) is None


class TestTransformRbFencesIsolated:
    def test_token_in_place_rewrite(self) -> None:
        md = _md_renderer()
        tokens = md.parse("```rb-verdict supports\nbody\n```\n")
        # Pre-condition: there's a fence token.
        assert any(t.type == "fence" for t in tokens)
        _transform_rb_fences(tokens, md)
        # Post-condition: the fence has been rewritten as html_block.
        assert any(t.type == "html_block" and "rb-verdict" in t.content for t in tokens)
        assert not any(t.type == "fence" for t in tokens)


class TestStatusChips:
    def test_chip_classes_round_trip_through_html(self) -> None:
        # html=True is enabled; raw <span> tags pass through and the CSS
        # provides the visual treatment. The renderer just needs to not
        # eat them.
        body = (
            "## Tab\n\n"
            'status: <span class="rb-ok">OK</span> '
            '<span class="rb-bad">FAIL</span> '
            '<span class="rb-flag">REVIEW</span>\n'
        )
        html = build_md_html(_doc(body))
        assert '<span class="rb-ok">OK</span>' in html
        assert '<span class="rb-bad">FAIL</span>' in html
        assert '<span class="rb-flag">REVIEW</span>' in html


class TestStarterRendersCleanly:
    def test_starter_renders_with_no_admonition_or_fence_artifacts(self) -> None:
        # Sanity check on the bundled starter — none of the catalog
        # elements should leave behind unrendered tokens after a build.
        from importlib import resources
        from pathlib import Path

        starter_path = Path(str(resources.files("research_buddy") / "starter.md"))
        src = starter_path.read_text(encoding="utf-8")
        html = build_md_html(src)
        # Common signs of a broken renderer:
        assert "[!NOTE]" not in html
        assert "[!TIP]" not in html
        assert "language-rb-verdict" not in html
        assert "language-rb-cards" not in html
        assert "language-rb-banner" not in html
