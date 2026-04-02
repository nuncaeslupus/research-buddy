"""Document validation — JSON Schema + semantic checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from research_docs.build import _collect_block_ids, _ensure_entry_id, build_changelog_nav

Doc = dict[str, Any]

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "document.schema.json"


def _load_schema() -> Doc:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def validate_schema(doc: Doc) -> list[str]:
    """Validate document against JSON Schema. Returns list of error messages."""
    schema = _load_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[{path}] {error.message}")
    return errors


def validate_links(doc: Doc) -> list[str]:
    """Cross-reference nav hrefs against content IDs. Returns warnings."""
    tabs = doc["tabs"]
    sections = doc["sections"]
    changelog = doc.get("changelog", {})

    all_ids: list[str] = []

    for sid, sec in sections.items():
        all_ids.append(sid)
        all_ids.extend(_collect_block_ids(sec.get("blocks", [])))

    if changelog:
        all_ids.append("cl-protocol")
        for entry in changelog.get("entries", []):
            eid = _ensure_entry_id(entry)
            if eid:
                all_ids.append(eid)

    for tab in tabs:
        all_ids.append(f"tab-{tab['id']}")

    warnings: list[str] = []

    # duplicate IDs
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

    # sections defined but not referenced
    referenced: set[str] = set()
    for tab in tabs:
        referenced.update(tab.get("sections", []))
    for sid in sections:
        if sid not in referenced:
            warnings.append(f"ORPHAN SECTION: '{sid}' defined but not in any tab")

    # changelog entries without ids
    if changelog:
        for i, entry in enumerate(changelog.get("entries", [])):
            if not entry.get("id"):
                ver = entry.get("version", f"index {i}")
                warnings.append(f"CHANGELOG: entry '{ver}' has no id (will be auto-generated)")

    return warnings


def validate(doc: Doc) -> list[str]:
    """Run all validations. Returns combined list of issues."""
    issues = validate_schema(doc)
    issues.extend(validate_links(doc))
    return issues
