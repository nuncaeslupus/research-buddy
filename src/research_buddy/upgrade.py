"""Template refresh: re-sync a project JSON against the installed starter.

`agent_guidelines` has three parts with distinct owners:

- `framework`        — template-owned, replaced wholesale on upgrade
- `session_protocol` — template-owned, replaced wholesale (session_zero.note preserved)
- `project_specific` — project-owned, never touched

Also bumps `meta.research_buddy_version` to the installed CLI version.
The CLI handler in `main.py` stamps `meta.format_note` only when the
upgrade produces real changes, so a no-op re-run stays idempotent.
"""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

Doc = dict[str, Any]


def upgrade_doc(
    doc: Doc, starter: Doc, installed_version: str
) -> tuple[Doc, list[str], dict[str, list[str]]]:
    """Structurally upgrade a document against the starter template.

    Returns (upgraded_doc, human_readable_change_lines, key_diffs).

    `key_diffs` shape:
        {
            "framework_added":         [...],
            "framework_removed":       [...],
            "session_protocol_added":   [...],
            "session_protocol_removed": [...],
        }

    Caller decides whether to write by comparing the returned doc to
    the input (`doc == upgraded`). This function does NOT touch
    `meta.format_note`; the CLI handler stamps it only on a real write.
    """
    upgraded = copy.deepcopy(doc)
    changes: list[str] = []

    old_ag = doc.get("agent_guidelines", {}) or {}
    new_ag = starter.get("agent_guidelines", {}) or {}

    key_diffs = _compute_key_diffs(old_ag, new_ag)

    ag = upgraded.setdefault("agent_guidelines", {})

    ag["framework"] = copy.deepcopy(new_ag.get("framework", {}))
    changes.append("framework ← starter.json")

    preserved_note = old_ag.get("session_protocol", {}).get("session_zero", {}).get("note")
    ag["session_protocol"] = copy.deepcopy(new_ag.get("session_protocol", {}))
    if preserved_note is not None:
        ag["session_protocol"].setdefault("session_zero", {})["note"] = preserved_note
        changes.append("session_protocol ← starter.json (session_zero.note preserved)")
    else:
        changes.append("session_protocol ← starter.json")

    if "project_specific" not in ag:
        ag["project_specific"] = copy.deepcopy(new_ag.get("project_specific", {}))
        changes.append("project_specific ← starter.json (was missing)")
    else:
        changes.append("project_specific: unchanged")

    meta = upgraded.setdefault("meta", {})
    old_rb = meta.get("research_buddy_version", "unknown")
    meta["research_buddy_version"] = installed_version
    if old_rb != installed_version:
        changes.append(f"meta.research_buddy_version: {old_rb} → {installed_version}")

    return upgraded, changes, key_diffs


def stamp_format_note(doc: Doc, installed_version: str) -> str:
    """Append a dated migration entry to `meta.format_note`.

    Mutates `doc`. Returns the appended entry for logging. Multiple entries
    accumulate on separate lines so the history stays readable.
    """
    meta = doc.setdefault("meta", {})
    version = meta.get("version", "?")
    today = date.today().isoformat()
    entry = (
        f"v{version} ({today} template refresh): agent_guidelines.framework "
        f"and agent_guidelines.session_protocol refreshed from research-buddy "
        f"{installed_version} starter.json. project_specific unchanged."
    )
    existing = (meta.get("format_note", "") or "").rstrip()
    meta["format_note"] = f"{existing}\n{entry}" if existing else entry
    return entry


def _compute_key_diffs(old_ag: Doc, new_ag: Doc) -> dict[str, list[str]]:
    def _keys(d: Doc, key: str) -> set[str]:
        val = d.get(key)
        return set(val.keys()) if isinstance(val, dict) else set()

    old_fr = _keys(old_ag, "framework")
    new_fr = _keys(new_ag, "framework")
    old_sp = _keys(old_ag, "session_protocol")
    new_sp = _keys(new_ag, "session_protocol")
    return {
        "framework_added": sorted(new_fr - old_fr),
        "framework_removed": sorted(old_fr - new_fr),
        "session_protocol_added": sorted(new_sp - old_sp),
        "session_protocol_removed": sorted(old_sp - new_sp),
    }
