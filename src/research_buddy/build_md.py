"""Build single-file HTML from a v2 Markdown research document.

Mirrors the chrome of `build.py` (tab bar, sidebar nav, hljs, theme toggle,
Research Buddy footer) so v1-JSON-built and v2-MD-built documents look the
same in a browser.

Mapping:
- YAML frontmatter → page title / version / date / lang.
- Each top-level H2 in the body → one tab. Tab id = slug of the H2 text.
- H3 / H4 headings within a tab → sidebar nav entries.
- Markdown body of each tab is rendered with markdown-it-py + GFM tables.
  Raw HTML (e.g. `<a id="...">`, `<!-- @anchor: ... -->`) passes through.

Public entry point: `build_md_html(text, *, theme_css=None) -> str`.
"""

from __future__ import annotations

import functools
import json
import re
from typing import Any

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin

from research_buddy.build import (
    _RB_FOOTER_CSS,
    BuildState,
    _build_rb_footer_html,
    _get_env,
    _load_asset,
    _resolve_lang_code,
)
from research_buddy.clean_md import (
    collect_framework_targets,
    parse_frontmatter,
    strip_framework_block,
    unwrap_framework_links,
)
from research_buddy.validator_md import _line_in_fence

# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _md_renderer() -> MarkdownIt:
    """A configured markdown-it-py instance.

    Cached for the lifetime of the process — building one is cheap but not
    free, and `build_md_html` is called once per document. `html=True` lets
    raw HTML (`<a id>`, anchor comments, inline images) flow through. The
    anchors plugin assigns slug IDs to H1-H6 so sidebar links resolve.
    """
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("table")
    md.use(anchors_plugin, max_level=6, permalink=False)
    return md


# ---------------------------------------------------------------------------
# Body splitting (fence-aware)
# ---------------------------------------------------------------------------


def split_into_tabs(body: str) -> list[tuple[str, str]]:
    """Split the body on top-level H2 headings.

    Returns a list of (heading_text, body_md) pairs. Content before the first
    H2 is dropped — `build_md` always renders the title block separately
    from the chrome, and the v2 source always opens with the title block.

    Fenced code blocks are respected: `## ` lines inside ``` fences do not
    split tabs.
    """
    lines = body.splitlines()
    in_fence = _line_in_fence(lines)
    h2_re = re.compile(r"^##\s+(.+?)\s*$")

    tabs: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    current_title: str | None = None

    for i, line in enumerate(lines):
        if in_fence[i]:
            if current is not None:
                current.append(line)
            continue
        m = h2_re.match(line)
        if m:
            if current is not None and current_title is not None:
                tabs.append((current_title, current))
            current_title = m.group(1).strip()
            current = []
            continue
        if current is not None:
            current.append(line)

    if current is not None and current_title is not None:
        tabs.append((current_title, current))

    return [(title, "\n".join(body_lines).strip("\n")) for title, body_lines in tabs]


# ---------------------------------------------------------------------------
# Sidebar nav extraction
# ---------------------------------------------------------------------------


def _extract_nav_entries(tokens: list[Any]) -> list[dict[str, Any]]:
    """Walk a parsed token stream and return a list of {level, id, title}
    dicts for every H3/H4 heading.

    The caller parses once and passes the tokens to both `md.renderer.render`
    and this helper, so we don't pay for parsing twice. The anchors plugin
    has already assigned `id` attributes by the time this runs.
    """
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open" and tok.tag in ("h3", "h4"):
            level = int(tok.tag[1])
            sid = (tok.attrs.get("id") or "") if tok.attrs else ""
            # The next token is `inline` with the heading content.
            title = ""
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                title = tokens[i + 1].content
            if sid:
                out.append({"level": level, "id": str(sid), "title": title})
        i += 1
    return out


def _dedupe_heading_ids(tokens: list[Any], state: BuildState) -> None:
    """Mutate `tokens` so heading IDs are globally unique across tabs.

    The anchors plugin restarts its slug set per `parse()` call, so two
    `### Domain` headings in different tabs both get `id="domain"` and the
    first one swallows every cross-link. Run each heading's slug through
    `BuildState.unique_id` (shared across all tabs) so a repeat becomes
    `domain-2`, `domain-3`, etc. Same dedup model `build.py` uses for v1.
    """
    for tok in tokens:
        if tok.type != "heading_open" or not tok.attrs:
            continue
        sid = tok.attrs.get("id")
        if not sid:
            continue
        unique = state.unique_id(str(sid))
        if unique != sid:
            tok.attrs["id"] = unique


# ---------------------------------------------------------------------------
# Slugs (also used to derive tab IDs)
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "tab"


# ---------------------------------------------------------------------------
# Top-level entry
# ---------------------------------------------------------------------------


def build_md_html(
    text: str,
    *,
    theme_css: str | None = None,
    keep_framework: bool = False,
) -> str:
    """Render a v2 Markdown source document as a single-file HTML page.

    By default the framework block is stripped and links into it are unwrapped,
    matching the JSON pipeline's `starter.html` (which never renders
    `agent_guidelines.framework`). Pass `keep_framework=True` to render the
    full agent-facing source with the framework visible.

    Args:
        text: Full v2 Markdown source (with YAML frontmatter).
        theme_css: Optional extra CSS appended after the default stylesheet.
        keep_framework: When True, render the framework block as content tabs.
    """
    fm, body_start_idx = parse_frontmatter(text)
    fm = fm or {}

    if not keep_framework:
        framework_targets = collect_framework_targets(text)
        text = strip_framework_block(text)
        text = unwrap_framework_links(text, framework_targets)
        # The frontmatter index from the original text isn't valid after
        # the framework strip rewrites the body. Re-derive.
        _, body_start_idx = parse_frontmatter(text)

    # Starter-mode fallbacks: when frontmatter fields are null (the agent
    # hasn't filled them in yet), emit the same "[FILL in session_zero …]"
    # placeholders the v1 JSON starter uses. Keeps the unconfigured-starter
    # render legible side-by-side with starter.html.
    starter_mode = ((fm.get("project") or {}).get("domain")) is None
    fill_placeholder = "[FILL in session_zero]"

    def _or_fill(value: Any, label: str) -> str:
        if value:
            return str(value)
        return f"[FILL in session_zero: {label}]" if starter_mode else ""

    doc_title = _or_fill(fm.get("title"), "Project Name") or "Research Document"
    short_title = fm.get("subtitle") or doc_title
    ver = fm.get("version") or (fill_placeholder if starter_mode else "")
    date = fm.get("date") or (fill_placeholder if starter_mode else "")

    body = "\n".join(text.splitlines()[body_start_idx:]) if body_start_idx else text
    tabs = split_into_tabs(body)
    if not tabs:
        # Nothing to render as a tab — emit a single tab carrying the whole
        # body. Keeps the chrome consistent with the JSON pipeline.
        tabs = [("Document", body.strip())]

    state = BuildState()
    md = _md_renderer()

    # ── tab bar ────────────────────────────────────────────────────────────
    # Tab IDs are derived from the raw label (data-tab attribute must be a
    # plain slug); button text is rendered through markdown-it so inline
    # markup like *italics* works and HTML special chars get escaped.
    tab_ids: list[str] = []
    rendered_labels: list[str] = []
    tab_btns: list[str] = []
    for i, (label, _) in enumerate(tabs):
        tid = state.unique_id(_slugify(label))
        tab_ids.append(tid)
        rendered_label = md.renderInline(label)
        rendered_labels.append(rendered_label)
        active = " active" if i == 0 else ""
        tab_btns.append(
            f'<button class="tab-btn{active}" data-tab="{tid}">{rendered_label}</button>'
        )

    tab_bar = (
        '<div id="tab-bar">\n'
        '<button id="menu-toggle" aria-label="Menu">☰</button>\n'
        + "\n".join(tab_btns)
        + '\n<button id="theme-toggle" aria-label="Toggle theme" title="Toggle theme">☾</button>'
        + "</div>\n"
    )

    # ── per-tab content + sidebar nav ──────────────────────────────────────
    nav_html_parts: list[str] = []
    tab_contents: list[str] = []

    for i, ((label, tab_md), tid, rendered_label) in enumerate(
        zip(tabs, tab_ids, rendered_labels, strict=True)
    ):
        is_active = i == 0
        active_cls = " active" if is_active else ""
        tab_num = str(i + 1)
        tab_hdr_id = state.unique_id(f"tab-hdr-{tid}")

        # Parse once — the same tokens feed both the renderer and the nav
        # extractor. `_dedupe_heading_ids` rewrites collisions with the
        # shared `state` so IDs are globally unique across tabs.
        tokens = md.parse(tab_md)
        _dedupe_heading_ids(tokens, state)
        body_html = md.renderer.render(tokens, md.options, {})
        nav_entries = _extract_nav_entries(tokens)

        tab_body = (
            f'<h1 id="{tab_hdr_id}">{tab_num}. {rendered_label}</h1>\n'
            f"{body_html}\n"
            f'<p style="text-align:center;color:var(--text3);font-size:12px;padding:16px 0">'
            f"{doc_title} · {rendered_label} · v{ver}</p>\n"
        )

        # sidebar nav for this tab
        nav_html = [f'<nav class="tab-nav{active_cls}" data-for="{tid}">\n']
        nav_html.append(f'<a href="#{tab_hdr_id}">{tab_num}. {rendered_label}</a>\n')
        for entry in nav_entries:
            cls = ' class="sub"' if entry["level"] == 3 else ' class="subsub"'
            nav_html.append(f'<a href="#{entry["id"]}"{cls}>{entry["title"]}</a>\n')
        nav_html.append("</nav>\n")
        nav_html_parts.append("".join(nav_html))

        tab_contents.append(
            f'<div id="tab-{tid}" class="tab-content{active_cls}" data-tab-label="{label}">\n'
            f'<div class="content">\n{tab_body}</div></div>\n'
        )

    sidebar = (
        '<div id="sidebar">\n'
        f'<div class="sidebar-hdr">{short_title}'
        f"<span>v{ver} · {date}</span></div>\n{''.join(nav_html_parts)}</div>\n"
    )

    # ── chrome assembly ────────────────────────────────────────────────────
    lang_code = _resolve_lang_code(
        {"language": fm.get("language") or {"code": "en", "label": "English"}}
    )
    rb_footer_html = _build_rb_footer_html(
        {"research_buddy_version": fm.get("research_buddy_version", "")}
    )

    body_content = (
        tab_bar
        + '<div id="layout">\n'
        + sidebar
        + '<div id="main">\n'
        + "".join(tab_contents)
        + rb_footer_html
        + "</div>\n</div>\n"
    )

    css = _load_asset("style.css", "css")
    js = _load_asset("script.js", "js")
    hljs_css = _load_asset("highlight-theme.min.css", "lib")
    hljs_js = _load_asset("highlight.min.js", "lib")

    js = re.sub(
        r"/\*TABS_INJECT\*/.*?/\*END_INJECT\*/",
        lambda _: f"/*TABS_INJECT*/{json.dumps(tab_ids)}/*END_INJECT*/",
        js,
    )

    theme_block = f"\n/* ── Theme overrides ── */\n{theme_css}" if theme_css else ""
    theme_block += _RB_FOOTER_CSS

    return (
        _get_env()
        .get_template("base.html.j2")
        .render(
            lang_code=lang_code,
            doc_title=doc_title,
            ver=ver,
            hljs_css=hljs_css,
            css=css,
            theme_block=theme_block,
            body_content=body_content,
            hljs_js=hljs_js,
            js=js,
        )
    )
