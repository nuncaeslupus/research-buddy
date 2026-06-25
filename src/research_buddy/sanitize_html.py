"""Sanitize the agent-authored HTML on the v2 Markdown build path.

v2's premise is *LLM-authored Markdown* rendered to a single-file HTML page a
human opens in a browser. The renderer runs Jinja with ``autoescape=False`` and
markdown-it with ``html=True``, so raw HTML in the document body passes straight
through. A prompt-injected or sloppy agent emitting ``<script>``, an inline
``onerror=`` handler, a ``javascript:`` URI, or an ``<svg>`` carrying a
``<foreignObject>`` is therefore in the threat model.

``validator_md._check_dangerous_html`` *warns* about the obvious cases at
validate time; this module is the render-time backstop that actually neutralizes
them. It runs every agent-derived HTML fragment (the rendered body of each tab,
frontmatter banners, tab labels) through `nh3` (Rust ``ammonia``) with an
allowlist tuned to exactly what the renderer emits plus the closed
``Element catalog`` in ``starter.md`` — most importantly the inline SVG of EL-09
and the status chips of EL-16.

Why a real sanitizer and not a regex: SVG is a large attack surface
(``<foreignObject>`` re-enters the HTML namespace, ``<animate>`` can rewrite
attributes, ``<use href>`` can pull external content) that cannot be safely
filtered with pattern matching. `nh3` parses to a DOM and re-serializes, so the
output is well-formed regardless of how malformed the input was.

The trusted chrome (tab bar, sidebar, footer, the app's own ``<script>`` /
``<style>``) is *not* run through here — it is tool-generated, and sanitizing it
would strip the very ``data-tab`` / ``<script>`` it depends on. Only
agent-controlled fragments are sanitized; see `build_md`.
"""

from __future__ import annotations

import nh3

# ---------------------------------------------------------------------------
# Allowlist — least privilege, matched to the renderer's output + starter.md's
# Element catalog. Anything not listed is dropped (its text content is kept,
# except for `_CLEAN_CONTENT_TAGS`).
# ---------------------------------------------------------------------------

# Block + inline tags markdown-it (commonmark + tables + anchors) emits, plus
# the `<div>`/`<span>` wrappers the rb-* renderers and status chips produce.
_HTML_TAGS: frozenset[str] = frozenset(
    {
        # prose / structure
        "p", "br", "hr", "blockquote", "pre", "code",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li",
        # tables (incl. the layout colgroup/col the table renderer emits)
        "table", "thead", "tbody", "tr", "th", "td", "colgroup", "col",
        # inline
        "a", "img", "em", "strong", "del", "s", "sub", "sup",
        "kbd", "mark", "abbr",
        # rb-* wrappers, callouts, cards, verdicts, banners, status chips
        "span", "div",
    }
)  # fmt: skip

# Static inline-SVG illustration set (EL-09). Deliberately excludes the dynamic
# / namespace-crossing elements that are the real SVG XSS vectors:
# `<script>`, `<foreignObject>`, `<animate>`, `<set>`, `<animateTransform>`,
# `<handler>`. html5 parsing rewrites a few SVG tag names to camelCase in the
# tree (e.g. `lineargradient` -> `linearGradient`), and ammonia matches the
# adjusted name, so both spellings are listed.
_SVG_TAGS: frozenset[str] = frozenset(
    {
        "svg", "g", "path", "rect", "circle", "ellipse", "line",
        "polyline", "polygon", "text", "tspan", "textPath", "textpath",
        "defs", "marker", "symbol", "use", "image", "title", "desc",
        "linearGradient", "lineargradient", "radialGradient", "radialgradient",
        "stop", "clipPath", "clippath", "mask", "pattern",
    }
)  # fmt: skip

ALLOWED_TAGS: frozenset[str] = _HTML_TAGS | _SVG_TAGS

# Tags whose *content* is dropped too (not just the tag). Without this, the text
# inside a `<script>` survives as page text. These must NOT also appear in
# `ALLOWED_TAGS` (ammonia rejects the overlap).
_CLEAN_CONTENT_TAGS: frozenset[str] = frozenset({"script", "style"})

# SVG presentational attributes — harmless on any element, so granted globally
# via the "*" wildcard alongside id/class/style. camelCase SVG attributes are
# listed in both spellings for the same html5-adjustment reason as the tags.
_SVG_ATTRS: frozenset[str] = frozenset(
    {
        "viewBox", "viewbox", "xmlns", "xmlns:xlink", "preserveAspectRatio",
        "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
        "width", "height", "d", "points", "transform", "fill", "stroke",
        "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
        "stroke-dashoffset", "stroke-opacity", "fill-opacity", "fill-rule",
        "clip-rule", "clip-path", "opacity", "offset", "stop-color",
        "stop-opacity", "gradientUnits", "gradientunits", "gradientTransform",
        "gradienttransform", "spreadMethod", "spreadmethod", "patternUnits",
        "patternunits", "patternTransform", "patterntransform", "markerWidth",
        "markerwidth", "markerHeight", "markerheight", "refX", "refx", "refY",
        "refy", "orient", "markerUnits", "markerunits", "text-anchor",
        "dominant-baseline", "alignment-baseline", "font-family", "font-size",
        "font-weight", "font-style", "letter-spacing", "dx", "dy", "rotate",
        "marker-start", "marker-mid", "marker-end", "vector-effect", "color",
        "role", "aria-hidden", "aria-label",
    }
)  # fmt: skip

ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    # Global: anchors/cross-links need id; every rb-* primitive carries class;
    # `<col style="width:..">` (table layout) and inline SVG need style.
    "*": {"id", "class", "style"} | set(_SVG_ATTRS),
    "a": {"href", "title", "name", "hreflang"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan", "align"},
    "th": {"colspan", "rowspan", "align", "scope"},
    "col": {"span"},
    "colgroup": {"span"},
    "ol": {"start", "type"},
    # SVG references (fragment/relative only — scheme-filtered like any URL).
    "use": {"href", "xlink:href"},
    "image": {"href", "xlink:href"},
}

# CSS properties allowed to survive in a `style=` attribute. CSS cannot execute
# JS in modern browsers, but restricting to presentational properties blocks
# layout/overlay tricks (position, z-index, …). Covers the table layout
# (`width`) and inline-SVG styling an agent might use.
_ALLOWED_STYLE_PROPS: set[str] = {
    "width", "height", "color", "text-align", "fill", "fill-opacity",
    "fill-rule", "stroke", "stroke-width", "stroke-opacity", "stroke-linecap",
    "stroke-linejoin", "stroke-dasharray", "opacity", "font-size",
    "font-family", "font-weight", "font-style", "text-anchor", "stop-color",
    "stop-opacity",
}  # fmt: skip


def sanitize_html(html: str) -> str:
    """Return `html` with active content removed, safe structure preserved.

    Strips ``<script>`` (and its text), inline event handlers (``on*=``),
    ``javascript:`` / ``data:`` and other non-allowlisted URL schemes, and any
    tag/attribute outside the allowlist — while keeping the document body,
    tables, callouts, cards, verdicts, status chips, inline SVG illustrations,
    and the framework's HTML-comment anchors intact.

    Idempotent and safe on already-clean input; ``""`` in, ``""`` out.
    """
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=set(ALLOWED_TAGS),
        clean_content_tags=set(_CLEAN_CONTENT_TAGS),
        attributes={k: set(v) for k, v in ALLOWED_ATTRIBUTES.items()},
        filter_style_properties=set(_ALLOWED_STYLE_PROPS),
        # Keep the framework's `<!-- @anchor: ... -->` comments (inert in the
        # rendered HTML, but preserved so the output mirrors the source).
        strip_comments=False,
        # Don't inject rel="noopener noreferrer" onto every internal #anchor
        # link; the doc's links open in the same tab.
        link_rel=None,
        # url_schemes defaults to ammonia's vetted set (http/https/mailto/tel/…)
        # which excludes javascript: and data:.
    )
