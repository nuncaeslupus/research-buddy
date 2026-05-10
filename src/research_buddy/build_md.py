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
import html as html_lib
import json
import re
from typing import Any

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token
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
from research_buddy.table_layout import TableLayout, compute_layouts
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

    Custom render rules wrap each `<table>` in `<div class="table-wrap">` and
    apply per-table layouts (colgroup widths, `t-fixed` class, per-cell `nw`
    nowrap class) read from `env["_rb_layouts"]`. The layouts are computed
    globally across all tabs so structurally similar tables align — see
    `build_md_html`.
    """
    md = MarkdownIt("commonmark", {"html": True})
    md.enable("table")
    md.use(anchors_plugin, max_level=6, permalink=False)
    _install_table_layout_rules(md)
    return md


# ---------------------------------------------------------------------------
# Render rules: wrap tables and apply pre-computed layouts
# ---------------------------------------------------------------------------


def _install_table_layout_rules(md: MarkdownIt) -> None:
    """Override table_open, table_close, tr_open, td_open, th_open render
    rules so the rendered HTML carries the layouts stashed in `env`.

    Render-time state (current table index, current column index, current
    layout) flows through `env`, never closure-captured — the cached `md`
    instance is reused across builds, so each call must initialise its own
    counters.
    """

    # `add_render_rule` binds these as methods on the renderer, so each gets
    # the renderer as the first positional arg (we ignore it).

    def table_open(
        _self: Any, _tokens: list[Any], _idx: int, _opts: Any, env: dict[str, Any]
    ) -> str:
        layouts: list[TableLayout] = env.get("_rb_layouts") or []
        i = env.get("_rb_table_idx", 0)
        layout = layouts[i] if i < len(layouts) else None
        env["_rb_cur_layout"] = layout
        env["_rb_table_idx"] = i + 1
        cls = ' class="t-fixed"' if (layout and layout.use_fixed) else ""
        out = [f'<div class="table-wrap"><table{cls}>']
        if layout and layout.col_widths:
            ncols = len(layout.nowrap)
            out.append("<colgroup>")
            for j in range(ncols):
                w = layout.col_widths.get(j)
                out.append(f'<col style="width:{w}">' if w else "<col>")
            out.append("</colgroup>")
        return "".join(out) + "\n"

    def table_close(
        _self: Any, _tokens: list[Any], _idx: int, _opts: Any, _env: dict[str, Any]
    ) -> str:
        return "</table></div>\n"

    def tr_open(_self: Any, _tokens: list[Any], _idx: int, _opts: Any, env: dict[str, Any]) -> str:
        env["_rb_col_idx"] = 0
        return "<tr>"

    def td_open(_self: Any, _tokens: list[Any], _idx: int, _opts: Any, env: dict[str, Any]) -> str:
        layout: TableLayout | None = env.get("_rb_cur_layout")
        col = env.get("_rb_col_idx", 0)
        env["_rb_col_idx"] = col + 1
        if layout and col < len(layout.nowrap) and layout.nowrap[col]:
            return '<td class="nw">'
        return "<td>"

    def th_open(_self: Any, _tokens: list[Any], _idx: int, _opts: Any, env: dict[str, Any]) -> str:
        env["_rb_col_idx"] = env.get("_rb_col_idx", 0) + 1
        return "<th>"

    md.add_render_rule("table_open", table_open)
    md.add_render_rule("table_close", table_close)
    md.add_render_rule("tr_open", tr_open)
    md.add_render_rule("td_open", td_open)
    md.add_render_rule("th_open", th_open)


# ---------------------------------------------------------------------------
# v2 element catalog — closed list of rb-* primitives. The shape is fixed by
# starter.md's "Element catalog" section; this module is the renderer side of
# that contract.
# ---------------------------------------------------------------------------

# GFM-style admonitions (`> [!KIND]`). Five kinds match the GitHub default
# (NOTE/TIP/IMPORTANT/WARNING/CAUTION); LIMITATION and HYPOTHESIS are
# research-specific additions documented in the catalog.
_ADMONITION_KINDS: dict[str, tuple[str, str]] = {
    # KIND -> (css_modifier, glyph). The glyphs are deliberate Unicode
    # symbols (information sign, ballot check, star, warning sign, no entry,
    # flag) chosen to read in plain-text fallbacks too.
    "NOTE": ("note", "ℹ"),  # noqa: RUF001 — INFORMATION SOURCE, not Latin i
    "TIP": ("tip", "✓"),
    "IMPORTANT": ("important", "★"),
    "WARNING": ("warning", "⚠"),
    "CAUTION": ("caution", "⛔"),
    "LIMITATION": ("limitation", "⚑"),
    "HYPOTHESIS": ("hypothesis", "?"),
}

_VERDICT_KINDS = {
    "supports": "SUPPORTS",
    "contradicts": "CONTRADICTS",
    "unverifiable": "UNVERIFIABLE",
    "silent": "SILENT",
}

_BANNER_KINDS = {"usage", "agnostic", "cc"}

_ADMONITION_OPENER = re.compile(r"^(\s*)>\s*\[!([A-Z]+)\]\s*$")


def _expand_admonitions(text: str) -> str:
    """Rewrite GFM-admonition blockquotes into wrapper `<div class="callout …">`
    blocks containing plain Markdown body. The wrapper passes through markdown-it
    via `html=True`; the body is parsed normally so prose, lists, code and links
    inside an admonition keep working.

    Done at the text level (not the token level) because markdown-it-py's inline
    children can't be re-parsed cheaply after stripping the `[!KIND]` prefix —
    rewriting the surface text is the simplest correct transform.

    Lines inside fenced code blocks are left untouched.
    """
    lines = text.split("\n")
    if not any("[!" in ln for ln in lines):
        return text
    in_fence = _line_in_fence(lines)
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if in_fence[i]:
            out.append(lines[i])
            i += 1
            continue
        m = _ADMONITION_OPENER.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        kind_raw = m.group(2)
        kind_meta = _ADMONITION_KINDS.get(kind_raw)
        if kind_meta is None:
            out.append(lines[i])
            i += 1
            continue
        indent = m.group(1)
        cls, icon = kind_meta
        body_lines: list[str] = []
        i += 1
        while i < n and not in_fence[i]:
            stripped = lines[i].lstrip()
            if not stripped.startswith(">"):
                break
            body = stripped[1:]
            if body.startswith(" "):
                body = body[1:]
            body_lines.append(body)
            i += 1
        out.append(f'{indent}<div class="callout {cls}">')
        out.append(
            f'{indent}<div class="callout-title">'
            f'<span class="callout-icon">{icon}</span> {kind_raw}</div>'
        )
        out.append("")
        out.extend(body_lines)
        out.append("")
        out.append(f"{indent}</div>")
    return "\n".join(out)


def _md_render_inline(md: MarkdownIt, text: str) -> str:
    """Render Markdown for an *inline* slot — strip the outer `<p>` when the
    result is a single paragraph. Used for list items and verdict bodies that
    drop straight into a `<li>` / span context.

    NOT used for block-context bodies (cards, banners) — those go through
    `_md_render_body` so multi-paragraph content stays valid HTML; wrapping
    multiple `<p>` blocks in another `<p>` is invalid nesting.
    """
    if not text:
        return ""
    rendered = md.render(text).strip()
    m = re.fullmatch(r"<p>(.*?)</p>", rendered, re.DOTALL)
    return m.group(1) if m else rendered


def _md_render_body(md: MarkdownIt, text: str) -> str:
    """Render Markdown for a *block* slot — keep markdown-it's `<p>` wrapping
    intact so multi-paragraph content stays well-formed inside the surrounding
    `<div>` wrapper. The CSS targets `.card p`, `.agnostic p`, `.cc-banner p`
    so single-paragraph and multi-paragraph bodies render identically.
    """
    return md.render(text).strip() if text else ""


def _render_verdict(md: MarkdownIt, kind: str, body: str) -> str:
    badge = _VERDICT_KINDS.get(kind, kind.upper())
    # Verdict body sits inside `<div class="rb-verdict-body">` whose CSS
    # styles direct `<p>` children — keep markdown-it's wrapping.
    body_html = _md_render_body(md, body)
    return (
        f'<div class="rb-verdict {kind}">'
        f'<span class="verdict-badge {kind}">{badge}</span>'
        f'<div class="rb-verdict-body">{body_html}</div>'
        f"</div>"
    )


def _render_cards(md: MarkdownIt, body: str) -> str:
    try:
        cards = yaml.safe_load(body) or []
    except yaml.YAMLError:
        return f"<pre><code>{html_lib.escape(body)}</code></pre>"
    if not isinstance(cards, list):
        return f"<pre><code>{html_lib.escape(body)}</code></pre>"
    cls = "card-grid three" if len(cards) >= 3 else "card-grid"
    parts = [f'<div class="{cls}">']
    for card in cards:
        if not isinstance(card, dict):
            continue
        title = html_lib.escape(str(card.get("title", "")))
        icon = card.get("icon")
        body_md = str(card.get("body", ""))
        body_html = _md_render_body(md, body_md)
        if icon:
            icon_html = f'<span class="card-icon">{html_lib.escape(str(icon))}</span> '
            title_html = f"{icon_html}{title}"
        else:
            title_html = title
        parts.append(
            f'<div class="card"><div class="card-title">{title_html}</div>'
            f'<div class="card-body">{body_html}</div></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def _render_banner(md: MarkdownIt, kind: str, body: str) -> str:
    if kind not in _BANNER_KINDS:
        return f"<pre><code>{html_lib.escape(body)}</code></pre>"
    try:
        data = yaml.safe_load(body) or {}
    except yaml.YAMLError:
        return f"<pre><code>{html_lib.escape(body)}</code></pre>"
    if not isinstance(data, dict):
        data = {}
    title = html_lib.escape(str(data.get("title", "")))
    if kind == "usage":
        # `<li>` is an inline-context slot; strip the outer `<p>` for a clean
        # bullet line.
        items = data.get("items") or []
        items_html = "".join(f"<li>{_md_render_inline(md, str(i))}</li>" for i in items)
        return f'<div class="usage-banner"><h4>{title}</h4><ul>{items_html}</ul></div>'
    body_md = str(data.get("body", ""))
    body_html = _md_render_body(md, body_md)
    if kind == "agnostic":
        return (
            f'<div class="agnostic"><div class="ico">🌐</div>'
            f'<div><h4>{title}</h4><div class="banner-body">{body_html}</div></div></div>'
        )
    # kind == "cc"
    return (
        f'<div class="cc-banner"><div><h4>{title}</h4>'
        f'<div class="banner-body">{body_html}</div></div></div>'
    )


def _transform_rb_fences(tokens: list[Any], md: MarkdownIt) -> None:
    """Replace fence tokens whose info string starts with `rb-` with html_block
    tokens carrying the rendered HTML.

    Done at the token level (not the text level like admonitions) because the
    YAML body of `rb-cards` / `rb-banner` needs structured parsing, and
    `rb-verdict` body needs a recursive Markdown render that's easiest to drive
    via the same `md` instance.
    """
    for tok in tokens:
        if tok.type != "fence":
            continue
        info = (tok.info or "").strip()
        if not info.startswith("rb-"):
            continue
        parts = info.split(maxsplit=1)
        name = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""
        rendered: str | None
        if name == "rb-verdict" and arg in _VERDICT_KINDS:
            rendered = _render_verdict(md, arg, tok.content or "")
        elif name == "rb-cards":
            rendered = _render_cards(md, tok.content or "")
        elif name == "rb-banner" and arg in _BANNER_KINDS:
            rendered = _render_banner(md, arg, tok.content or "")
        else:
            continue
        tok.type = "html_block"
        tok.tag = ""
        tok.info = ""
        tok.content = rendered + "\n"
        tok.children = None


_REFERENCES_ANCHOR_RE = re.compile(r"<!--\s*@anchor:\s*references\s*-->", re.IGNORECASE)


def _references_tab_index(body: str) -> int | None:
    """Return the index of the tab whose H2 is preceded by
    `<!-- @anchor: references -->`, or None.

    The anchor convention places `<!-- @anchor: NAME -->` immediately *before*
    its `## NAME` heading. After splitting into tabs that comment lands at the
    end of the previous tab — invisible to the per-tab rendering pass. Detect
    the pattern up front and tell the right tab to start "armed" so the
    references list inside picks up its compact styling.
    """
    lines = body.split("\n")
    in_fence = _line_in_fence(lines)
    h2_re = re.compile(r"^##\s+\S")
    h2_count = 0
    armed = False
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        if _REFERENCES_ANCHOR_RE.search(line):
            armed = True
            continue
        if h2_re.match(line):
            if armed:
                return h2_count
            h2_count += 1
            armed = False
    return None


def _mark_references_list(tokens: list[Any], *, initial_armed: bool = False) -> None:
    """Add `class="references"` to the first `<ul>` after a
    `<!-- @anchor: references -->` HTML comment.

    The references anchor is part of the v2 framework — the agent has already
    placed the comment; this function only surfaces it as a visual cue so the
    renderer can give the bibliography compact list styling.

    `initial_armed=True` covers the convention-driven case where the anchor
    sits in the source *before* the tab's H2 and was therefore filtered out
    by `split_into_tabs` (see `_references_tab_index`).
    """
    armed = initial_armed
    for tok in tokens:
        if tok.type == "html_block" and _REFERENCES_ANCHOR_RE.search(tok.content or ""):
            armed = True
            continue
        if not armed:
            continue
        if tok.type == "bullet_list_open":
            existing = tok.attrs.get("class", "") if tok.attrs else ""
            new_cls = f"{existing} references".strip() if existing else "references"
            tok.attrSet("class", new_cls)
            armed = False
        elif tok.type in ("table_open", "ordered_list_open"):
            # If we hit another block-level element first, drop the arming —
            # the anchor was for documentation rather than a list directly
            # below it. Headings (H3 inside the references tab) are allowed
            # because the framework writes `### v1.0 — date` above the list.
            armed = False


# ---------------------------------------------------------------------------
# Frontmatter banners (top-of-doc chrome)
# ---------------------------------------------------------------------------


def _render_frontmatter_banners(md: MarkdownIt, banners: Any) -> str:
    """Render the optional `banners` frontmatter as HTML to inject above the
    first tab's content. Each entry is `{kind, title, body|items}` matching
    the rb-banner fenced shape; unknown kinds are skipped silently.
    """
    if not isinstance(banners, list):
        return ""
    parts: list[str] = []
    for entry in banners:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "")).strip().lower()
        if kind not in _BANNER_KINDS:
            continue
        # The fenced renderer takes a YAML body string; serialise the dict
        # back so a single _render_banner code path handles both.
        payload = {k: v for k, v in entry.items() if k != "kind"}
        parts.append(_render_banner(md, kind, yaml.safe_dump(payload, sort_keys=False)))
    return "".join(parts)


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


def _process_headings(tokens: list[Any], tab_num: str) -> list[dict[str, Any]]:
    """Walk tokens once, prepend `<span class="num">N.M</span>` to H3/H4
    inline content (matching v1's `<span class="num">` numbering), and return
    nav entries `{level, id, title, num}` for the sidebar.

    Counters reset per tab and within a tab as expected: H3 is `{tab}.{n}`,
    H4 is `{tab}.{n}.{m}` with `m` resetting at each new H3. An H4 appearing
    before any H3 (malformed nesting) is left unnumbered rather than
    fabricating a parent.
    """
    out: list[dict[str, Any]] = []
    h3 = 0
    h4 = 0
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open" or tok.tag not in ("h3", "h4"):
            continue
        level = int(tok.tag[1])
        if tok.tag == "h3":
            h3 += 1
            h4 = 0
            num = f"{tab_num}.{h3}"
        elif h3 == 0:
            num = ""
        else:
            h4 += 1
            num = f"{tab_num}.{h3}.{h4}"
        sid = (tok.attrs.get("id") or "") if tok.attrs else ""
        if i + 1 >= len(tokens) or tokens[i + 1].type != "inline":
            continue
        inline = tokens[i + 1]
        if num:
            span = Token("html_inline", "", 0)
            span.content = f'<span class="num">{num}</span> '
            inline.children = [span, *(inline.children or [])]
        if sid:
            out.append({"level": level, "id": str(sid), "title": inline.content, "num": num})
    return out


def _extract_table_cells(tokens: list[Any]) -> list[list[list[str]]]:
    """Return a list of tables; each table is a list of rows; each row is a
    list of cell-content strings, in render order.

    Headers and body rows are both included — width profiling treats every
    visible cell as content. The caller passes the resulting tables (across
    all tabs, in render order) to `compute_layouts`.
    """
    tables: list[list[list[str]]] = []
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i].type != "table_open":
            i += 1
            continue
        rows: list[list[str]] = []
        current: list[str] = []
        in_row = False
        j = i + 1
        while j < n and tokens[j].type != "table_close":
            t = tokens[j]
            if t.type == "tr_open":
                current = []
                in_row = True
            elif t.type == "tr_close":
                if in_row:
                    rows.append(current)
                in_row = False
            elif t.type == "inline":
                current.append(t.content)
            j += 1
        tables.append(rows)
        i = j + 1
    return tables


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
    body = _expand_admonitions(body)
    references_idx = _references_tab_index(body)
    tabs = split_into_tabs(body)
    if not tabs:
        # Nothing to render as a tab — emit a single tab carrying the whole
        # body. Keeps the chrome consistent with the JSON pipeline.
        tabs = [("Document", body.strip())]

    state = BuildState()
    md = _md_renderer()
    banners_html = _render_frontmatter_banners(md, fm.get("banners"))

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

    # ── parse pass: tokenize each tab, dedupe heading IDs, number H3/H4,
    # collect every table's cells globally so layouts can group similar
    # tables across the whole document ────────────────────────────────────
    parsed: list[tuple[list[Any], list[dict[str, Any]], int, int]] = []
    all_tables: list[list[list[str]]] = []
    for i, (label, tab_md) in enumerate(tabs):
        tab_num = str(i + 1)
        tokens = md.parse(tab_md)
        _transform_rb_fences(tokens, md)
        _mark_references_list(tokens, initial_armed=(i == references_idx))
        _dedupe_heading_ids(tokens, state)
        nav_entries = _process_headings(tokens, tab_num)
        tab_tables = _extract_table_cells(tokens)
        layout_start = len(all_tables)
        all_tables.extend(tab_tables)
        parsed.append((tokens, nav_entries, layout_start, len(all_tables)))
        del label, tab_md  # avoid accidental reuse — see render pass below

    global_layouts = compute_layouts(all_tables)

    # ── render pass: emit per-tab content + sidebar nav ────────────────────
    nav_html_parts: list[str] = []
    tab_contents: list[str] = []

    for i, ((label, _tab_md), tid, rendered_label, (tokens, nav_entries, lo, hi)) in enumerate(
        zip(tabs, tab_ids, rendered_labels, parsed, strict=True)
    ):
        is_active = i == 0
        active_cls = " active" if is_active else ""
        tab_num = str(i + 1)
        tab_hdr_id = state.unique_id(f"tab-hdr-{tid}")

        env: dict[str, Any] = {
            "_rb_layouts": global_layouts[lo:hi],
            "_rb_table_idx": 0,
        }
        body_html = md.renderer.render(tokens, md.options, env)

        # Frontmatter `banners` render above the first tab's content only —
        # they're top-of-doc chrome, not per-tab decoration.
        banners_block = banners_html if (i == 0 and banners_html) else ""

        tab_body = (
            f'<h1 id="{tab_hdr_id}">{tab_num}. {rendered_label}</h1>\n'
            f"{banners_block}"
            f"{body_html}\n"
            f'<p style="text-align:center;color:var(--text3);font-size:12px;padding:16px 0">'
            f"{doc_title} · {rendered_label} · v{ver}</p>\n"
        )

        # sidebar nav for this tab
        nav_html = [f'<nav class="tab-nav{active_cls}" data-for="{tid}">\n']
        nav_html.append(f'<a href="#{tab_hdr_id}">{tab_num}. {rendered_label}</a>\n')
        for entry in nav_entries:
            cls = ' class="sub"' if entry["level"] == 3 else ' class="subsub"'
            num_prefix = f"{entry['num']}. " if entry["num"] else ""
            nav_html.append(f'<a href="#{entry["id"]}"{cls}>{num_prefix}{entry["title"]}</a>\n')
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
