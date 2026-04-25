"""Template refresh: re-sync a project JSON against the installed starter.

`agent_guidelines` has three parts with distinct owners:

- `framework`        — template-owned, replaced wholesale on upgrade
- `session_protocol` — template-owned, replaced wholesale (session_zero.note preserved)
- `project_specific` — project-owned; values preserved, top-level keys
                       reordered to match the starter's canonical order.

Also bumps `meta.research_buddy_version` to the installed CLI version, and
fixes structural ordering at four levels so an agent reading top-to-bottom
encounters keys in the right order:

1. Doc top-level: agent_guidelines, meta, tabs, changelog
2. agent_guidelines: framework, session_protocol, project_specific
3. meta: starter's key order (extras preserved at end)
4. agent_guidelines.project_specific: starter's key order (extras at end)

The CLI handler in `main.py` stamps `meta.format_note` only when the
upgrade produces real changes, so a no-op re-run stays idempotent.

Equality note: dict `==` compares values but NOT key order, so a
reorder-only change would otherwise look identical to a no-op. Use
`docs_equivalent()` from this module — it walks dicts comparing both
keys-in-order and values, recursively.
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

    # Structural reordering — fix four levels of key order so an agent
    # reading the file top-to-bottom hits keys in the canonical order
    # defined by the starter. All values are preserved; only key order
    # changes. Track whether any reordering actually happened so the
    # caller's `doc == upgraded` idempotency check still works.
    reordered_at: list[str] = []

    starter_meta = starter.get("meta", {}) or {}
    starter_ps = new_ag.get("project_specific", {}) or {}

    upgraded_ag = upgraded["agent_guidelines"]
    if isinstance(upgraded_ag.get("project_specific"), dict):
        new_ps = _reorder_dict(upgraded_ag["project_specific"], list(starter_ps.keys()))
        if list(new_ps.keys()) != list(upgraded_ag["project_specific"].keys()):
            reordered_at.append("agent_guidelines.project_specific")
        upgraded_ag["project_specific"] = new_ps

    new_ag_ordered = _reorder_dict(
        upgraded_ag, ["framework", "session_protocol", "project_specific"]
    )
    if list(new_ag_ordered.keys()) != list(upgraded_ag.keys()):
        reordered_at.append("agent_guidelines")
    upgraded["agent_guidelines"] = new_ag_ordered

    new_meta = _reorder_dict(meta, list(starter_meta.keys()))
    if list(new_meta.keys()) != list(meta.keys()):
        reordered_at.append("meta")
    upgraded["meta"] = new_meta

    new_top = _reorder_dict(upgraded, ["agent_guidelines", "meta", "tabs", "changelog"])
    if list(new_top.keys()) != list(upgraded.keys()):
        reordered_at.append("top-level")
    upgraded = new_top

    if reordered_at:
        changes.append(f"keys reordered: {', '.join(reordered_at)}")

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


def _reorder_dict(d: Doc, canonical: list[str]) -> Doc:
    """Return a new dict whose keys appear in `canonical` order (when
    present in `d`), followed by any extra keys in their original order.

    Values are not copied — caller controls deep-vs-shallow.
    """
    seen: set[str] = set()
    out: Doc = {}
    for key in canonical:
        if key in d:
            out[key] = d[key]
            seen.add(key)
    for key, value in d.items():
        if key not in seen:
            out[key] = value
    return out


def docs_equivalent(a: Any, b: Any) -> bool:
    """Compare two JSON-shaped values by both value AND key order.

    Built-in `dict == dict` ignores key order, which would mask
    reorder-only upgrades. This helper treats two dicts as equivalent
    only when their keys appear in the same order and all values are
    recursively equivalent. Lists compare element-wise; scalars use `==`.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a.keys()) != list(b.keys()):
            return False
        return all(docs_equivalent(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(docs_equivalent(x, y) for x, y in zip(a, b, strict=False))
    return bool(a == b)


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
