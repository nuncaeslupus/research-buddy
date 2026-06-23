"""v2 `bump` — perform the mechanical Turn-2 edits for one researched queue item.

Given a v2 source file and a `Q-NNN` queue ID, produce the next version with all
the boilerplate edits done and `{{placeholders}}` left for the agent to fill in
prose:

1. Frontmatter `version` (MINOR bump per the framework's Versioning rule) +
   `date` (today).
2. Move the `Q-NNN` row out of the [Open Research Queue] and into the
   [Research Tracker], preserving the ID and attributing the new version.
3. Insert an empty [Session Notes] skeleton for `Q-NNN` (pre-registration +
   hypothesis-resolution table + sources table + cross-section-impact line +
   compliance-validation line).
4. Prepend an empty [Changelog] entry for the new version (heading carries the
   version so the validator's changelog-version check passes, and links the
   completed `Q-NNN`).
5. Prepend an empty [References] subsection for the new version.

Everything mechanical is already correct on output; the agent fills the prose.
Dry-run by default — the CLI handler writes the new
`{file_name}_v{version}-source.md` atomically and runs `validate_md` (with the
input as `--prior`) only when `--apply` is passed.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BumpError(Exception):
    """Raised when the source file cannot be bumped (bad version, missing
    section, unknown queue ID, …)."""


# ---------------------------------------------------------------------------
# Version arithmetic
# ---------------------------------------------------------------------------


def next_minor_version(version: str) -> str:
    """Return the next MINOR version. `1.0` → `1.1`, `2.5` → `2.6`.

    The framework bumps MINOR on any content change (1.0 → 1.1 → 1.2); a
    trailing PATCH component, if present (`1.0.3`), is dropped on the bump
    since MINOR moves.
    """
    parts = version.strip().split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError) as e:
        raise BumpError(f"cannot parse version {version!r} as MAJOR.MINOR") from e
    return f"{major}.{minor + 1}"


# ---------------------------------------------------------------------------
# Section surgery (anchor-delimited bodies)
# ---------------------------------------------------------------------------


def _section_re(anchor_id: str) -> re.Pattern[str]:
    e = re.escape(anchor_id)
    return re.compile(
        rf"(<!-- @anchor:\s*{e}\s*-->)(.*?)(<!-- @end:\s*{e}\s*-->)",
        re.DOTALL,
    )


def _get_section_body(text: str, anchor_id: str) -> str:
    m = _section_re(anchor_id).search(text)
    if not m:
        raise BumpError(f"section {anchor_id!r} not found (missing @anchor/@end markers)")
    return m.group(2)


def _set_section_body(text: str, anchor_id: str, new_body: str) -> str:
    # Function replacement avoids backreference interpretation in `new_body`.
    return _section_re(anchor_id).sub(
        lambda m: f"{m.group(1)}{new_body}{m.group(3)}", text, count=1
    )


# ---------------------------------------------------------------------------
# Table-row helpers
# ---------------------------------------------------------------------------


def _comment_mask(lines: list[str]) -> list[bool]:
    """Mark lines that fall inside an HTML comment block (so the queue's
    example rows, which live inside `<!-- ... -->`, are never treated as live
    table rows)."""
    mask: list[bool] = []
    in_comment = False
    for line in lines:
        starts_inside = in_comment
        # Track open/close within the line. Naive but sufficient for the
        # single-level HTML comments the framework uses.
        idx = 0
        while True:
            if not in_comment:
                opn = line.find("<!--", idx)
                if opn < 0:
                    break
                in_comment = True
                idx = opn + 4
            else:
                cls = line.find("-->", idx)
                if cls < 0:
                    break
                in_comment = False
                idx = cls + 3
        mask.append(starts_inside)
    return mask


def _row_cells(line: str) -> list[str]:
    # Negative lookbehind so escaped pipes (\|) inside a cell aren't split on.
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _is_separator_row(line: str) -> bool:
    return bool(re.match(r"^\|\s*[-:]+", line.strip()))


def pop_queue_row(queue_body: str, queue_id: str) -> tuple[str, str]:
    """Remove the queue row whose first cell is `queue_id`; return
    (new_body, topic). Raises BumpError if the ID is not a live queue row."""
    # split("\n") (not splitlines) so the trailing blank line before the
    # @end marker survives the join below.
    lines = queue_body.split("\n")
    mask = _comment_mask(lines)
    for i, line in enumerate(lines):
        if mask[i] or not line.strip().startswith("|") or _is_separator_row(line):
            continue
        cells = _row_cells(line)
        if cells and cells[0].upper() == queue_id:
            topic = cells[1] if len(cells) > 1 else ""
            del lines[i]
            return "\n".join(lines), topic
    raise BumpError(
        f"{queue_id} is not a live row in the Open Research Queue "
        "(already researched, or never queued?)"
    )


def append_tracker_row(tracker_body: str, row: str) -> str:
    """Insert `row` immediately after the last live table row in the tracker."""
    lines = tracker_body.split("\n")  # preserve trailing blank line (see pop_queue_row)
    mask = _comment_mask(lines)
    last = -1
    for i, line in enumerate(lines):
        if not mask[i] and line.strip().startswith("|"):
            last = i
    if last < 0:
        raise BumpError("Research Tracker has no table to append to")
    lines.insert(last + 1, row)
    return "\n".join(lines)


def _append_before_end(body: str, block: str) -> str:
    """Append `block` to the end of a section body, separated by one blank
    line, preserving the trailing blank line before the `@end` marker."""
    trimmed = body.rstrip("\n")
    return f"{trimmed}\n\n{block}\n\n"


def _prepend_subsection(body: str, block: str) -> str:
    """Insert `block` immediately before the first `### ` subsection in the
    body (newest-first sections). Falls back to appending if none exists."""
    m = re.search(r"^### ", body, re.MULTILINE)
    if m:
        return f"{body[: m.start()]}{block}\n\n{body[m.start() :]}"
    return _append_before_end(body, block)


# ---------------------------------------------------------------------------
# Block builders (placeholders left for the agent to fill)
# ---------------------------------------------------------------------------


def _session_skeleton(queue_id: str, topic: str, date: str) -> str:
    anchor_id = queue_id.lower()
    topic_str = topic or "{{topic}}"
    return "\n".join(
        [
            f"<!-- @session: {queue_id} -->",
            f'<a id="{anchor_id}"></a>',
            "",
            f"### {queue_id}: {topic_str} ({date})",
            "",
            "**Pre-registration.** {{Hypotheses, PASS metric, FAIL/REJECT metric "
            "— written before consulting sources.}}",
            "",
            "**Hypothesis resolution.**",
            "",
            "| Hypothesis | Pre-registered metric | Outcome | Evidence |",
            "|---|---|---|---|",
            "| {{H1}} | {{PASS and FAIL/REJECT metrics}} | {{VALIDATED / PROPOSED / REJECTED}} "
            "| {{Tier-1 citation}} |",
            "",
            "**Sources consulted.**",
            "",
            "| Source | Tier | Verification | Disposition |",
            "|---|---|---|---|",
            "| {{...}} | {{...}} | {{...}} | {{...}} |",
            "",
            "**Decisions adopted.** {{Bulleted list; link each adopted rule by ID, e.g. R-XXX-N.}}",
            "",
            "**Rejected claims.** {{Bulleted list; link each DA by ID, e.g. DA-XXX.}}",
            "",
            "**Second-opinion evaluation.** {{Per submitted source, by label: main "
            "claims; ≥3-source verification; agreements / disagreements / "
            "unverifiables; incorporate-or-discard with rationale.}}",
            "",
            "**Cross-section impact.** {{Which sections this write touched and why.}}",
            "",
            "**Compliance validation.** {{`research-buddy validate` output (or the "
            "mental-simulation checklist) — PASS is required before delivery.}}",
        ]
    )


def _changelog_entry(queue_id: str, new_version: str, date: str) -> str:
    anchor_id = queue_id.lower()
    return "\n".join(
        [
            f"### v{new_version}: {{{{summary}}}} — {date}",
            "",
            f"{{{{What changed in v{new_version}. Decisions adopted, rejected "
            f"alternatives, contradiction-check result, second opinions reviewed. "
            f"Closes [{queue_id}](#{anchor_id}).}}}}",
        ]
    )


def _references_entry(new_version: str, date: str) -> str:
    return "\n".join(
        [
            f"### v{new_version} — {date}",
            "",
            "- {{Sources newly cited this version: Title, Author(s), Year, Venue, URL/DOI.}}",
        ]
    )


# ---------------------------------------------------------------------------
# Top-level transform
# ---------------------------------------------------------------------------


def bump_md_text(
    text: str,
    queue_id: str,
    new_version: str,
    date: str,
) -> tuple[str, str, list[str]]:
    """Apply all mechanical bump edits. Returns (new_text, topic, changes)."""
    from research_buddy.commands.init import _set_frontmatter_scalar

    changes: list[str] = []

    # 1. Queue → Tracker move (capture the topic for the session heading + row).
    queue_body = _get_section_body(text, "queue")
    new_queue_body, topic = pop_queue_row(queue_body, queue_id)
    text = _set_section_body(text, "queue", new_queue_body)
    topic_str = topic or "{{topic}}"
    changes.append(f"queue: removed row {queue_id} ({topic_str})")

    tracker_row = f"| {queue_id} | {topic_str} | {{{{Decision / finding}}}} | v{new_version} |"
    tracker_body = _get_section_body(text, "tracker")
    text = _set_section_body(text, "tracker", append_tracker_row(tracker_body, tracker_row))
    changes.append(f"tracker: appended row {queue_id} (v{new_version})")

    # 2. Session Notes skeleton.
    sessions_body = _get_section_body(text, "sessions")
    session_block = _session_skeleton(queue_id, topic, date)
    text = _set_section_body(text, "sessions", _append_before_end(sessions_body, session_block))
    changes.append(f"sessions: inserted skeleton for {queue_id}")

    # 3. Changelog entry (newest first).
    changelog_body = _get_section_body(text, "changelog")
    changelog_block = _changelog_entry(queue_id, new_version, date)
    text = _set_section_body(
        text, "changelog", _prepend_subsection(changelog_body, changelog_block)
    )
    changes.append(f"changelog: prepended v{new_version} entry")

    # 4. References subsection (newest first).
    references_body = _get_section_body(text, "references")
    references_block = _references_entry(new_version, date)
    text = _set_section_body(
        text, "references", _prepend_subsection(references_body, references_block)
    )
    changes.append(f"references: prepended v{new_version} subsection")

    # 5. Frontmatter version + date.
    text = _set_frontmatter_scalar(text, "version", new_version)
    text = _set_frontmatter_scalar(text, "date", date)
    changes.append(f"frontmatter: version → {new_version}, date → {date}")

    return text, topic_str, changes
