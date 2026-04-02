"""Core HTML builder — converts a structured JSON document into a single-file HTML page."""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

# ── Type aliases ────────────────────────────────────────────────────────────

Block = dict[str, Any]
Doc = dict[str, Any]

# ── Constants ───────────────────────────────────────────────────────────────

VALID_TAG_CLASSES = frozenset({
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
})

MAX_NOWRAP_COLUMN_LENGTH = 30

# ── Assets ──────────────────────────────────────────────────────────────────


def _load_asset(name: str) -> str:
    """Load a bundled asset file from the package."""
    ref = resources.files("research_docs") / "assets" / name
    return ref.read_text(encoding="utf-8")


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


def md_block(text: str) -> str:
    """Convert a text block that may contain paragraph-separated sections."""
    if not text:
        return ""
    parts = text.split("\n\n")
    if len(parts) == 1:
        return md(text)
    return "".join(f"<p>{md(p.strip())}</p>" for p in parts if p.strip())


# ── Block renderers ─────────────────────────────────────────────────────────


def r_p(b: Block) -> str:
    style = f' style="{b["style"]}"' if b.get("style") else ""
    return f"<p{style}>{md(b.get('md', ''))}</p>\n"


def r_h3(b: Block) -> str:
    sid = f' id="{b["id"]}"' if b.get("id") else ""
    badge = f' <span class="tag tag-blue">{b["badge"]}</span>' if b.get("badge") else ""
    return f"<h3{sid}>{md(b.get('md', ''))}{badge}</h3>\n"


def r_h4(b: Block) -> str:
    sid = f' id="{b["id"]}"' if b.get("id") else ""
    return f"<h4{sid}>{md(b.get('md', ''))}</h4>\n"


def r_heading(b: Block) -> str:
    """Render a 'heading' block: {type, level, content}."""
    level = b.get("level", 3)
    tag = f"h{level}" if level in (3, 4) else "h3"
    text = b.get("content", "") or b.get("md", "")
    sid = f' id="{b["id"]}"' if b.get("id") else ""
    return f"<{tag}{sid}>{md(text)}</{tag}>\n"


def r_paragraph(b: Block) -> str:
    """Render a 'paragraph' block: {type, content}."""
    text = b.get("content", "") or b.get("md", "")
    style = f' style="{b["style"]}"' if b.get("style") else ""
    return f"<p{style}>{md(text)}</p>\n"


def r_hr(_b: Block) -> str:
    return "<hr>\n"


def r_ul(b: Block) -> str:
    items = "".join(f"<li>{md(i)}</li>\n" for i in b.get("items", []))
    return f"<ul>\n{items}</ul>\n"


def r_ol(b: Block) -> str:
    items = "".join(f"<li>{md(i)}</li>\n" for i in b.get("items", []))
    return f"<ol>\n{items}</ol>\n"


def r_code(b: Block) -> str:
    lang = b.get("lang", "")
    code = b.get("text", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lang_attr = f' data-lang="{lang}"' if lang else ""
    lang_cls = f' class="language-{lang}"' if lang else ""
    return (
        f'<div class="code-wrap"{lang_attr}>'
        f'<button class="copy-btn" title="Copy">⎘</button>'
        f"<pre><code{lang_cls}>{code}</code></pre>"
        f"</div>\n"
    )


def r_callout(b: Block) -> str:
    variant = b.get("variant", "blue")
    title = b.get("title", "")
    cls = f"callout {variant}" if variant != "blue" else "callout"
    title_html = f'<div class="callout-title">{title}</div>\n' if title else ""
    return f'<div class="{cls}">\n{title_html}<p>{md(b.get("md", ""))}</p>\n</div>\n'


def r_verdict(b: Block) -> str:
    badge = b.get("badge", "reject")
    badge_text = b.get("badge_text", badge.upper())
    label = b.get("label", "")
    text = md(b.get("md", ""))
    return (
        f'<div class="verdict">'
        f'<span class="verdict-label">{md(label)}</span>'
        f'<span class="verdict-badge {badge}">{badge_text}</span>'
        f'<span class="verdict-text">{text}</span>'
        f"</div>\n"
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


def r_table(b: Block) -> str:
    headers = b.get("headers", [])
    rows = b.get("rows", [])
    nowrap = _nowrap_cols(headers, rows)
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
    return f'<div class="table-wrap"><table>\n{thead}{tbody}</table></div>\n'


def r_svg(b: Block) -> str:
    return f'<div class="diagram-wrap">{b.get("html", "")}</div>\n'


def r_usage_banner(b: Block) -> str:
    title = b.get("title", "")
    items = b.get("items", [])
    items_html = "".join(f"<li>{md(i)}</li>\n" for i in items)
    return f'<div class="usage-banner"><h4>{title}</h4><ul>{items_html}</ul></div>\n'


def r_agnostic_banner(b: Block) -> str:
    return (
        f'<div class="agnostic">'
        f'<div class="ico">🌐</div>'
        f"<div><h4>{b.get('title', '')}</h4>"
        f"<p>{md(b.get('md', ''))}</p>"
        f"</div></div>\n"
    )


def r_cc_banner(b: Block) -> str:
    return (
        f'<div class="cc-banner">'
        f"<div><h4>{b.get('title', '')}</h4>"
        f"<p>{md(b.get('md', ''))}</p>"
        f"</div></div>\n"
    )


def r_phase_cards(b: Block) -> str:
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


def r_card_grid(b: Block) -> str:
    cols = b.get("cols", 2)
    extra = " three" if cols == 3 else ""
    cards_html = ""
    for card in b.get("cards", []):
        cards_html += (
            f'<div class="card">'
            f'<div class="card-title">{md(card.get("title", ""))}</div>'
            f"<p>{md(card.get('md', ''))}</p>"
            f"</div>\n"
        )
    return f'<div class="card-grid{extra}">\n{cards_html}</div>\n'


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
}


def render_blocks(blocks: list[Block]) -> str:
    out: list[str] = []
    for b in blocks:
        renderer = BLOCK_RENDERERS.get(b.get("type", ""))
        if renderer:
            out.append(renderer(b))
        else:
            out.append(f"<!-- unknown block type: {b.get('type')} -->\n")
    return "".join(out)


# ── Section rendering ───────────────────────────────────────────────────────


def render_section(sec: Doc, tab_id: str, meta: Doc | None = None, section_id: str = "") -> str:
    sid = sec.get("id", section_id)
    title = sec.get("title", "")
    section_label = sec.get("section_label", "")
    badge = sec.get("badge", "")

    title_page_id = (meta or {}).get("title_page_section", "ov-intro")
    is_title_page = sid == title_page_id

    label_html = f'<div class="section-label">{section_label}</div>\n' if section_label else ""
    badge_html = f' <span class="tag tag-blue">{badge}</span>' if badge else ""

    if is_title_page:
        doc_title = (meta or {}).get("title", "Documentation")
        subtitle = (meta or {}).get("subtitle", "")
        ver = (meta or {}).get("version", "")
        date = (meta or {}).get("date", "")
        ver_line = f"<p>v{ver} — {date}</p>\n" if ver else ""
        sub_line = f'<p class="subtitle">{subtitle}</p>\n' if subtitle else ""
        heading = f"<h1>{doc_title}</h1>\n{sub_line}{ver_line}"
        open_tag = f'<div id="{sid}" class="title-page">\n{label_html}{heading}'
        close_tag = "</div>\n"
    elif sid.startswith("ov-"):
        h2 = f"<h2>{md(title)}{badge_html}</h2>\n" if title else ""
        open_tag = f'<div id="{sid}">\n{label_html}{h2}'
        close_tag = "</div>\n"
    else:
        h2 = f"<h2>{md(title)}{badge_html}</h2>\n" if title else ""
        open_tag = f'<section id="{sid}">\n{label_html}{h2}'
        close_tag = "</section>\n"

    body = render_blocks(sec.get("blocks", []))
    return f"{open_tag}{body}{close_tag}<hr>\n"


# ── Sidebar nav ─────────────────────────────────────────────────────────────


def render_nav(nav_groups: list[Doc], tab_id: str, *, is_active: bool = False) -> str:
    active_cls = " active" if is_active else ""
    lines = [f'<nav class="tab-nav{active_cls}" data-for="{tab_id}">\n']
    for group in nav_groups:
        label = group.get("label", "")
        if label:
            lines.append(f'<div class="nav-s">{label}</div>\n')
        for item in group.get("items", []):
            href = item.get("href", "")
            lbl = item.get("label", "")
            sub = " sub" if item.get("sub") else ""
            subsub = " subsub" if item.get("subsub") else ""
            lines.append(f'<a href="#{href}" class="{(sub + subsub).strip()}">{lbl}</a>\n')
    lines.append("</nav>\n")
    return "".join(lines)


# ── Changelog ───────────────────────────────────────────────────────────────


def _version_sort_key(entry: Doc) -> tuple[int, int]:
    ver = entry.get("version", "") or entry.get("id", "")
    m = re.search(r"(\d+)\.(\d+)", ver)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _ensure_entry_id(entry: Doc) -> str:
    eid = entry.get("id") or ""
    if eid:
        return eid
    ver = entry.get("version", "")
    m = re.search(r"(\d+)\.(\d+)", ver)
    if m:
        return f"cl-v{m.group(1)}{m.group(2)}"
    return ""


def build_changelog_nav(changelog: Doc) -> list[Doc]:
    """Auto-generate changelog sidebar nav from entries."""
    entries = sorted(changelog.get("entries", []), key=_version_sort_key, reverse=True)
    items: list[Doc] = []
    for entry in entries:
        eid = _ensure_entry_id(entry)
        ver = entry.get("version", "")
        label = ver.split("—")[0].split("\u2014")[0].strip()
        if label and not label.startswith("v"):
            label = f"v{label}"
        if entry.get("current"):
            label += " \u2014 Current"
        items.append({"href": eid, "label": label})
    groups: list[Doc] = []
    if changelog.get("protocol_blocks"):
        groups.append(
            {"label": "Protocol", "items": [{"href": "cl-protocol", "label": "Update Protocol"}]}
        )
    groups.append({"label": "Version History", "items": items})
    return groups


def render_changelog(changelog: Doc, meta: Doc) -> str:
    entries = sorted(changelog.get("entries", []), key=_version_sort_key, reverse=True)
    entries_html = ""
    for entry in entries:
        current_cls = " current" if entry.get("current") else ""
        eid = _ensure_entry_id(entry)
        id_attr = f' id="{eid}"' if eid else ""
        ver = entry.get("version", "")
        if ver and not ver.startswith("v"):
            ver = f"v{ver}"

        paras = ""
        if entry.get("paragraphs"):
            paras = "".join(f"<p>{md(p)}</p>\n" for p in entry["paragraphs"])
        else:
            title = entry.get("title", "")
            items = entry.get("items", [])
            if title:
                paras += f"<p><strong>{md(title)}</strong></p>\n"
            if items:
                paras += "<ul>\n"
                paras += "".join(f"<li>{md(i)}</li>\n" for i in items)
                paras += "</ul>\n"

        entries_html += (
            f'<div class="cl-entry{current_cls}"{id_attr}>\n'
            f'<div class="cl-version">{ver}</div>\n'
            f"{paras}</div>\n"
        )

    proto_html = render_blocks(changelog.get("protocol_blocks", []))
    doc_title = meta.get("short_title", meta.get("title", "Documentation"))
    v = meta.get("version", "")
    return (
        f'<div id="cl-protocol"><h2>Update Protocol</h2>\n{proto_html}</div>\n<hr>\n'
        f"{entries_html}"
        f'<p style="text-align:center;color:#6070a0;font-size:12px;padding:16px 0">'
        f"{doc_title} \u00b7 Changelog \u00b7 v{v}</p>\n"
    )


# ── Link validation ─────────────────────────────────────────────────────────


def _collect_block_ids(blocks: list[Block]) -> list[str]:
    ids: list[str] = []
    for b in blocks:
        bid = b.get("id")
        if bid:
            ids.append(bid)
    return ids


def validate_links(doc: Doc) -> list[str]:
    """Cross-reference nav hrefs against content IDs. Returns warnings."""
    tabs = doc["tabs"]
    sections = doc["sections"]
    changelog = doc.get("changelog", {})

    all_ids: list[str] = []

    # section-level IDs
    for sid, sec in sections.items():
        all_ids.append(sid)
        all_ids.extend(_collect_block_ids(sec.get("blocks", [])))

    # changelog IDs
    if changelog:
        all_ids.append("cl-protocol")
        for entry in changelog.get("entries", []):
            eid = _ensure_entry_id(entry)
            if eid:
                all_ids.append(eid)

    for tab in tabs:
        all_ids.append(f"tab-{tab['id']}")

    # duplicate IDs
    warnings: list[str] = []
    seen: dict[str, int] = {}
    for aid in all_ids:
        seen[aid] = seen.get(aid, 0) + 1
    for aid, count in seen.items():
        if count > 1:
            warnings.append(f"DUPLICATE ID: '{aid}' appears {count} times")

    id_set = set(all_ids)

    # nav hrefs -> content IDs
    for tab in tabs:
        tab_id = tab["id"]
        tab_label = tab["label"]
        if tab_id == "changelog":
            nav_groups = build_changelog_nav(changelog)
        else:
            nav_groups = tab.get("nav", [])

        for group in nav_groups:
            for item in group.get("items", []):
                href = item.get("href", "")
                label = item.get("label", "")
                if href and href not in id_set:
                    warnings.append(
                        f"BROKEN LINK: [{tab_label}] '{label}' -> #{href} (no matching id)"
                    )

    # sections referenced in tabs but not defined
    for tab in tabs:
        if tab["id"] == "changelog":
            continue
        for sid in tab.get("sections", []):
            if sid not in sections:
                warnings.append(f"MISSING SECTION: tab '{tab['label']}' references '{sid}'")

    # sections defined but not referenced by any tab
    referenced: set[str] = set()
    for tab in tabs:
        referenced.update(tab.get("sections", []))
    for sid in sections:
        if sid not in referenced:
            warnings.append(f"ORPHAN SECTION: '{sid}' defined but not in any tab")

    return warnings


# ── HTML assembly ───────────────────────────────────────────────────────────


def find_latest_json(source_dir: Path) -> Path | None:
    """Find the highest-versioned document_v*.json in a directory."""
    candidates = list(source_dir.glob("document_v*.json"))
    if not candidates:
        return None

    def ver_key(p: Path) -> tuple[int, int]:
        m = re.search(r"v(\d+)[_.](\d+)", p.name)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    return sorted(candidates, key=ver_key)[-1]


def build_html(doc: Doc, *, theme_css: str | None = None) -> str:
    """Build the complete single-file HTML from a document dict.

    Args:
        doc: Parsed JSON document.
        theme_css: Optional extra CSS appended after the default stylesheet.
    """
    meta = doc["meta"]
    tabs = doc["tabs"]
    sections = doc["sections"]
    changelog = doc.get("changelog", {})

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
        + '\n<div id="search-wrap">'
        '<input id="search-input" type="search" placeholder="Search\u2026 (Ctrl+F)" '
        'autocomplete="off">'
        '<span id="search-count"></span>'
        "</div>\n</div>\n"
    )

    # sidebar
    nav_html = ""
    for i, tab in enumerate(tabs):
        is_active = i == 0
        if tab["id"] == "changelog":
            nav_groups = build_changelog_nav(changelog)
        else:
            nav_groups = tab.get("nav", [])
        nav_html += render_nav(nav_groups, tab["id"], is_active=is_active)

    sidebar = (
        '<div id="sidebar">\n'
        f'<div class="sidebar-hdr">{short_title}'
        f"<span>v{ver} \u00b7 {date}</span></div>\n{nav_html}</div>\n"
    )

    # tab content areas
    tab_contents: list[str] = []
    for i, tab in enumerate(tabs):
        active = " active" if i == 0 else ""
        tid = tab["id"]
        label = tab["label"]

        if tid == "changelog":
            inner = render_changelog(changelog, meta)
        else:
            parts: list[str] = []
            for sid in tab.get("sections", []):
                sec = sections.get(sid)
                if sec:
                    parts.append(render_section(sec, tid, meta, section_id=sid))
                else:
                    parts.append(f"<!-- missing section: {sid} -->\n")
            parts.append(
                f'<p style="text-align:center;color:#6070a0;font-size:12px;padding:16px 0">'
                f"{doc_title} \u00b7 {label} \u00b7 v{ver}</p>\n"
            )
            inner = "".join(parts)

        tab_contents.append(
            f'<div id="tab-{tid}" class="tab-content{active}" data-tab-label="{label}">\n'
            f'<div class="content">\n{inner}</div></div>\n'
        )

    body_content = (
        tab_bar
        + '<div id="layout">\n'
        + sidebar
        + '<div id="main">\n'
        + "".join(tab_contents)
        + "</div>\n</div>\n"
        '<div id="breadcrumb"></div>\n'
        '<button id="back-top" title="Back to top">\u2191</button>\n'
    )

    # load assets
    css = _load_asset("style.css")
    js = _load_asset("script.js")
    hljs_css = _load_asset("highlight-theme.min.css")
    hljs_js = _load_asset("highlight.min.js")

    # inject tab IDs into JS
    tab_ids = json.dumps([tab["id"] for tab in tabs])
    js = re.sub(
        r"/\*TABS_INJECT\*/.*?/\*END_INJECT\*/",
        f"/*TABS_INJECT*/{tab_ids}/*END_INJECT*/",
        js,
    )

    # theme override
    theme_block = f"\n/* ── Theme overrides ── */\n{theme_css}" if theme_css else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{doc_title} — v{ver}</title>
<!-- v{ver} -->
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
