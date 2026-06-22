"""Migrate a research-buddy v1 JSON document to a v2 Markdown source file.

Transformations:
- meta.* + project spec (the filled top-level `project_specific`, falling back to
  `agent_guidelines.project_specific`) → YAML frontmatter
- agent_guidelines.framework + session_protocol → DROPPED (replaced by v2 framework
  block, copied from the installed starter.md)
- tabs[overview] → an "Overview" domain tab placed after Project Specification; only
  navigation sections (Quick Links / How to Navigate) are dropped, substantive
  sections (Project Goal, Working Hypotheses, …) survive as H3 subsections
- tabs[research] sections → top-level H2 sections (Open Research Queue, Research
  Tracker, Reasoning Journey, References, Discarded Alternatives, and per-Q
  Session Notes coalesced into a single ## Session Notes H2)
- tabs[skill-spec], tabs[system-design], tabs[meta-validation], or any other
  domain-specific tab → H2 sections placed AFTER Project Specification, with each
  original section becoming an H3 subsection. Verdict blocks (badge=adopt|rule)
  become <!-- @rule: ... --> blocks; verdict blocks (badge=reject) inside research
  Discarded Alternatives become <!-- @da: ... --> blocks.
- section.subsections (any depth) → nested H4/H5/H6 headings (see
  render_subsections). The v1 schema nests most of a mature document's content
  here; dropping it lost the bulk of theory/discarded/reference material and the
  architecture diagrams.
- Rich blocks keep their chrome instead of flattening: svg → raw inline <svg>
  (EL-09); card_grid / phase_cards → ```rb-cards; agnostic_banner / cc_banner /
  usage_banner → ```rb-banner.
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

from research_buddy import __version__
from research_buddy.build import _LANGUAGE_NAME_TO_CODE
from research_buddy.fileio import atomic_write

Doc = dict[str, Any]
Block = dict[str, Any]


# ---------------------------------------------------------------------------
# Project-specification + language resolution
# ---------------------------------------------------------------------------

# Older v1 docs (pre-1.x schema) keep the real, filled project spec at the top
# level as doc["project_specific"], while the agent_guidelines copy stays an
# untouched [FILL] template. The two blocks also diverge on a handful of key
# names; normalize the top-level vocabulary to the agent_guidelines one.
_TOP_LEVEL_PS_ALIASES = {
    "deliverable": "deliverable_type",
    "timeline": "timing",
}
_TOP_LEVEL_TIER_ALIASES = {
    "tier_3": "discovery",
    "never_tier": "never",
}


def _is_filled(value: Any) -> bool:
    """True if `value` carries real content (not empty, not a `[FILL]` stub)."""
    if value is None:
        return False
    if isinstance(value, str):
        s = value.strip()
        return bool(s) and "[fill" not in s.lower()
    if isinstance(value, list):
        return any(_is_filled(v) for v in value)
    if isinstance(value, dict):
        return any(_is_filled(v) for k, v in value.items() if not str(k).startswith("_"))
    return True


def _normalize_top_level_ps(raw: Any) -> Doc:
    """Rename the divergent top-level keys to the agent_guidelines vocabulary."""
    if not isinstance(raw, dict):
        return {}
    ps: Doc = {_TOP_LEVEL_PS_ALIASES.get(str(key), str(key)): val for key, val in raw.items()}
    st = ps.get("source_tiers")
    if isinstance(st, dict):
        ps["source_tiers"] = {
            _TOP_LEVEL_TIER_ALIASES.get(str(key), str(key)): val for key, val in st.items()
        }
    return ps


def _merge_ps(primary: Doc, fallback: Doc) -> Doc:
    """Field-level merge: keep `primary` values that are filled, else fall back.

    `source_tiers` is merged per-tier so a half-filled tiers block recovers the
    missing tiers from `fallback` instead of being taken wholesale.
    """
    merged: Doc = dict(fallback)
    for key, val in primary.items():
        if key == "source_tiers":
            continue
        if _is_filled(val) or key not in merged:
            merged[key] = val

    p_st = primary.get("source_tiers")
    f_st = fallback.get("source_tiers")
    if isinstance(p_st, dict) or isinstance(f_st, dict):
        st_merged: Doc = dict(f_st) if isinstance(f_st, dict) else {}
        if isinstance(p_st, dict):
            for key, val in p_st.items():
                if _is_filled(val) or key not in st_merged:
                    st_merged[key] = val
        merged["source_tiers"] = st_merged
    return merged


def resolve_project_spec(doc: Doc) -> Doc:
    """The effective project spec for migration.

    Mature v1 docs leave `agent_guidelines.project_specific` as the untouched
    `[FILL]` template and keep the real spec at the top level
    (`doc["project_specific"]`, with a few divergent key names). Prefer the
    agent_guidelines copy per-field when it has actually been filled in,
    otherwise recover the (key-normalized) top-level value — so domain / goal /
    source tiers aren't lost to the stale template.
    """
    guidelines = (doc.get("agent_guidelines") or {}).get("project_specific") or {}
    if not isinstance(guidelines, dict):
        guidelines = {}
    top = _normalize_top_level_ps(doc.get("project_specific") or {})
    return _merge_ps(guidelines, top)


def resolve_language(meta: Doc) -> dict[str, str]:
    """Coerce `meta.language` (string or object) to a `{code, label}` dict.

    Older docs store the language as a bare string (`"English"`); the v2
    frontmatter wants an object. Map a known label to a BCP-47 code, falling
    back to `"und"` (undetermined) for an unrecognized label.
    """
    raw = meta.get("language")
    if isinstance(raw, dict):
        label = str(raw.get("label") or "English")
        code = raw.get("code") or _LANGUAGE_NAME_TO_CODE.get(label.strip().lower(), "und")
        return {"code": str(code), "label": label}
    if isinstance(raw, str) and raw.strip():
        label = raw.strip()
        return {"code": _LANGUAGE_NAME_TO_CODE.get(label.lower(), "und"), "label": label}
    return {"code": "en", "label": "English"}


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def _frontmatter_source_tiers(ps: Doc) -> Doc:
    """The `project.source_tiers` frontmatter block (tier_1 / tier_2 / discovery).

    Mirrors the canonical shape in `starter.md`: the three named tiers, each
    carrying the resolved value or `None` when the v1 spec didn't supply it.
    (The fixed "Never" tier lives in the framework, not the frontmatter.)
    """
    st = ps.get("source_tiers")
    st = st if isinstance(st, dict) else {}
    return {
        "tier_1": st.get("tier_1"),
        "tier_2": st.get("tier_2"),
        "discovery": st.get("discovery"),
    }


def build_frontmatter(doc: Doc) -> str:
    meta = doc.get("meta", {}) or {}
    ps = resolve_project_spec(doc)
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
        "doc_format_version": 2,
        "research_buddy_version": __version__,
        "version": version_str,
        "date": meta.get("date"),
        "file_name": file_name or None,
        "title": meta.get("title"),
        "subtitle": meta.get("subtitle"),
        "language": resolve_language(meta),
        "project": {
            "domain": ps.get("domain"),
            "deliverable_type": ps.get("deliverable_type"),
            "final_goal": ps.get("final_goal"),
            "timing": ps.get("timing"),
            "validation_gate": ps.get("validation_gate"),
            "source_tiers": _frontmatter_source_tiers(ps),
            "domain_rules": ps.get("domain_rules"),
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


def _yaml_block(payload: Any) -> str:
    """Serialise `payload` to a YAML body suitable for an `rb-*` fence."""
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip("\n")


def _as_str_list(value: Any) -> list[str]:
    """Coerce a v1 `items`-style value to a list of strings.

    The schema expects a list, but migration may run on unvalidated JSON: a
    `null` becomes `[]`, and a bare string becomes a single-item list rather
    than being iterated character-by-character.
    """
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _as_dict_list(value: Any) -> list[Block]:
    """Coerce a v1 `cards`-style value to a list of dict blocks (drop the rest)."""
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, dict)]


def _cards_fence(cards: list[Block]) -> str:
    """Emit a `rb-cards` fence (v2 EL-12) from a list of `{title, body}` dicts.

    Mirrors the v1 `card_grid` / `phase_cards` chrome instead of flattening the
    cards to plain prose. Empty card lists collapse to an empty string so the
    block is dropped rather than emitting an empty fence.
    """
    items: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        entry: dict[str, Any] = {"title": str(card.get("title") or "")}
        if card.get("icon"):
            entry["icon"] = str(card["icon"])
        body = str(card.get("body") or "").strip()
        if body:
            entry["body"] = body
        items.append(entry)
    if not items:
        return ""
    return f"```rb-cards\n{_yaml_block(items)}\n```"


def _render_card_grid(blk: Block) -> str:
    cards = [
        {"title": c.get("title") or "", "body": (c.get("md") or "").strip()}
        for c in _as_dict_list(blk.get("cards"))
    ]
    return _cards_fence(cards)


def _render_phase_cards(blk: Block) -> str:
    """v1 `phase_cards` → `rb-cards`. Each phase's `items` list becomes a
    Markdown bullet list in the card body so nothing is lost.
    """
    cards: list[dict[str, Any]] = []
    for c in _as_dict_list(blk.get("cards")):
        title = c.get("title") or c.get("phase") or ""
        body = "\n".join(f"- {it}" for it in _as_str_list(c.get("items")))
        cards.append({"title": title, "body": body})
    return _cards_fence(cards)


def _render_banner(blk: Block, kind: str) -> str:
    """v1 `agnostic_banner` / `cc_banner` → `rb-banner <kind>` fence (EL-13)."""
    payload: dict[str, Any] = {"title": str(blk.get("title") or "")}
    body = (blk.get("md") or "").strip()
    if body:
        payload["body"] = body
    return f"```rb-banner {kind}\n{_yaml_block(payload)}\n```"


def _render_usage_banner(blk: Block) -> str:
    """v1 `usage_banner` → `rb-banner usage` fence (EL-13)."""
    payload: dict[str, Any] = {"title": str(blk.get("title") or "")}
    items = _as_str_list(blk.get("items"))
    if items:
        payload["items"] = items
    return f"```rb-banner usage\n{_yaml_block(payload)}\n```"


def _render_svg(blk: Block) -> str:
    """v1 `svg` → raw inline SVG (EL-09).

    The v2 renderer passes raw HTML through, so the diagram survives verbatim.
    Internal blank lines are collapsed: a blank line would split the CommonMark
    HTML block and truncate the passthrough.
    """
    svg = blk.get("html")
    if not isinstance(svg, str):
        return ""
    svg = svg.strip()
    if not svg:
        return ""
    return re.sub(r"\n\s*\n+", "\n", svg)


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


def _slug(text: str) -> str:
    """Lowercase, hyphenate non-alphanumerics — a valid HTML id / anchor slug.

    For a well-formed rule id (`R-FM-1`) this is a no-op beyond lowercasing
    (`r-fm-1`); for a label that lacks a clean `R-`/`DA-` prefix it strips
    spaces and punctuation that would otherwise produce an invalid `<a id>`.
    """
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _render_verdict_as_rule(blk: Block) -> str:
    label = blk.get("label", "")
    parsed = parse_rule_label(label)
    rid = parsed["id"]
    aid = _slug(rid)
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
    aid = _slug(rid)
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
    if t in {"p", "paragraph"}:
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
        return _render_svg(blk)
    if t == "phase_cards":
        return _render_phase_cards(blk)
    if t == "agnostic_banner":
        return _render_banner(blk, "agnostic")
    if t == "cc_banner":
        return _render_banner(blk, "cc")
    return f"<!-- unknown block type: {t} -->"


def render_blocks(blocks: list[Block], heading_offset: int = 0) -> str:
    rendered = [render_block(b, heading_offset) for b in blocks if b]
    rendered = [r for r in rendered if r]
    return "\n\n".join(rendered)


def render_subsections(sec: Block, start_level: int) -> str:
    """Render a v1 section's `subsections` recursively as nested Markdown
    headings.

    The v1 schema nests content under `section.subsections.<name>.{blocks,
    subsections}`; `build.py` renders that tree recursively. Without this the
    migration silently dropped every subsection (the bulk of a mature
    document — theory derivations, discarded-alternative records, per-version
    reference groups, and the architecture SVGs all live in subsections).

    Each subsection name becomes a heading at `start_level` (clamped to
    H3-H6), its blocks render one level deeper than that heading, and nested
    subsections recurse at `start_level + 1`. Names beginning with `_` are
    treated as private metadata and skipped, matching `build_domain_tab`.
    """
    subsections = sec.get("subsections")
    if not isinstance(subsections, dict):
        return ""
    out: list[str] = []
    for name, sub in subsections.items():
        if str(name).startswith("_") or not isinstance(sub, dict):
            continue
        level = max(3, min(6, start_level))
        clean = re.sub(r"^#+\s*", "", str(name)).strip()
        out.append(f"{_heading_prefix(level)} {clean}")
        out.append("")
        body = render_blocks(sub.get("blocks") or [], heading_offset=max(0, level - 2))
        if body:
            out.append(body)
            out.append("")
        nested = render_subsections(sub, start_level + 1)
        if nested:
            out.append(nested)
            out.append("")
    return "\n".join(out).rstrip("\n")


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


# Plain-slug anchors the framework's own sections own. A migrated domain tab
# whose label slugs to one of these is mangled (suffixed `-tab`) so the two
# never emit the same `<!-- @anchor: X -->`. Dotted anchors (framework.core,
# project.tiers, …) can't collide with a slugified label, so they're omitted.
CANONICAL_ANCHORS = {
    "title",
    "project",
    "overview",
    "queue",
    "tracker",
    "journey",
    "references",
    "discarded",
    "rules",
    "sessions",
    "changelog",
}


def build_domain_tab(tab: Doc, skip_sections: set[str] | None = None) -> str:
    """Render a domain-specific tab as an H2 section.

    `skip_sections` (matched case-insensitively) is dropped — used for the
    overview tab, whose navigation sections (Quick Links / How to Navigate) are
    obsolete in v2 but whose substantive sections must survive.
    """
    label = tab.get("label") or tab.get("id") or "Untitled"
    anchor_id = _slug(label)
    # A domain-tab label that slugs to a canonical framework anchor (e.g. a tab
    # literally named "References" or "Changelog") would emit a duplicate
    # `@anchor`. Mangle it so the framework's own section keeps the canonical id.
    if anchor_id in CANONICAL_ANCHORS:
        anchor_id = f"{anchor_id}-tab"
    skip = {s.strip().lower() for s in (skip_sections or set())}

    parts = [
        f"<!-- @anchor: {anchor_id} -->",
        f"## {label}",
        "",
    ]

    for sec_name, sec in tab.get("sections", {}).items():
        if sec_name.startswith("_") or sec_name.strip().lower() in skip:
            continue
        parts.append(f"### {sec_name}")
        parts.append("")
        body = render_blocks(sec.get("blocks", []), heading_offset=1)
        if body:
            parts.append(body)
            parts.append("")
        subs = render_subsections(sec, start_level=4)
        if subs:
            parts.append(subs)
            parts.append("")

    parts.append(f"<!-- @end: {anchor_id} -->")
    return "\n".join(parts)


# Overview-tab sections that are pure navigation chrome — obsolete in v2 (the
# single-page layout has no tabs to link between), so they're dropped. Anything
# else in the overview tab is substantive research content and is preserved.
OVERVIEW_NAV_SECTIONS = {
    "quick links",
    "quick navigation",
    "how to navigate",
    "how-to-navigate",
    "navigation",
    "navigate",
    "at a glance",
}


def _section_has_content(sec: Doc) -> bool:
    return bool(render_blocks(sec.get("blocks", []), heading_offset=1)) or bool(
        render_subsections(sec, start_level=4)
    )


def build_overview_tab(tab: Doc) -> str:
    """Render the v1 `overview` tab, dropping only navigation sections.

    Returns "" when nothing substantive survives (a pure Quick-Links / How-to-
    Navigate tab), so the caller can omit the section entirely.
    """
    substantive = {
        name: sec
        for name, sec in (tab.get("sections") or {}).items()
        if not str(name).startswith("_")
        and str(name).strip().lower() not in OVERVIEW_NAV_SECTIONS
        and isinstance(sec, dict)
        and _section_has_content(sec)
    }
    if not substantive:
        return ""
    return build_domain_tab(
        {
            "id": tab.get("id", "overview"),
            "label": tab.get("label") or "Overview",
            "sections": substantive,
        },
        skip_sections=OVERVIEW_NAV_SECTIONS,
    )


def _tracker_ids(research_tab: Doc) -> set[str]:
    """Q-NNN IDs already recorded in the Research Tracker."""
    section = (research_tab.get("sections") or {}).get("Research Tracker") or {}
    table_block = next(
        (b for b in section.get("blocks", []) if b.get("type") == "table"),
        None,
    )
    if table_block is None:
        return set()
    ids: set[str] = set()
    for row in table_block.get("rows", []):
        m = re.search(r"\bQ-\d+\b", " ".join(str(c) for c in row))
        if m:
            ids.add(m.group(0))
    return ids


def _row_done(row: list[str], status_col: int, done_glyph: str, tracker_ids: set[str]) -> bool:
    """A master-queue row is done if its status reads researched/✦, or its ID
    is already in the Research Tracker (the "no ID in both queue and tracker"
    invariant)."""
    if status_col >= 0 and status_col < len(row):
        cell = str(row[status_col]).strip()
        # ✦ glyph (the leading token of e.g. "✦ Researched"), OR a cell that
        # *starts* with "Researched vX.Y" (no glyph) — both mean done. The
        # anchor avoids false positives like "Not Researched" / "Not yet
        # researched", which are open statuses, not done ones.
        if done_glyph and done_glyph in cell:
            return True
        if cell.startswith("✦") or re.match(r"researched\b", cell, re.IGNORECASE):
            return True
    if tracker_ids:
        m = re.search(r"\bQ-\d+\b", " ".join(str(c) for c in row))
        if m and m.group(0) in tracker_ids:
            return True
    return False


def _strip_done_rows_from_queue(
    table_block: Block, ui: Doc, tracker_ids: set[str] | None = None
) -> tuple[list[str], list[list[str]]]:
    headers = list(table_block.get("headers", []))
    rows = list(table_block.get("rows", []))
    status_done_token = ui.get("status_done", "✦ Researched")
    glyph_tokens = status_done_token.split()
    done_glyph = glyph_tokens[0] if glyph_tokens else ""
    tracker_ids = tracker_ids or set()

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
        if _row_done(row, status_col, done_glyph, tracker_ids):
            continue
        keep_rows.append(row)

    new_headers = [h for i, h in enumerate(headers) if i not in drop_idx]
    new_rows: list[list[str]] = []
    for row in keep_rows:
        new_rows.append([c for i, c in enumerate(row) if i not in drop_idx])

    has_id_col = bool(new_rows) and bool(re.match(r"^Q-\d+", str(new_rows[0][0])))
    if not has_id_col and new_rows:
        # First pass: pull the IDs rows already carry, so synthesized IDs can
        # avoid colliding with them OR with IDs already in the tracker. The old
        # `Q-{i+1}` (row-index) scheme could hand an unlabeled row the same ID
        # as a labeled sibling, or one already used by a done (tracker) item.
        used: set[str] = set(tracker_ids)
        parsed: list[tuple[str | None, str]] = []  # (existing_id, topic_text)
        for row in new_rows:
            topic = row[0] if row else ""
            m = re.match(r"^(Q-\d+)\b", topic)
            if m:
                used.add(m.group(1))
                parsed.append((m.group(1), topic[m.end() :].lstrip(" -—:")))
            else:
                parsed.append((None, topic))
        # Second pass: assign, synthesizing the lowest free Q-NNN for the rest.
        counter = 1
        for row, (existing, topic_text) in zip(new_rows, parsed, strict=True):
            if existing is not None:
                qid = existing
            else:
                while f"Q-{counter:03d}" in used:
                    counter += 1
                qid = f"Q-{counter:03d}"
                used.add(qid)
            row[0] = topic_text
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
        headers, rows = _strip_done_rows_from_queue(table_block, ui, _tracker_ids(research_tab))
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
    subs = render_subsections(section, start_level=3)
    if subs:
        body_blocks.append(subs)
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
        subs = render_subsections(sec, start_level=4)
        if subs:
            parts.append(subs)
            parts.append("")

    # Catch-all: research-tab sections that aren't reserved (handled by another
    # builder) and aren't `Session Notes — Q-NNN` (captured above) are per-topic
    # research notes under an idiosyncratic v1 layout. Without this they were
    # dropped entirely. Render each as a topic subsection so their content
    # (and any nested subsections) survives the migration.
    for sec_name, sec in (research_tab.get("sections") or {}).items():
        if sec_name.startswith("_") or sec_name in RESERVED_RESEARCH_SECTIONS:
            continue
        if re.match(r"^Session Notes\s*[—-]\s*Q-\d+", sec_name):
            continue
        body = render_blocks(sec.get("blocks") or [], heading_offset=1)
        subs = render_subsections(sec, start_level=4)
        if not body and not subs:
            continue
        parts.append(f"### {sec_name}")
        parts.append("")
        if body:
            parts.append(body)
            parts.append("")
        if subs:
            parts.append(subs)
            parts.append("")

    parts.append("<!-- @end: sessions -->")
    return "\n".join(parts)


def build_reasoning_journey(research_tab: Doc) -> str:
    section = (research_tab.get("sections") or {}).get("Reasoning Journey") or {}
    body = render_blocks(section.get("blocks", []), heading_offset=0)
    subs = render_subsections(section, start_level=3)
    body = "\n\n".join(p for p in (body, subs) if p)
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
    subs = render_subsections(section, start_level=3)
    body = "\n\n".join(p for p in (body, subs) if p)
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

    def _key(e: Doc) -> tuple[int, ...]:
        # Sort on (major, minor, patch). The old (major, minor)-only key
        # collapsed 1.1.0 and 1.1.4 to the same value, so distinct entries
        # sorted unstably and could swap order between runs.
        nums = [int(n) for n in re.findall(r"\d+", str(e.get("version", "")))]
        return tuple([*nums, 0, 0, 0][:3])

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
                "date": meta.get("date"),
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
        date = str(entry.get("date") or "").strip()
        body = render_blocks(entry.get("blocks", []) or [], heading_offset=1)
        heading = f"### v{ver_clean} — {date}" if date else f"### v{ver_clean}"
        parts.append(heading)
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

# Research-tab sections that have a dedicated builder. Anything else in the
# research tab is treated as per-topic session notes by `build_session_notes`'s
# catch-all (some v1 docs name session notes after the topic rather than
# `Session Notes — Q-NNN`). `Research Methodology` is intentionally dropped —
# the v2 in-file framework replaces it.
RESERVED_RESEARCH_SECTIONS = {
    "Open Research Queue",
    "Research Tracker",
    "Reasoning Journey",
    "References",
    "Discarded Alternatives",
    "Research Methodology",
}


def migrate(doc: Doc) -> str:
    meta = doc.get("meta", {}) or {}
    ps = resolve_project_spec(doc)
    ui = meta.get("ui_strings") or {}

    domain_tabs = [t for t in doc.get("tabs", []) if t.get("id") not in SPECIAL_TABS]
    overview_tab: Doc = next((t for t in doc.get("tabs", []) if t.get("id") == "overview"), {})
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

    overview_md = build_overview_tab(overview_tab) if overview_tab else ""
    if overview_md:
        sections.append(overview_md)
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
    atomic_write(out, text)

    in_size = args.input.stat().st_size
    out_size = out.stat().st_size
    print(f"\u2714  {args.input.name} \u2192 {out.name} ({in_size:,} \u2192 {out_size:,} bytes)")
    print(f"   Now run: research-buddy validate {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
