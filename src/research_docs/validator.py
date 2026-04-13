"""Schema validation for research documents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema

from research_docs.build import slugify

Doc = dict[str, Any]

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "document.schema.json"


def _load_schema() -> Doc:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
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


def _collect_all_ids(doc: Doc) -> list[str]:
    """Gather every ID that will be generated in the HTML."""
    ids: list[str] = []

    # Meta title page (implied ID from its title)
    title_sec = doc["meta"].get("title_page_section_title")
    if title_sec:
        ids.append(slugify(title_sec))

    # Tab sections
    for tab in doc.get("tabs", []):

        def _walk(secs: dict[str, Any]) -> None:
            for title, sec in secs.items():
                ids.append(slugify(title))
                ids.extend(_collect_block_ids(sec.get("blocks", [])))
                _walk(sec.get("subsections", {}))

        _walk(tab.get("sections", {}))

    # Changelog (legacy structure check if still present)
    cl = doc.get("changelog")
    if cl:
        for entry in cl.get("entries", []):
            ids.append(_ensure_entry_id(entry))

    return ids


def _parse_ver(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def _parse_date(d: str) -> tuple[int, ...]:
    """Parse date string into a sortable tuple.
    Supports YYYY-MM-DD and 'Month YYYY'.
    """
    # Try YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Try Month YYYY
    months = {
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
    parts = d.lower().split()
    if len(parts) == 2 and parts[0] in months and parts[1].isdigit():
        return (int(parts[1]), months[parts[0]], 0)

    # Fallback to numeric extraction
    nums = [int(x) for x in re.findall(r"\d+", d)]
    return tuple(nums)


def _validate_references(doc: Doc) -> list[str]:
    warnings = []
    for tab in doc.get("tabs", []):

        def _walk(secs: dict[str, Any]) -> None:
            for title, sec in secs.items():
                for b in sec.get("blocks", []):
                    if b.get("type") == "references":
                        items = b.get("items", [])
                        # Check version ordering (should be descending)
                        versions = [i.get("version") for i in items if i.get("version")]
                        if len(versions) > 1:
                            parsed_v = [_parse_ver(v) for v in versions]
                            if parsed_v != sorted(parsed_v, reverse=True):
                                warnings.append(
                                    f"REFERENCE ORDER in '{title}': versions not descending"
                                )
                        # Check date ordering (should be descending)
                        dates = [i.get("date") for i in items if i.get("date")]
                        if len(dates) > 1:
                            parsed_d = [_parse_date(d) for d in dates]
                            if parsed_d != sorted(parsed_d, reverse=True):
                                warnings.append(
                                    f"REFERENCE ORDER in '{title}': dates not descending"
                                )
                _walk(sec.get("subsections", {}))

        _walk(tab.get("sections", {}))
    return warnings


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

    return warnings
