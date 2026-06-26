"""v2 `diff-summary` — emit the mechanical portion of a Turn-2 change summary.

Diffs two versions of a v2 source file and produces the
`<!-- @summary-start --> ... <!-- @summary-end -->` block the framework expects
at the end of Turn 2, filling the parts a script can derive deterministically:

- version bump (`old → new`);
- queue rows that left for the tracker, and rows newly added;
- Adopted Rules added / revised;
- Discarded Alternatives added (append-only — never revised);
- Session Notes added;
- append-only-invariant check (PASS / the violations found).

The narrative sentences at the top stay agent-authored — emitted as a
`{{placeholder}}`. Reuses `validator_md._check_append_only`,
`_extract_section`, `_extract_table_first_column`, and `_parse_frontmatter`.
"""

from __future__ import annotations

import re

from research_buddy.validator_md import (
    _check_append_only,
    _extract_section,
    _extract_table_first_column,
    _parse_frontmatter,
)


def _entry_blocks(text: str, kind: str, section_anchor: str) -> dict[str, str]:
    """Map each `@kind: ID` entry in the named section to its block text
    (from the marker to the next marker / section end)."""
    section = _extract_section(text, section_anchor) or ""
    pat = re.compile(rf"<!-- @{kind}:\s*(\S+)\s*-->")
    matches = list(pat.finditer(section))
    blocks: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        blocks[m.group(1)] = section[m.start() : end].strip()
    return blocks


def _queue_ids(text: str) -> list[str]:
    section = _extract_section(text, "queue") or ""
    return [c for c in _extract_table_first_column(section) if re.match(r"^Q-\d+$", c)]


def _tracker_ids(text: str) -> list[str]:
    section = _extract_section(text, "tracker") or ""
    return [c for c in _extract_table_first_column(section) if re.match(r"^[QT]-\w+$", c)]


def _version(text: str) -> str:
    fm, _ = _parse_frontmatter(text)
    return str((fm or {}).get("version") or "?")


def build_summary(old_text: str, new_text: str) -> str:
    """Return the full `@summary-start … @summary-end` block for old → new."""
    lines: list[str] = [f"- Version: v{_version(old_text)} → v{_version(new_text)}"]

    # Queue movement.
    old_q, new_q = _queue_ids(old_text), _queue_ids(new_text)
    new_tracker = _tracker_ids(new_text)
    removed = [q for q in old_q if q not in new_q]
    added_q = [q for q in new_q if q not in old_q]
    moves: list[str] = []
    for q in removed:
        moves.append(f"{q} → tracker" if q in new_tracker else f"{q} dropped")
    moves += [f"+{q}" for q in added_q]
    if moves:
        lines.append(f"- Queue: {'; '.join(moves)}.")

    # Adopted rules added / revised.
    old_rules, new_rules = (
        _entry_blocks(old_text, "rule", "rules"),
        _entry_blocks(new_text, "rule", "rules"),
    )
    added_rules = [r for r in new_rules if r not in old_rules]
    revised_rules = [r for r in new_rules if r in old_rules and new_rules[r] != old_rules[r]]
    rule_parts = [f"+{r}" for r in added_rules] + [f"revised {r}" for r in revised_rules]
    if rule_parts:
        lines.append(f"- Adopted rules: {'; '.join(rule_parts)}.")

    # Discarded alternatives (append-only).
    old_das = _entry_blocks(old_text, "da", "discarded")
    new_das = _entry_blocks(new_text, "da", "discarded")
    added_das = [d for d in new_das if d not in old_das]
    if added_das:
        lines.append(f"- Discarded alternatives: {', '.join('+' + d for d in added_das)}.")

    # Session notes added.
    old_sessions = _entry_blocks(old_text, "session", "sessions")
    new_sessions = _entry_blocks(new_text, "session", "sessions")
    added_sessions = [s for s in new_sessions if s not in old_sessions]
    if added_sessions:
        lines.append(f"- Session notes: {', '.join('+' + s for s in added_sessions)}.")

    # Append-only invariant.
    violations = _check_append_only(old_text, new_text)
    if violations:
        detail = "; ".join(v.message for v in violations)
        lines.append(f"- Append-only invariant: FAIL — {detail}")
    else:
        lines.append("- Append-only invariant: PASS")

    body = "\n".join(lines)
    return (
        "<!-- @summary-start -->\n"
        "{{Narrative — 1-3 plain-language sentences on what this version "
        "accomplished. Reference rules / DAs / sessions by linked ID.}}\n\n"
        f"{body}\n"
        "<!-- @summary-end -->"
    )


def build_downstream_action(old_text: str, new_text: str) -> str | None:
    """Return a downstream-action block when new Adopted Rules were added, else None.

    Lists newly added rules as an unchecked checklist so the agent or user can
    propagate decisions to implementation specs or plans before the next session.
    Revised rules are not included — they refine an already-adopted decision.
    """
    old_rules = _entry_blocks(old_text, "rule", "rules")
    new_rules = _entry_blocks(new_text, "rule", "rules")
    added = [r for r in new_rules if r not in old_rules]
    if not added:
        return None
    new_version = _version(new_text)
    items = "\n".join(
        f"- [ ] [{r}](#{r.lower()}) — {{{{downstream files or specs to update}}}}" for r in added
    )
    return (
        "<!-- downstream-action-start -->\n"
        f"**Downstream action required (v{new_version}).** "
        "New decisions adopted this session may require propagation"
        " to implementation specs or plans:\n\n"
        f"{items}\n"
        "<!-- downstream-action-end -->"
    )


def has_append_only_violation(old_text: str, new_text: str) -> bool:
    return bool(_check_append_only(old_text, new_text))
