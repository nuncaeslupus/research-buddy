"""Core HTML builder — converts a structured JSON document into a single-file HTML page."""

from __future__ import annotations

import base64
import functools
import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

import jinja2

# ── Type aliases ────────────────────────────────────────────────────────────

Block = dict[str, Any]
Doc = dict[str, Any]

# ── Constants ───────────────────────────────────────────────────────────────

VALID_TAG_CLASSES = frozenset(
    {
        "tag-blue",
        "tag-green",
        "tag-amber",
        "tag-red",
        "tag-teal",
        "tag-purple",
        "phase-1",
        "phase-2",
        "cloud",
        "skip",
        "tag",
    }
)

MAX_NOWRAP_COLUMN_LENGTH = 30

# Mapping of human-readable language names to BCP-47 codes, for documents that use
# `meta.language` as a plain string (e.g. "English") instead of the preferred
# {"code": "en", "label": "English"} form. Falls back to a best-effort slug.
_LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "spanish": "es",
    "español": "es",
    "castellano": "es",
    "french": "fr",
    "français": "fr",
    "german": "de",
    "deutsch": "de",
    "italian": "it",
    "italiano": "it",
    "portuguese": "pt",
    "português": "pt",
    "chinese": "zh",
    "中文": "zh",
    "japanese": "ja",
    "日本語": "ja",
    "korean": "ko",
    "한국어": "ko",
    "arabic": "ar",
    "العربية": "ar",
    "russian": "ru",
    "русский": "ru",
    "dutch": "nl",
    "nederlands": "nl",
    "polish": "pl",
    "polski": "pl",
}

_RB_FOOTER_CSS = """
/* ── Research Buddy footer ── */
.rb-powered-by{display:flex;align-items:center;justify-content:center;gap:16px;padding:20px;font-size:12px;color:var(--text3);clear:both}
.rb-logo{width:100px;height:auto}
.rb-powered-by a{color:var(--text3);text-decoration:none}
.rb-powered-by a:hover{color:var(--text2)}
@media print{.rb-powered-by{display:none}}
"""

# ── State Management ────────────────────────────────────────────────────────


class BuildState:
    """Tracks state during a single build pass, primarily for unique ID generation."""

    def __init__(self) -> None:
        self.used_ids: set[str] = set()

    def unique_id(self, base: str) -> str:
        """Generate a unique ID by appending a counter if the base is already taken."""
        if not base:
            base = "id"
        candidate = base
        counter = 2
        while candidate in self.used_ids:
            candidate = f"{base}-{counter}"
            counter += 1
        self.used_ids.add(candidate)
        return candidate


# ── Assets ──────────────────────────────────────────────────────────────────


def _load_asset(name: str, subdir: str = "") -> str:
    """Load a bundled asset file from the package."""
    if subdir:
        ref = resources.files("research_buddy") / subdir / name
    else:
        ref = resources.files("research_buddy") / name
    return ref.read_text(encoding="utf-8")


def _load_binary_asset(name: str, subdir: str = "") -> bytes:
    """Load a bundled binary asset from the package."""
    if subdir:
        ref = resources.files("research_buddy") / subdir / name
    else:
        ref = resources.files("research_buddy") / name
    return ref.read_bytes()


def _asset_to_base64(data: bytes, mime: str) -> str:
    """Convert binary data to base64 data URL."""
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ── Jinja environment ───────────────────────────────────────────────────────

# autoescape=False matches the historical behaviour: r_svg embeds caller-provided
# HTML verbatim and md()/title fields are interpolated raw. The trust assumption
# is documented in starter.json's agent_guidelines (no JS in svg blocks).


@functools.lru_cache(maxsize=1)
def _get_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.PackageLoader("research_buddy", "templates"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.globals["md"] = md
    env.filters["md"] = md
    return env


@functools.lru_cache(maxsize=1)
def _block_macros() -> Any:
    """Return the imported module of blocks.html.j2, exposing macros as attributes."""
    return _get_env().get_template("blocks.html.j2").module


# ── Inline Markdown → HTML ──────────────────────────────────────────────────


def md(text: str) -> str:
    """Convert inline markdown + custom tags to HTML."""
    if not text:
        return ""
    t = text

    # [tag:classnames]text[/tag]
    def _render_tag(m: re.Match[str]) -> str:
        cls = m.group(1).strip()
        inner = m.group(2)
        keep = [c for c in cls.split() if c in VALID_TAG_CLASSES]
        if not keep:
            keep = ["tag", "tag-blue"]
        if "tag" not in keep:
            keep.insert(0, "tag")
        return f'<span class="{" ".join(keep)}">{inner}</span>'

    t = re.sub(r"\[tag:([^\]]*)\](.+?)\[/tag\]", _render_tag, t)

    # xlinks: [label](href){tab=tabid}
    def _render_xlink(m: re.Match[str]) -> str:
        label, href, tab = m.group(1), m.group(2), m.group(3)
        return f'<a href="#{href.lstrip("#")}" class="xlink" data-tab="{tab}">{label}</a>'

    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)\{tab=([^}]+)\}", _render_xlink, t)

    # regular links
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)

    # bold+italic, bold, italic
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)

    # inline code
    def _code_span(m: re.Match[str]) -> str:
        inner = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<code>{inner}</code>"

    t = re.sub(r"`([^`]+)`", _code_span, t)
    return t


def slugify(text: str) -> str:
    """Convert a title into a URL-friendly ID."""
    t = str(text).lower()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", "-", t)
    t = t.strip("-")
    return t or "sec"


def md_block(text: str) -> str:
    """Convert a text block that may contain paragraph-separated sections."""
    if not text:
        return ""
    parts = text.split("\n\n")
    if len(parts) == 1:
        return md(text)
    return "".join(f"<p>{md(p.strip())}</p>" for p in parts if p.strip())


# ── Block renderers ─────────────────────────────────────────────────────────


def r_p(b: Block, _state: BuildState) -> str:
    return str(_block_macros().p(md_html=md(b.get("md", "")), style=b.get("style")))


def r_h3(b: Block, state: BuildState) -> str:
    sid = state.unique_id(b.get("id") or slugify(b.get("md", "")))
    return str(
        _block_macros().h3(sid=sid, md_html=md(b.get("md", "")), badge=b.get("badge"))
    )


def r_h4(b: Block, state: BuildState) -> str:
    sid = state.unique_id(b.get("id") or slugify(b.get("md", "")))
    return str(_block_macros().h4(sid=sid, md_html=md(b.get("md", ""))))


def r_heading(b: Block, state: BuildState) -> str:
    """Render a 'heading' block: {type, level, content}."""
    level = b.get("level", 3)
    tag = f"h{level}" if level in (3, 4) else "h3"
    text = b.get("content", "") or b.get("md", "")
    sid = state.unique_id(b.get("id") or slugify(text))
    return str(_block_macros().heading(tag=tag, sid=sid, md_html=md(text)))


def r_paragraph(b: Block, _state: BuildState) -> str:
    """Render a 'paragraph' block: {type, content}."""
    text = b.get("content", "") or b.get("md", "")
    return str(_block_macros().p(md_html=md(text), style=b.get("style")))


def r_hr(_b: Block, _state: BuildState) -> str:
    return str(_block_macros().hr())


def r_ul(b: Block, _state: BuildState) -> str:
    items_html = [md(i) for i in b.get("items", [])]
    return str(_block_macros().ul(items_html=items_html))


def r_ol(b: Block, _state: BuildState) -> str:
    items_html = [md(i) for i in b.get("items", [])]
    return str(_block_macros().ol(items_html=items_html))


def r_code(b: Block, _state: BuildState) -> str:
    lang = b.get("lang") or ""
    # Accept both "text" and legacy "content"/"md" field names
    text = b.get("text") or b.get("content") or b.get("md") or ""
    if not lang:
        # Require at least two Python-specific signals to avoid mis-classifying
        # JSON/YAML/shell blocks that happen to contain a bare "# comment"
        py_signals = sum(
            [
                "def " in text,
                "import " in text,
                "class " in text,
                text.lstrip().startswith("# "),
            ]
        )
        if py_signals >= 2:
            lang = "python"
    code = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lang_attr = f' data-lang="{lang}"' if lang else ""
    lang_cls = f' class="language-{lang}"' if lang else ""
    return (
        f'<div class="code-wrap"{lang_attr}>'
        f'<button class="copy-btn" title="Copy">⎘</button>'
        f"<pre><code{lang_cls}>{code}</code></pre>"
        f"</div>\n"
    )


def r_callout(b: Block, _state: BuildState) -> str:
    variant = b.get("variant", "blue")
    cls = f"callout {variant}" if variant != "blue" else "callout"
    return str(
        _block_macros().callout(cls=cls, title=b.get("title", ""), md_html=md(b.get("md", "")))
    )


def r_verdict(b: Block, _state: BuildState) -> str:
    badge = b.get("badge", "reject")
    badge_text = b.get("badge_text", badge.upper())
    return str(
        _block_macros().verdict(
            badge=badge,
            badge_text=badge_text,
            label_html=md(b.get("label", "")),
            text_html=md(b.get("md", "")),
        )
    )


def _nowrap_cols(headers: list[str], rows: list[list[str]]) -> list[bool]:
    ncols = len(headers) or (len(rows[0]) if rows else 0)
    if ncols == 0:
        return []
    maxes = [0] * ncols
    for row in rows:
        for i, cell in enumerate(row[:ncols]):
            maxes[i] = max(maxes[i], len(cell))
    return [mx < MAX_NOWRAP_COLUMN_LENGTH for mx in maxes]


def _table_col_widths(headers: list[str], ncols: int) -> tuple[dict[int, str], bool]:
    if not headers or ncols == 0:
        return {}, False
    h = " ".join(headers).lower()

    # # | Build | Test condition to pass | Time
    if "build" in h and "test condition" in h:
        return {0: "4%", 1: "26%", 3: "10%"}, True

    # # | Build | Activation condition  (Phase 2 table)
    if "build" in h and "activation condition" in h:
        return {0: "4%", 1: "20%"}, True

    # Phase / barrier control
    if "phase" in h and "who controls barriers" in h:
        return {1: "22%"}, True

    # Problem / root-cause  OR  proposal / rationale
    if ("problem" in h and "root" in h) or ("proposal" in h and "rationale" in h):
        return {0: "25%", 1: "25%"}, True

    # Source | Tier | Relevance  (research session citation tables)
    if h.strip().startswith("source") and "tier" in h and "relevance" in h:
        return {0: "48%", 1: "8%", 2: "44%"}, True

    # Source | Tier | Adopted claims | Rejected/flagged claims
    if "source" in h and "tier" in h and "adopted" in h:
        return {0: "28%", 1: "7%", 2: "32%", 3: "33%"}, True

    # Source | Role in system  (reference role tables)
    if "source" in h and "role" in h and ncols == 2:
        return {0: "45%", 1: "55%"}, True

    # Reference | Used for
    if "reference" in h and "used for" in h:
        return {0: "42%", 1: "58%"}, True

    # Citation | What it supports
    if "citation" in h and "supports" in h:
        return {0: "42%", 1: "58%"}, True

    # Concept (full name) | What it does | Why ...  (Concept Map tables)
    if "concept" in h and "what it does" in h:
        return {0: "22%", 1: "39%", 2: "39%"}, True

    # Concept | Status | Session finding  (Tracker tables)
    if "concept" in h and "status" in h and "session" in h:
        return {0: "28%", 1: "12%", 2: "60%"}, True

    # Decision | Adopted spec | Rationale
    if "decision" in h and "adopted spec" in h:
        return {0: "18%", 1: "42%", 2: "40%"}, True

    # Verdict / rejection tables (Discarded Alternatives etc.)
    REJECTION_WORDS = (
        "rejected",
        "verdict",
        "alternative",
        "discarded",
        "approach",
        "why",
        "decision",
        "status",
    )
    if any(w in h for w in REJECTION_WORDS):
        if ncols == 2:
            return {0: "35%", 1: "65%"}, True
        if ncols == 3:
            return {0: "30%", 1: "18%", 2: "52%"}, True
        if ncols == 4:
            return {0: "26%", 1: "14%", 2: "14%", 3: "46%"}, True

    return {}, False


def r_table(b: Block, _state: BuildState) -> str:
    headers = b.get("headers", [])
    rows = b.get("rows", [])
    ncols = len(headers) or (len(rows[0]) if rows else 0)
    nowrap = _nowrap_cols(headers, rows)

    col_widths, use_fixed = _table_col_widths(headers, ncols)

    # <colgroup><col> is more reliable than per-<th> style for fixed layout
    colgroup = ""
    if col_widths:
        cols_html = "".join(
            f'<col style="width:{col_widths[i]}">' if i in col_widths else "<col>"
            for i in range(ncols)
        )
        colgroup = f"<colgroup>{cols_html}</colgroup>\n"

    table_cls = ' class="t-fixed"' if use_fixed else ""

    thead = ""
    if headers:
        ths = "".join(f"<th>{md(h)}</th>" for h in headers)
        thead = f"<thead><tr>{ths}</tr></thead>\n"

    tbody_rows = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            nw = ' class="nw"' if i < len(nowrap) and nowrap[i] else ""
            cells.append(f"<td{nw}>{md(cell)}</td>")
        tbody_rows.append(f"<tr>{''.join(cells)}</tr>\n")
    tbody = f"<tbody>\n{''.join(tbody_rows)}</tbody>\n"

    return f'<div class="table-wrap"><table{table_cls}>\n{colgroup}{thead}{tbody}</table></div>\n'


def r_svg(b: Block, _state: BuildState) -> str:
    return f'<div class="diagram-wrap">{b.get("html", "")}</div>\n'


def r_usage_banner(b: Block, _state: BuildState) -> str:
    items_html = [md(i) for i in b.get("items", [])]
    return str(_block_macros().usage_banner(title=b.get("title", ""), items_html=items_html))


def r_agnostic_banner(b: Block, _state: BuildState) -> str:
    return str(
        _block_macros().agnostic_banner(
            title=b.get("title", ""), md_html=md(b.get("md", ""))
        )
    )


def r_cc_banner(b: Block, _state: BuildState) -> str:
    return str(
        _block_macros().cc_banner(title=b.get("title", ""), md_html=md(b.get("md", "")))
    )


def r_phase_cards(b: Block, _state: BuildState) -> str:
    cards_html = ""
    for card in b.get("cards", []):
        phase = card.get("phase", "p1")
        title = card.get("title", "")
        items = card.get("items", [])
        items_html = "".join(f"<li>{md(i)}</li>\n" for i in items)
        cards_html += (
            f'<div class="phase-card {phase}"><h4>{md(title)}</h4><ul>{items_html}</ul></div>\n'
        )
    return f'<div class="phase-bar">\n{cards_html}</div>\n'


def r_card_grid(b: Block, _state: BuildState) -> str:
    cols = b.get("cols", 2)
    extra = " three" if cols == 3 else ""
    cards_html = ""
    for card in b.get("cards", []):
        title_val = card.get("title", "")
        md_val = card.get("md", "")
        cards_html += (
            f'<div class="card">'
            f'<div class="card-title">{md(title_val)}</div>'
            f"<p>{md(md_val)}</p>"
            f"</div>\n"
        )
    return f'<div class="card-grid{extra}">\n{cards_html}</div>\n'


def r_references(b: Block, _state: BuildState) -> str:
    """Render a 'references' block."""
    items_html = ""
    for item in b.get("items", []):
        ver = item.get("version", "")
        date = item.get("date", "")
        text = item.get("text", "")
        ver_tag = f'<span class="tag tag-blue">{ver}</span> ' if ver else ""
        date_tag = f'<span class="date">{date}</span> ' if date else ""
        items_html += f"<li>{ver_tag}{date_tag}{md(text)}</li>\n"
    return f'<ul class="references">\n{items_html}</ul>\n'


BLOCK_RENDERERS: dict[str, Any] = {
    "p": r_p,
    "h3": r_h3,
    "h4": r_h4,
    "heading": r_heading,
    "paragraph": r_paragraph,
    "hr": r_hr,
    "ul": r_ul,
    "ol": r_ol,
    "code": r_code,
    "callout": r_callout,
    "verdict": r_verdict,
    "table": r_table,
    "svg": r_svg,
    "usage_banner": r_usage_banner,
    "agnostic_banner": r_agnostic_banner,
    "cc_banner": r_cc_banner,
    "phase_cards": r_phase_cards,
    "card_grid": r_card_grid,
    "references": r_references,
}


def render_blocks(blocks: list[Block], state: BuildState, include_agent_only: bool = False) -> str:
    out: list[str] = []
    for b in blocks:
        if not include_agent_only and b.get("agent_only"):
            continue
        renderer = BLOCK_RENDERERS.get(b.get("type", ""))
        if renderer:
            out.append(renderer(b, state))
        else:
            out.append(f"<!-- unknown block type: {b.get('type')} -->\n")
    return "".join(out)


# ── Section rendering ───────────────────────────────────────────────────────


def render_section(
    title: str,
    sec: Doc,
    state: BuildState,
    nav_list: list[dict[str, Any]],
    level: int = 2,
    number: str = "",
    meta: Doc | None = None,
) -> str:
    """Render a section and its subsections recursively.

    Unique IDs are added to nav_list for sidebar generation.
    """
    sid = state.unique_id(sec.get("changelog_id") or slugify(title))
    subtitle = sec.get("subtitle", "")

    title_page_title = (meta or {}).get("title_page_section_title", "")
    is_title_page = level == 2 and title == title_page_title

    h_tag = f"h{level}" if level <= 4 else "h4"

    display_title = md(title)
    if subtitle:
        sep = "" if subtitle.startswith("\u2014") or subtitle.startswith("-") else " \u2014 "
        display_title += f' <span class="subtitle">{sep}{md(subtitle)}</span>'

    if sec.get("current"):
        display_title += ' <span class="tag tag-green">Current</span>'

    num_html = f'<span class="num">{number}</span> ' if number else ""

    if is_title_page:
        doc_title = (meta or {}).get("title", "Documentation")
        doc_subtitle = (meta or {}).get("subtitle", "")
        ver = (meta or {}).get("version", "")
        date = (meta or {}).get("date", "")
        ver_line = f"<p><strong>Version:</strong> v{ver} \u2014 {date}</p>\n" if ver else ""
        sub_line = f'<p class="subtitle">{doc_subtitle}</p>\n' if doc_subtitle else ""
        heading = f"<h1>{doc_title}</h1>\n{sub_line}{ver_line}"
        open_tag = f'<div id="{sid}" class="title-page">\n{heading}'
        close_tag = "</div>\n"
    else:
        h_html = f"<{h_tag}>{num_html}{display_title}</{h_tag}>\n"
        tag = "section" if level == 2 else "div"
        open_tag = f'<{tag} id="{sid}" class="level-{level}">\n{h_html}'
        close_tag = f"</{tag}>\n"

    # Add this section to navigation
    nav_list.append({"id": sid, "num": number, "title": title, "level": level})

    body = render_blocks(sec.get("blocks", []), state)

    sub_html_parts = []
    subsections = sec.get("subsections", {})
    if subsections:
        for i, (sub_title, sub_sec) in enumerate(subsections.items(), 1):
            sub_num = f"{number}.{i}" if number else str(i)
            sub_content = render_section(
                sub_title, sub_sec, state, nav_list, level + 1, sub_num, meta
            )
            sub_html_parts.append(sub_content)

    return f"{open_tag}{body}{''.join(sub_html_parts)}{close_tag}"


# ── HTML assembly ───────────────────────────────────────────────────────────


def find_latest_json(source_dir: Path) -> Path | None:
    """Find the highest-versioned *_vX.Y.json in a directory, or research-document.json fallback.

    Matches any file ending in _vX.Y.json (e.g. myproject_v1.2.json, document_v3.0.json).
    Falls back to research-document.json for unversioned template files.
    """
    candidates = [p for p in source_dir.glob("*.json") if re.search(r"_v\d+[_.]\d+\.json$", p.name)]
    if candidates:

        def ver_key(p: Path) -> tuple[int, int]:
            m = re.search(r"v(\d+)[_.](\d+)", p.name)
            return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

        return sorted(candidates, key=ver_key)[-1]

    # Fallback: unversioned template
    fallback = source_dir / "research-document.json"
    if fallback.exists():
        return fallback

    return None


def _resolve_lang_code(meta: Doc) -> str:
    """Return an HTML lang attribute value (BCP-47-ish) from meta.language.

    Accepts three shapes:
      - {"code": "es", "label": "Español"} — preferred, returns "es".
      - "en", "es-419" — already a BCP-47 short tag, returned as-is (lower-cased).
      - "English", "Spanish" — human-readable, mapped via `_LANGUAGE_NAME_TO_CODE`;
        unknown names fall back to the first whitespace-delimited token, truncated.
    """
    lang_meta = meta.get("language", "en")
    if isinstance(lang_meta, dict):
        return str(lang_meta.get("code") or "en")
    if not lang_meta:
        return "en"
    raw = str(lang_meta).strip()
    if re.fullmatch(r"[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*", raw):
        return raw.lower()[:10]
    # Whitespace-only strings produce empty split(); fall back to "en" to stay BCP-47-ish.
    tokens = raw.split() or ["en"]
    return _LANGUAGE_NAME_TO_CODE.get(raw.lower(), tokens[0][:10])


def _build_rb_footer_html(meta: Doc) -> str:
    """Render the inline "Powered by Research Buddy" footer div."""
    rb_version = meta.get("research_buddy_version", "")
    logo_data = _rb_logo_data_url()
    ver_suffix = f" v{rb_version}" if rb_version else ""
    return (
        f'<div class="rb-powered-by">'
        f'<img src="{logo_data}" alt="Research Buddy" class="rb-logo">'
        f"<span>Powered by "
        f'<a href="https://github.com/nuncaeslupus/research-buddy">Research Buddy</a>'
        f"{ver_suffix}"
        f"</span></div>\n"
    )


@functools.lru_cache(maxsize=1)
def _rb_logo_data_url() -> str:
    """Load and base64-encode the Research Buddy logo exactly once per process."""
    return _asset_to_base64(_load_binary_asset("research-buddy.png", "images"), "image/png")


def build_html(doc: Doc, *, theme_css: str | None = None) -> str:
    """Build the complete single-file HTML from a document dict.

    Args:
        doc: Parsed JSON document.
        theme_css: Optional extra CSS appended after the default stylesheet.
    """
    state = BuildState()
    meta = doc["meta"]
    tabs = doc["tabs"]

    doc_title = meta.get("title", "Documentation")
    short_title = meta.get("short_title", doc_title)
    ver = meta.get("version", "")
    date = meta.get("date", "")

    # tab bar
    tab_btns = []
    for i, tab in enumerate(tabs):
        active = " active" if i == 0 else ""
        tab_btns.append(
            f'<button class="tab-btn{active}" data-tab="{tab["id"]}">{tab["label"]}</button>'
        )
    tab_bar = (
        '<div id="tab-bar">\n'
        '<button id="menu-toggle" aria-label="Menu">☰</button>\n'
        + "\n".join(tab_btns)
        + '\n<button id="theme-toggle" aria-label="Toggle theme" title="Toggle theme">☾</button>'
        + "</div>\n"
    )

    # sidebar & content areas
    nav_html_parts = []
    tab_contents: list[str] = []

    for i, tab in enumerate(tabs):
        is_active = i == 0
        tab_num = str(i + 1)
        tid = tab["id"]
        label = tab["label"]
        active_cls = " active" if is_active else ""

        # Header ID for the tab itself
        tab_hdr_id = state.unique_id(f"tab-hdr-{tid}")

        tab_nav_list: list[dict[str, Any]] = []

        # Render sections recursively and collect nav entries
        tab_body_parts = [f'<h1 id="{tab_hdr_id}">{tab_num}. {label}</h1>\n']
        sections = tab.get("sections", {})
        for j, (title, sec) in enumerate(sections.items(), 1):
            num = f"{tab_num}.{j}"
            tab_body_parts.append(
                render_section(title, sec, state, tab_nav_list, level=2, number=num, meta=meta)
            )

        tab_body_parts.append(
            f'<p style="text-align:center;color:var(--text3);font-size:12px;padding:16px 0">'
            f"{doc_title} \u00b7 {label} \u00b7 v{ver}</p>\n"
        )

        # Assemble sidebar nav for this tab
        tab_nav_html = [f'<nav class="tab-nav{active_cls}" data-for="{tid}">\n']
        tab_nav_html.append(f'<a href="#{tab_hdr_id}">{tab_num}. {label}</a>\n')
        for entry in tab_nav_list:
            cls = ""
            if entry["level"] == 2:
                cls = ' class="sub"'
            elif entry["level"] >= 3:
                cls = ' class="subsub"'
            tab_nav_html.append(
                f'<a href="#{entry["id"]}"{cls}>{entry["num"]}. {entry["title"]}</a>\n'
            )
        tab_nav_html.append("</nav>\n")
        nav_html_parts.append("".join(tab_nav_html))

        # Assemble tab content area
        tab_contents.append(
            f'<div id="tab-{tid}" class="tab-content{active_cls}" data-tab-label="{label}">\n'
            f'<div class="content">\n{"".join(tab_body_parts)}</div></div>\n'
        )

    sidebar = (
        '<div id="sidebar">\n'
        f'<div class="sidebar-hdr">{short_title}'
        f"<span>v{ver} \u00b7 {date}</span></div>\n{''.join(nav_html_parts)}</div>\n"
    )

    lang_code = _resolve_lang_code(meta)
    rb_footer_html = _build_rb_footer_html(meta)

    body_content = (
        tab_bar
        + '<div id="layout">\n'
        + sidebar
        + '<div id="main">\n'
        + "".join(tab_contents)
        + rb_footer_html
        + "</div>\n</div>\n"
    )

    # load assets
    css = _load_asset("style.css", "css")
    js = _load_asset("script.js", "js")
    hljs_css = _load_asset("highlight-theme.min.css", "lib")
    hljs_js = _load_asset("highlight.min.js", "lib")

    # inject tab IDs into JS
    tab_ids = json.dumps([tab["id"] for tab in tabs])
    js = re.sub(
        r"/\*TABS_INJECT\*/.*?/\*END_INJECT\*/",
        lambda _: f"/*TABS_INJECT*/{tab_ids}/*END_INJECT*/",
        js,
    )

    # theme override + mandatory footer CSS
    theme_block = f"\n/* ── Theme overrides ── */\n{theme_css}" if theme_css else ""
    theme_block += _RB_FOOTER_CSS

    return f"""<!DOCTYPE html>
<html lang="{lang_code}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc_title} — v{ver}</title>
<!-- v{ver} -->
<script>
(function(){{
  try {{
    if (localStorage.getItem('rb-theme') === 'dark') {{
      document.documentElement.setAttribute('data-theme', 'dark');
    }}
  }} catch (e) {{}}
}})();
</script>
<style>
{hljs_css}
{css}{theme_block}
</style>
</head>
<body>
{body_content}
<script>{hljs_js}</script>
<script defer>
{js}
</script>
</body>
</html>"""
