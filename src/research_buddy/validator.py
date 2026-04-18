"""Schema validation for research documents."""

from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

import jsonschema

from research_buddy import __version__ as TOOL_VERSION
from research_buddy.build import slugify

Doc = dict[str, Any]


def _load_schema() -> Doc:
    ref = resources.files("research_buddy") / "schema.json"
    with ref.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


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

    def _version_sort_key(entry: Doc) -> tuple[int, int]:
        ver = entry.get("version", "") or entry.get("id", "")
        m = re.search(r"(\d+)\.(\d+)", ver)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

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
    return [{"label": "", "items": items}]


def _collect_block_ids(blocks: list[dict[str, Any]]) -> list[str]:
    """Helper to gather IDs from content blocks."""
    ids: list[str] = []
    for b in blocks:
        bid = b.get("id")
        if bid:
            ids.append(bid)
        elif b.get("type") in ("h3", "h4", "heading"):
            text = b.get("md") or b.get("content") or ""
            if text:
                ids.append(slugify(text))
    return ids


def _walk_section_ids(secs: dict[str, Any], ids: list[str]) -> None:
    """Recursively collect slugified titles + block IDs from a section tree."""
    for title, sec in secs.items():
        ids.append(slugify(title))
        ids.extend(_collect_block_ids(sec.get("blocks", [])))
        _walk_section_ids(sec.get("subsections", {}), ids)


def _collect_all_ids(doc: Doc) -> list[str]:
    """Gather every ID that will be generated in the HTML."""
    ids: list[str] = []

    # Meta title page (implied ID from its title)
    title_sec = doc["meta"].get("title_page_section_title")
    if title_sec:
        ids.append(slugify(title_sec))

    # Tab sections
    for tab in doc.get("tabs", []):
        _walk_section_ids(tab.get("sections", {}), ids)

    # Changelog (legacy structure check if still present)
    cl = doc.get("changelog")
    if cl:
        for entry in cl.get("entries", []):
            ids.append(_ensure_entry_id(entry))

    return ids


def _parse_ver(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v))


_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_date(d: str) -> tuple[int, ...]:
    """Parse date string into a sortable tuple.
    Supports YYYY-MM-DD and 'Month YYYY'.
    """
    if not isinstance(d, str):
        return (0, 0, 0)

    # Try YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Try Month YYYY
    parts = d.lower().split()
    if len(parts) == 2 and parts[0] in _MONTHS and parts[1].isdigit():
        return (int(parts[1]), _MONTHS[parts[0]], 0)

    # Fallback to numeric extraction
    nums = [int(x) for x in re.findall(r"\d+", d)]
    return tuple(nums)


def _validate_references(doc: Doc) -> list[str]:
    warnings: list[str] = []
    for tab in doc.get("tabs", []):
        _walk_references(tab.get("sections", {}), warnings)
    return warnings


def _walk_references(secs: dict[str, Any], warnings: list[str]) -> None:
    """Recursively scan sections for `references` blocks and check ordering."""
    for title, sec in secs.items():
        for b in sec.get("blocks", []):
            if b.get("type") == "references":
                items = b.get("items", [])
                # Check version ordering (should be descending)
                versions = [i.get("version") for i in items if i.get("version")]
                if len(versions) > 1:
                    parsed_v = [_parse_ver(v) for v in versions]
                    if parsed_v != sorted(parsed_v, reverse=True):
                        warnings.append(f"REFERENCE ORDER in '{title}': versions not descending")
                # Check date ordering (should be descending)
                dates = [i.get("date") for i in items if i.get("date")]
                if len(dates) > 1:
                    parsed_d = [_parse_date(d) for d in dates]
                    if parsed_d != sorted(parsed_d, reverse=True):
                        warnings.append(f"REFERENCE ORDER in '{title}': dates not descending")
        _walk_references(sec.get("subsections", {}), warnings)


def _parse_semver(v: str) -> tuple[int, int, int] | None:
    """Parse "1.0", "1.0.3", "v1.0.3" → (major, minor, patch). Missing parts → 0.

    Returns None if the string contains no digits at all.
    """
    if not isinstance(v, str):
        return None
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", v)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0))


def _check_version_compatibility(doc_ver: str, tool_ver: str) -> list[str]:
    """Compare the document's `research_buddy_version` against the installed tool.

    Rules (MAJOR.MINOR.PATCH):
      - MAJOR mismatch → hard warning: schema is NOT guaranteed compatible.
      - Same MAJOR, tool MINOR < doc MINOR → warning: tool may silently drop newer features.
      - Same MAJOR, tool MINOR > doc MINOR → info: fully backwards-compatible.
      - PATCH-only difference → silent (patches are always compatible).
    """
    doc = _parse_semver(doc_ver)
    tool = _parse_semver(tool_ver)
    if doc is None:
        return [
            f"[meta.research_buddy_version] Unrecognized version format: {doc_ver!r}. "
            "Expected something like '1.0' or '1.0.3'."
        ]
    if tool is None:
        # The tool itself has a malformed version — not the user's problem; skip.
        return []

    d_maj, d_min, _d_patch = doc
    t_maj, t_min, _t_patch = tool

    if d_maj != t_maj:
        return [
            f"[meta.research_buddy_version] VERSION MISMATCH: document was written with "
            f"research-buddy v{doc_ver}, but you are running v{tool_ver}. "
            f"Major version differs — schema and build output may be incompatible. "
            f"Build will proceed but the HTML may be wrong or missing content. "
            f"Fix: (a) pin the matching major with "
            f"`pip install 'research-buddy=={d_maj}.*'`, OR "
            f"(b) open the document in an AI session and say "
            f"'Migrate to research-buddy v{tool_ver}' so the agent updates the structure. "
            f"See CHANGELOG.md for what changed between majors."
        ]

    if t_min < d_min:
        return [
            f"[meta.research_buddy_version] Document was last updated with research-buddy "
            f"v{doc_ver}; you are on v{tool_ver} (tool MINOR is older). "
            f"The document may use features this tool version does not render correctly. "
            f"Recommendation: `pip install --upgrade research-buddy`."
        ]

    # Tool MINOR newer than doc MINOR (or equal) with same MAJOR: silent.
    # The document is fully backwards-compatible. The agent will bump
    # meta.research_buddy_version on the next write. Emitting a warning here
    # would cause `research-buddy validate` to exit non-zero for docs that
    # require no action — confusing for CI pipelines.
    return []


def validate(doc: Doc) -> list[str]:
    """Validate document against JSON schema and internal consistency rules.

    Returns a list of warning/error strings.
    """
    warnings: list[str] = []

    # 1. Structural JSON Schema validation
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(doc), key=lambda e: str(list(e.absolute_path))):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        warnings.append(f"[{path}] {error.message}")

    # 2. Semantic validations
    warnings.extend(_validate_references(doc))

    # 3. Research Buddy version check — presence + doc/tool compatibility
    meta = doc.get("meta", {})
    rb_ver = meta.get("research_buddy_version")
    if rb_ver is None:
        warnings.append(
            "[meta.research_buddy_version] Missing — add 'research_buddy_version': "
            f"'{TOOL_VERSION}' to meta. This field is required for schema and build "
            "script version traceability."
        )
    else:
        warnings.extend(_check_version_compatibility(str(rb_ver), TOOL_VERSION))

    # 4. Language field check — accept string or {code, label} object
    lang = meta.get("language")
    if lang is not None and not isinstance(lang, (str, dict)):
        warnings.append(
            "[meta.language] Must be a string (e.g. 'English') or an object "
            "with at least a 'code' key (e.g. {'code': 'en', 'label': 'English'})."
        )
    elif isinstance(lang, dict) and "code" not in lang:
        warnings.append("[meta.language] Object form must include a 'code' key.")

    return warnings
