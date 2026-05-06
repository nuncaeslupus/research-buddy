"""Migrate a research-buddy v1 JSON document to a v2 Markdown source file.

Transformations:
- meta.* + agent_guidelines.project_specific.* → YAML frontmatter
- agent_guidelines.framework + session_protocol → DROPPED (replaced by v2 framework
  block, copied from the installed starter.md)
- tabs[overview] → DROPPED (Quick Links / How to Navigate are obsolete in MD)
- tabs[research] sections → top-level H2 sections (Open Research Queue, Research
  Tracker, Reasoning Journey, References, Discarded Alternatives, and per-Q
  Session Notes coalesced into a single ## Session Notes H2)
- tabs[skill-spec], tabs[system-design], tabs[meta-validation], or any other
  domain-specific tab → H2 sections placed AFTER Project Specification, with each
  original section becoming an H3 subsection. Verdict blocks (badge=adopt|rule)
  become <!-- @rule: ... --> blocks; verdict blocks (badge=reject) inside research
  Discarded Alternatives become <!-- @da: ... --> blocks.
- tabs[changelog] → DROPPED (data is in doc.changelog.entries)
- doc.changelog.entries → ## Changelog with H3 entries newest-first

Refuses to run if the target output already exists (use --force to overwrite).

Usage:
    python -m research_buddy.migrate_v1_to_v2 INPUT.json [-o OUTPUT.md] [--force]

Exit codes:
    0 — migration written
    2 — input missing, malformed, or output exists without --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

Doc = dict[str, Any]
Block = dict[str, Any]


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def build_frontmatter(doc: Doc) -> str:
    meta = doc.get("meta", {}) or {}
    ps = (doc.get("agent_guidelines") or {}).get("project_specific") or {}
    file_name = (meta.get("file_name") or "").rstrip()
    # Strip .json extension first, THEN strip any version suffix like "_v1_14"
    file_name = re.sub(r"\.json$", "", file_name)
    file_name = re.sub(r"_v\d+(?:[._]\d+)*$", "", file_name)

    version = meta.get("version")
    version_str: str | None
    if isinstance(version, (int, float)):
        version_str = f"{version:.2f}".rstrip("0").rstrip(".")
        if "." not in version_str:
            version_str = f"{version_str}.0"
    else:
        version_str = str(version) if version else None

    fm: Doc = {
        "format_version": 2,
        "research_buddy_version": "2.0.0",
        "version": version_str,
        "date": meta.get("date"),
        "file_name": file_name or None,
        "title": meta.get("title"),
        "subtitle": meta.get("subtitle"),
        "language": {
            "code": (meta.get("language") or {}).get("code", "en"),
            "label": (meta.get("language") or {}).get("label", "English"),
        },
        "project": {
            "domain": ps.get("domain"),
            "deliverable_type": ps.get("deliverable_type"),
            "final_goal": ps.get("final_goal"),
            "timing": ps.get("timing"),
            "validation_gate": ps.get("validation_gate"),
        },
        "ui_strings": {
            "status_open": (meta.get("ui_strings") or {}).get("status_open", "OPEN"),
            "status_done": (meta.get("ui_strings") or {}).get("status_done", "✦ Researched"),
            "status_wip": (meta.get("ui_strings") or {}).get("status_wip", "IN PROGRESS"),
        },
    }
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---"


# ---------------------------------------------------------------------------
# Block → Markdown rendering
# ---------------------------------------------------------------------------


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    def cell(s: Any) -> str:
        text = str(s) if s is not None else ""
        text = text.replace("\n", " ").replace("|", "\\|")
        return text.strip()

    out = ["| " + " | ".join(cell(h) for h in headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        out.append("| " + " | ".join(cell(c) for c in padded[: len(headers)]) + " |")
    return "\n".join(out)


def _heading_prefix(level: int) -> str:
    level = max(1, min(6, level))
    return "#" * level


def _render_callout(blk: Block) -> str:
    title = blk.get("title", "")
    md = blk.get("md", "").strip()
    variant = blk.get("variant", "")
    parts: list[str] = []
    head = f"**{title}**" if title else ""
    if variant:
        head = f"{head} _({variant})_" if head else f"_{variant}_"
    if head:
        parts.append(head)
    if md:
        parts.append(md)
    body = "\n\n".join(parts)
    return "\n".join(f"> {line}" if line else ">" for line in body.splitlines())


def _render_card_grid(blk: Block) -> str:
    out: list[str] = []
    for card in blk.get("cards", []):
        title = card.get("title", "")
        md = card.get("md", "").strip()
        out.append(f"**{title}**\n\n{md}" if title else md)
    return "\n\n".join(out)


def _render_usage_banner(blk: Block) -> str:
    title = blk.get("title", "")
    items = blk.get("items", [])
    out: list[str] = []
    if title:
        out.append(f"**{title}**")
    for it in items:
        out.append(f"- {it}")
    return "\n".join(out)


def parse_rule_label(label: str) -> dict[str, Any]:
    """Split 'R-FM-1 [skill][portable] VALIDATED — PRE-REGISTERED 64' into parts."""
    s = label.strip()
    m = re.match(r"^(R-[A-Z0-9-]+|DA-[A-Z0-9-]+)\s*(.*)$", s, re.IGNORECASE)
    if not m:
        return {"id": s, "tags": [], "status": "", "extras": ""}
    rule_id = m.group(1)
    rest = m.group(2)

    tags: list[str] = []
    while True:
        m2 = re.match(r"^\s*\[([^\]]+)\]\s*", rest)
        if not m2:
            break
        tags.append(m2.group(1))
        rest = rest[m2.end() :]

    status_match = re.match(r"^\s*([A-Z][A-Z0-9_]*)", rest)
    status = status_match.group(1) if status_match else ""
    extras = rest[status_match.end() :].lstrip() if status_match else rest.strip()
    extras = re.sub(r"^[—-]\s*", "", extras).strip()

    return {"id": rule_id, "tags": tags, "status": status, "extras": extras}


def _render_verdict_as_rule(blk: Block) -> str:
    label = blk.get("label", "")
    parsed = parse_rule_label(label)
    rid = parsed["id"]
    aid = rid.lower()
    tags_md = " ".join(f"[{t}]" for t in parsed["tags"])
    status = parsed["status"]
    extras = parsed["extras"]
    md = (blk.get("md") or "").strip()

    head = f"**{rid}**"
    if tags_md:
        head += f" {tags_md}"
    if status:
        head += f" {status}"
    if extras:
        head += f" — {extras}"
    head += "."

    parts = [
        f"<!-- @rule: {rid} -->",
        f'<a id="{aid}"></a>',
        "",
        head,
    ]
    if md:
        parts.append("")
        parts.append(md)
    return "\n".join(parts)


def _render_verdict_as_da(blk: Block) -> str:
    label = blk.get("label", "")
    parsed = parse_rule_label(label)
    rid = parsed["id"] or label.strip()
    aid = rid.lower()
    md = (blk.get("md") or "").strip()
    parts = [
        f"<!-- @da: {rid} -->",
        f'<a id="{aid}"></a>',
        "",
        f"**{rid}.** {md}" if md else f"**{rid}.**",
    ]
    return "\n".join(parts)


def render_block(blk: Block, heading_offset: int = 0) -> str:
    t = blk.get("type")
    if t == "p":
        return (blk.get("md") or "").strip()
    if t in {"h3", "h4", "h5"}:
        level = {"h3": 3, "h4": 4, "h5": 5}[t] + heading_offset
        text = (blk.get("md") or "").strip()
        text = re.sub(r"^#+\s*", "", text)
        return f"{_heading_prefix(level)} {text}"
    if t == "ul":
        items = blk.get("items", [])
        return "\n".join(f"- {item}" for item in items)
    if t == "ol":
        items = blk.get("items", [])
        return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
    if t == "code":
        lang = blk.get("lang", "")
        text = blk.get("text", "")
        return f"```{lang}\n{text}\n```"
    if t == "hr":
        return "---"
    if t == "callout":
        return _render_callout(blk)
    if t == "table":
        return _md_table(blk.get("headers", []), blk.get("rows", []))
    if t == "card_grid":
        return _render_card_grid(blk)
    if t == "usage_banner":
        return _render_usage_banner(blk)
    if t == "references":
        items = blk.get("items", [])
        return "\n".join(f"- {it.get('text', '')}" for it in items)
    if t == "verdict":
        badge = blk.get("badge", "")
        if badge in {"adopt", "rule"}:
            return _render_verdict_as_rule(blk)
        if badge == "reject":
            return _render_verdict_as_da(blk)
        label = blk.get("label", "")
        md = (blk.get("md") or "").strip()
        return (
            f"**{label}** _(badge: {badge})_\n\n{md}" if md else f"**{label}** _(badge: {badge})_"
        )
    if t == "svg":
        return "<!-- SVG omitted in migration -->"
    if t in {"phase_cards", "agnostic_banner", "cc_banner"}:
        title = blk.get("title", "")
        md = blk.get("md", "")
        out: list[str] = []
        if title:
            out.append(f"**{title}**")
        if md:
            out.append(md)
        return "\n\n".join(out)
    return f"<!-- unknown block type: {t} -->"


def render_blocks(blocks: list[Block], heading_offset: int = 0) -> str:
    rendered = [render_block(b, heading_offset) for b in blocks if b]
    rendered = [r for r in rendered if r]
    return "\n\n".join(rendered)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def build_title(meta: Doc) -> str:
    title = meta.get("title") or "Untitled"
    version = meta.get("version") or "?"
    date = meta.get("date") or ""
    subtitle = meta.get("subtitle") or ""

    parts: list[str] = [
        "<!-- @anchor: title -->",
        f"# {title} — Research Document",
        "",
    ]
    if subtitle:
        parts.append(f"*{subtitle}*")
        parts.append("")
    parts.extend(
        [
            f"**Format:** Research Buddy v2 (Markdown) · "
            f"**Version:** {version} · **Updated:** {date}",
            "",
            "This file is the source-of-truth artifact for the project. The agent edits this file; "
            "the clean view (without the framework) and the HTML rendering are derived on demand.",
            "",
            "**Filename convention:**",
            "",
            "- `{file_name}_v{version}-source.md` — this file. Agent-edited. "
            "Full framework included. Upload this each session.",
            "- `{file_name}_v{version}.md` — clean view. Generated on demand. "
            "Research content only, no framework.",
            "- `{file_name}_v{version}.html` — HTML rendering. Generated on demand.",
            "",
            "> **Agent: read [Framework (Core)](#framework-core) before any other action. "
            "Read [Framework (Reference)](#framework-reference) once per session. Both are short. "
            "Both are required reading.**",
            "",
            "<!-- @end: title -->",
        ]
    )
    return "\n".join(parts)


def load_framework_block_from_starter() -> str:
    try:
        ref = resources.files("research_buddy") / "starter.md"
        text = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        here = Path(__file__).parent
        text = (here / "starter.md").read_text(encoding="utf-8")

    lines = text.splitlines()
    start = end = -1
    for i, line in enumerate(lines):
        if line.strip() == "<!-- @anchor: framework.core -->" and start < 0:
            start = i
        elif line.strip() == "<!-- @end: framework.reference -->":
            end = i
    if start < 0 or end < 0:
        raise RuntimeError("starter.md is missing framework anchors; cannot migrate")
    return "\n".join(lines[start : end + 1])


def build_project_specification(ps: Doc) -> str:
    domain_rules = (ps.get("domain_constraints") or {}).get("rules") or []
    if isinstance(domain_rules, list) and domain_rules:
        rules_block = "\n".join(f"- {r}" for r in domain_rules)
    else:
        rules_block = "*(none specified)*"

    tier_lines: list[str] = []
    st = ps.get("source_tiers") or {}
    for label, key in [
        ("Tier 1", "tier_1"),
        ("Tier 2", "tier_2"),
        ("Discovery", "discovery"),
        ("Never", "never"),
    ]:
        val = st.get(key)
        if isinstance(val, list):
            val = "; ".join(str(v) for v in val)
        tier_lines.append(f"- **{label}:** {val or '*(unspecified)*'}")

    parts = [
        "<!-- @anchor: project -->",
        "## Project Specification",
        "",
        "<!-- Migrated from v1 agent_guidelines.project_specific. Modifications go here. "
        "Do not modify the Framework sections. -->",
        "",
        "### Domain",
        "",
        f"- **Domain:** {ps.get('domain') or '*(unspecified)*'}",
        f"- **Deliverable type:** {ps.get('deliverable_type') or '*(unspecified)*'}",
        f"- **Final goal:** {ps.get('final_goal') or '*(unspecified)*'}",
        f"- **Timing:** {ps.get('timing') or '*(unspecified)*'}",
        f"- **Validation gate:** {ps.get('validation_gate') or '*(unspecified)*'}",
        "",
        "<!-- @anchor: project.tiers -->",
        "### Source tiers",
        "",
        *tier_lines,
        "",
        "<!-- @end: project.tiers -->",
        "",
        "<!-- @anchor: project.rules -->",
        "### Domain rules",
        "",
        rules_block,
        "",
        "<!-- @end: project.rules -->",
        "",
        "<!-- @end: project -->",
    ]
    return "\n".join(parts)


def build_domain_tab(tab: Doc) -> str:
    label = tab.get("label") or tab.get("id") or "Untitled"
    anchor_id = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")

    parts = [
        f"<!-- @anchor: {anchor_id} -->",
        f"## {label}",
        "",
    ]

    for sec_name, sec in tab.get("sections", {}).items():
        if sec_name.startswith("_"):
            continue
        parts.append(f"### {sec_name}")
        parts.append("")
        body = render_blocks(sec.get("blocks", []), heading_offset=1)
        if body:
            parts.append(body)
            parts.append("")

    parts.append(f"<!-- @end: {anchor_id} -->")
    return "\n".join(parts)


def _strip_done_rows_from_queue(table_block: Block, ui: Doc) -> tuple[list[str], list[list[str]]]:
    headers = list(table_block.get("headers", []))
    rows = list(table_block.get("rows", []))
    status_done_token = ui.get("status_done", "✦ Researched")

    drop_idx: set[int] = set()
    for i, h in enumerate(headers):
        if h.strip().lower() in {"priority", "status"}:
            drop_idx.add(i)
    status_col = next(
        (i for i, h in enumerate(headers) if h.strip().lower() == "status"),
        -1,
    )
    keep_rows: list[list[str]] = []
    for row in rows:
        if status_col >= 0 and status_col < len(row):
            cell = str(row[status_col]).strip()
            if status_done_token.split()[0] in cell or cell.startswith("\u2726"):
                continue
        keep_rows.append(row)

    new_headers = [h for i, h in enumerate(headers) if i not in drop_idx]
    new_rows: list[list[str]] = []
    for row in keep_rows:
        new_rows.append([c for i, c in enumerate(row) if i not in drop_idx])

    has_id_col = bool(new_rows) and bool(re.match(r"^Q-\d+", str(new_rows[0][0])))
    if not has_id_col and new_rows:
        for i, row in enumerate(new_rows):
            topic = row[0] if row else ""
            m = re.match(r"^(Q-\d+)\b", topic)
            if m:
                qid = m.group(1)
                row[0] = topic[m.end() :].lstrip(" -—:")
            else:
                qid = f"Q-{i + 1:03d}"
            row.insert(0, qid)
        new_headers.insert(0, "ID")

    return new_headers, new_rows


def build_open_research_queue(research_tab: Doc, ui: Doc) -> str:
    section = (research_tab.get("sections") or {}).get("Open Research Queue") or {}
    table_block = next(
        (b for b in section.get("blocks", []) if b.get("type") == "table"),
        None,
    )
    if table_block is None:
        body = "*(no queue table found in source)*"
    else:
        headers, rows = _strip_done_rows_from_queue(table_block, ui)
        if rows:
            body = _md_table(headers, rows)
        else:
            body = "*(all topics complete — see Research Tracker)*"

    return "\n".join(
        [
            "<!-- @anchor: queue -->",
            "## Open Research Queue",
            "",
            "Pending topics in priority order. **Top row = next session's topic.** Done items "
            "leave the queue and move to the [Research Tracker](#research-tracker). New items "
            "pass through the insertion protocol.",
            "",
            body,
            "",
            "<!-- @end: queue -->",
        ]
    )


def build_research_tracker(research_tab: Doc) -> str:
    section = (research_tab.get("sections") or {}).get("Research Tracker") or {}
    table_block = next(
        (b for b in section.get("blocks", []) if b.get("type") == "table"),
        None,
    )
    if table_block is None:
        body = "*(no tracker table found in source)*"
    else:
        body = _md_table(table_block.get("headers", []), table_block.get("rows", []))

    return "\n".join(
        [
            "<!-- @anchor: tracker -->",
            "## Research Tracker",
            "",
            "Living status board — one row per researched topic. Rows are appended as topics "
            "complete; never deleted.",
            "",
            body,
            "",
            "<!-- @end: tracker -->",
        ]
    )


def build_adopted_rules_index(domain_tab_labels: list[str]) -> str:
    if domain_tab_labels:
        links = ", ".join(
            f"[{lbl}](#{re.sub(r'[^a-z0-9]+', '-', lbl.lower()).strip('-')})"
            for lbl in domain_tab_labels
        )
        intro = (
            f"Rules in this project are organized topically across {links}. "
            f"Each rule has a stable `R-XXX-N` ID and an inline `<a id>` link target; "
            f"reference them via standard cross-links such as `[R-FM-1](#r-fm-1)`."
        )
    else:
        intro = (
            "Rules adopted during research, with stable IDs of the form `R-{TOPIC}-{N}`. "
            "Each rule has an inline `<a id>` link target. None recorded yet."
        )
    return "\n".join(
        [
            "<!-- @anchor: rules -->",
            "## Adopted Rules",
            "",
            intro,
            "",
            "<!-- @end: rules -->",
        ]
    )


def build_discarded_alternatives(research_tab: Doc) -> str:
    section = (research_tab.get("sections") or {}).get("Discarded Alternatives") or {}
    parts = [
        "<!-- @anchor: discarded -->",
        "## Discarded Alternatives",
        "",
        "Permanent record of rejected approaches. Never re-propose items listed here. "
        "Each entry has a stable `DA-{TOPIC}-{N}` label and an inline `<a id>` link target.",
        "",
    ]
    body_blocks: list[str] = []
    for blk in section.get("blocks", []):
        t = blk.get("type")
        if t == "verdict" and blk.get("badge") == "reject":
            body_blocks.append(_render_verdict_as_da(blk))
        elif t == "p":
            md = (blk.get("md") or "").strip()
            if md:
                body_blocks.append(md)
    parts.append("\n\n".join(body_blocks) if body_blocks else "*(none recorded)*")
    parts.append("")
    parts.append("<!-- @end: discarded -->")
    return "\n".join(parts)


def build_session_notes(research_tab: Doc) -> str:
    parts = [
        "<!-- @anchor: sessions -->",
        "## Session Notes",
        "",
        "One subsection per researched topic. Each contains pre-registration, sources "
        "consulted, decisions adopted, rejected claims, and second-opinion evaluation.",
        "",
    ]

    sessions: list[tuple[str, Doc]] = []
    for sec_name, sec in (research_tab.get("sections") or {}).items():
        m = re.match(r"^Session Notes\s*[—-]\s*(Q-\d+)", sec_name)
        if m:
            sessions.append((m.group(1), sec))

    def _qnum(t: tuple[str, Doc]) -> int:
        m = re.match(r"Q-(\d+)", t[0])
        return int(m.group(1)) if m else 0

    sessions.sort(key=_qnum)

    for qid, sec in sessions:
        aid = qid.lower()
        blocks = list(sec.get("blocks", []))
        title = qid
        for i, blk in enumerate(blocks):
            if blk.get("type") == "h3":
                t = (blk.get("md") or "").strip()
                t = re.sub(r"^#+\s*", "", t)
                title = t or qid
                blocks.pop(i)
                break

        parts.append(f"<!-- @session: {qid} -->")
        parts.append(f'<a id="{aid}"></a>')
        parts.append("")
        parts.append(f"### {title}")
        parts.append("")
        body = render_blocks(blocks, heading_offset=0)
        if body:
            parts.append(body)
        parts.append("")

    parts.append("<!-- @end: sessions -->")
    return "\n".join(parts)


def build_reasoning_journey(research_tab: Doc) -> str:
    section = (research_tab.get("sections") or {}).get("Reasoning Journey") or {}
    body = render_blocks(section.get("blocks", []), heading_offset=0)
    return "\n".join(
        [
            "<!-- @anchor: journey -->",
            "## Reasoning Journey",
            "",
            "Chronological narrative of how the project arrived at its current state.",
            "",
            body or "*(none recorded)*",
            "",
            "<!-- @end: journey -->",
        ]
    )


def build_references(research_tab: Doc) -> str:
    section = (research_tab.get("sections") or {}).get("References") or {}
    body = render_blocks(section.get("blocks", []), heading_offset=0)
    return "\n".join(
        [
            "<!-- @anchor: references -->",
            "## References",
            "",
            "All sources cited across research, descending version order.",
            "",
            body or "*(none recorded)*",
            "",
            "<!-- @end: references -->",
        ]
    )


def build_changelog(doc: Doc) -> str:
    entries = list((doc.get("changelog") or {}).get("entries", []))

    def _key(e: Doc) -> tuple[int, int]:
        ver = str(e.get("version", ""))
        m = re.search(r"(\d+)\.(\d+)", ver)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    entries.sort(key=_key, reverse=True)

    # If the top changelog entry's version doesn't match meta.version, prepend a
    # synthetic entry so the document is internally consistent. This fixes a
    # pre-existing pattern in v1 projects where the changelog lagged behind
    # meta.version by one release.
    meta = doc.get("meta", {}) or {}
    meta_version = str(meta.get("version") or "").lstrip("v")
    if meta_version:
        top_ver = str(entries[0].get("version", "")).lstrip("v") if entries else ""
        if meta_version != top_ver:
            synth = {
                "version": meta_version,
                "blocks": [
                    {
                        "type": "p",
                        "md": (
                            "Format migration from research-buddy v1 (JSON) to v2 (Markdown). "
                            "Content preserved verbatim; rules retain their topical organization "
                            "across the domain-specific sections; all anchors and IDs preserved. "
                            "_Synthetic entry added by `migrate_v1_to_v2`; edit to record actual "
                            "v" + meta_version + " session work if any._"
                        ),
                    }
                ],
            }
            entries.insert(0, synth)

    parts = [
        "<!-- @anchor: changelog -->",
        "## Changelog",
        "",
        "Newest first. The first entry is implicitly the current version.",
        "",
    ]
    for entry in entries:
        ver = entry.get("version", "?")
        ver_clean = re.sub(r"^v", "", str(ver), flags=re.IGNORECASE)
        body = render_blocks(entry.get("blocks", []) or [], heading_offset=1)
        parts.append(f"### v{ver_clean}")
        parts.append("")
        if body:
            parts.append(body)
            parts.append("")

    parts.append("<!-- @end: changelog -->")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Top-level migration
# ---------------------------------------------------------------------------


SPECIAL_TABS = {"overview", "research", "changelog"}


def migrate(doc: Doc) -> str:
    meta = doc.get("meta", {}) or {}
    ps = (doc.get("agent_guidelines") or {}).get("project_specific") or {}
    ui = meta.get("ui_strings") or {}

    domain_tabs = [t for t in doc.get("tabs", []) if t.get("id") not in SPECIAL_TABS]
    research_tab: Doc = next((t for t in doc.get("tabs", []) if t.get("id") == "research"), {})

    sections: list[str] = []
    sections.append(build_frontmatter(doc))
    sections.append("")
    sections.append(build_title(meta))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(load_framework_block_from_starter())
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_project_specification(ps))
    sections.append("")
    sections.append("---")
    sections.append("")

    domain_tab_labels: list[str] = []
    for tab in domain_tabs:
        sections.append(build_domain_tab(tab))
        sections.append("")
        sections.append("---")
        sections.append("")
        domain_tab_labels.append(tab.get("label", tab.get("id", "")))

    sections.append(build_open_research_queue(research_tab, ui))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_research_tracker(research_tab))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_adopted_rules_index(domain_tab_labels))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_discarded_alternatives(research_tab))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_session_notes(research_tab))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_reasoning_journey(research_tab))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_references(research_tab))
    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(build_changelog(doc))

    text = "\n".join(sections)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text.endswith("\n"):
        text += "\n"
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def derive_output_path(input_path: Path, doc: Doc) -> Path:
    meta = doc.get("meta", {}) or {}
    file_name = str(meta.get("file_name") or "")
    # Strip .json first, then any version suffix
    file_name = re.sub(r"\.json$", "", file_name)
    file_name = re.sub(r"_v\d+(?:[._]\d+)*$", "", file_name)
    if not file_name:
        file_name = input_path.stem
    version = meta.get("version") or "?"
    return input_path.parent / f"{file_name}_v{version}-source.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate a research-buddy v1 JSON document to v2 Markdown source format."
    )
    parser.add_argument("input", type=Path, help="Path to the v1 *.json file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: {file_name}_v{version}-source.md alongside input)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"Error: {args.input} not found", file=sys.stderr)
        return 2

    try:
        doc = json.loads(args.input.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: {args.input} is not valid JSON: {e}", file=sys.stderr)
        return 2

    out = args.output or derive_output_path(args.input, doc)
    if out.exists() and not args.force:
        print(
            f"Error: {out} already exists. Use --force to overwrite, or specify -o.",
            file=sys.stderr,
        )
        return 2

    text = migrate(doc)
    out.write_text(text, encoding="utf-8")

    in_size = args.input.stat().st_size
    out_size = out.stat().st_size
    print(f"\u2714  {args.input.name} \u2192 {out.name} ({in_size:,} \u2192 {out_size:,} bytes)")
    print(f"   Now run: research-buddy validate {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
