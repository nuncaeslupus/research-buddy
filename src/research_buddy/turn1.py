"""v2 `turn1` — print the second-opinion brief skeleton, pre-filled from frontmatter.

Turn 1 of a standard research session opens with a second-opinion brief written
into the response BEFORE any research tool is called (the "brief gate"). The
brief is filled entirely from project-given context — never from this turn's
findings. Composing it from scratch is the step agents under tool-pressure skip;
this command turns "remember to write it" into "run this, then fill the few
remaining placeholders".

Pre-filled from the frontmatter + the top Open Research Queue row:
- the project description (domain, deliverable, final goal),
- the active topic + its objective (first live queue row),
- accepted source tiers + the framework's fixed "Never" reject rule.

Left as `{{placeholders}}` for the agent (they need preflight judgement, or are
this-turn inputs): the relevant rejected alternatives / prior tracker rows /
active rules, the pre-registered hypothesis names, and the excellence bar.

The body mirrors the canonical [Second-opinion brief template] in starter.md so
`turn1` output and the in-file template stay shape-identical; output is wrapped
in real `<!-- @brief-start -->` / `<!-- @brief-end -->` markers so it pastes
straight into the Turn 1 response. Pure module — the CLI handler in
`commands/turn1.py` owns I/O.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from research_buddy.bump import (
    BumpError,
    _comment_mask,
    _get_section_body,
    _is_separator_row,
    _row_cells,
)


class Turn1Error(Exception):
    """Raised when the brief skeleton cannot be produced."""


BRIEF_START = "<!-- @brief-start -->"
BRIEF_END = "<!-- @brief-end -->"

# The framework's fixed "Never" tier (see Source tiers in starter.md). Stated
# verbatim so the auto-rejected line is filled without the agent looking it up.
_NEVER_TIER = (
    "anonymous content, AI-generated overviews without human authorship, "
    "unverifiable PDFs, and sources without traceable authorship"
)

_QID_RE = re.compile(r"(?i)^[QT]-\d+$")


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce a frontmatter section to a mapping. Malformed YAML may parse a
    field as a string/list; returning {} for non-dicts keeps `.get()` from
    raising AttributeError (we surface a clean Turn1Error instead)."""
    return value if isinstance(value, dict) else {}


def _parse_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise Turn1Error("missing YAML frontmatter")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            try:
                fm = yaml.safe_load("\n".join(lines[1:i]))
            except yaml.YAMLError as e:
                raise Turn1Error(f"frontmatter YAML parse error: {e}") from e
            if not isinstance(fm, dict):
                raise Turn1Error("frontmatter is not a YAML mapping")
            return fm
    raise Turn1Error("frontmatter missing closing '---' delimiter")


def first_queue_row(text: str) -> tuple[str, str, str] | None:
    """Return (id, topic, objective) for the first live Open Research Queue row,
    or None when the queue has no live rows.

    Comment/example rows (the `<!-- ... -->` examples), the separator, and the
    header are skipped, reusing bump's comment-aware row helpers so behaviour
    matches `bump`'s own queue handling.
    """
    try:
        body = _get_section_body(text, "queue")
    except BumpError:
        return None
    lines = body.split("\n")
    mask = _comment_mask(lines)
    for i, line in enumerate(lines):
        if mask[i] or not line.strip().startswith("|") or _is_separator_row(line):
            continue
        cells = _row_cells(line)
        if not cells or not _QID_RE.match(cells[0]):
            # header row ("ID | Topic | …") or a malformed row — skip.
            continue
        qid = cells[0]
        topic = cells[1] if len(cells) > 1 else ""
        objective = cells[2] if len(cells) > 2 else ""
        return qid, topic, objective
    return None


def _project_description(fm: dict[str, Any]) -> str:
    project = _as_dict(fm.get("project"))
    domain = project.get("domain")
    deliverable = project.get("deliverable_type")
    goal = project.get("final_goal")
    if not domain:
        return "{{PROJECT_AND_BASIC_CHARACTERISTICS}}"
    desc = str(domain)
    extras = []
    if deliverable:
        extras.append(f"deliverable: {deliverable}")
    if goal:
        extras.append(f"goal: {goal}")
    if extras:
        desc += f" ({'; '.join(extras)})"
    return desc


def _accepted_sources(fm: dict[str, Any]) -> str:
    tiers = _as_dict(_as_dict(fm.get("project")).get("source_tiers"))
    t1 = tiers.get("tier_1")
    t2 = tiers.get("tier_2")
    parts = []
    if t1:
        parts.append(f"Tier 1 (primary, supports VALIDATED): {t1}")
    if t2:
        parts.append(f"Tier 2 (official secondary): {t2}")
    return ". ".join(parts) if parts else "{{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}"


def build_brief_skeleton(text: str) -> tuple[str, list[str]]:
    """Return (brief_block, guidance_notes).

    `brief_block` is the full brief wrapped in `@brief-start` / `@brief-end`
    markers, ready to paste into the Turn 1 response. `guidance_notes` are
    human-facing reminders about what still needs filling (printed to stderr by
    the CLI so they never pollute the copy-paste block).

    Raises Turn1Error on a starter file (no project to brief on) or unparseable
    frontmatter.
    """
    fm = _parse_frontmatter(text)
    if _as_dict(fm.get("project")).get("domain") is None:
        raise Turn1Error(
            "this is a starter file (project.domain is null) — run session zero "
            "first; there is no queue topic to brief on yet"
        )

    if fm.get("agent_state") == "complete":
        raise Turn1Error(
            "project is marked complete (agent_state: complete) — no research sessions "
            "are expected. To continue, add a queue item and set agent_state: ready"
        )

    notes: list[str] = []
    row = first_queue_row(text)
    if row is None:
        topic = "{{RESEARCH_TOPIC_IN_CONTEXT}}"
        questions = "{{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}"
        notes.append(
            "note: the Open Research Queue has no live row — fill the topic and "
            "questions manually, or add a queue item before researching."
        )
    else:
        qid, topic_cell, objective = row
        topic = topic_cell or "{{RESEARCH_TOPIC_IN_CONTEXT}}"
        questions = objective or "{{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}"
        notes.append(f"pre-filled from the top queue row {qid} ({topic}).")

    project = _project_description(fm)
    sources = _accepted_sources(fm)

    # Built as a list of lines (long prose split via implicit concatenation to
    # stay under the line-length limit) — same pattern as bump's skeletons. The
    # body mirrors the canonical [Second-opinion brief template] in starter.md.
    body = "\n".join(
        [
            BRIEF_START,
            f"I am working on a {project}. I'm trying to decide {topic}.",
            "",
            "I need you to do a deep research that allows you to answer these "
            f"questions: {questions}.",
            "",
            "Your research must be {{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}.",
            "",
            f"Accepted sources will be: {sources}.",
            f"Automatically rejected: {_NEVER_TIER}.",
            "",
            "Context that bounds the answer space — please respect these unless "
            "you have new Tier-1 evidence that overturns them:",
            "",
            "Already-rejected approaches (do not re-propose unless you bring new "
            "Tier-1 evidence; mark any revisit explicitly):",
            "{{RELEVANT_DISCARDED_ALTERNATIVES}}",
            "",
            "Related prior research already settled in this project (use as "
            "background; flag only if your findings contradict):",
            "{{RELATED_PRIOR_TRACKER_ROWS}}",
            "",
            "Active rules that constrain new conclusions (a recommendation that "
            "violates these needs to either narrow itself to fit or argue "
            "explicitly for revision):",
            "{{ACTIVE_CONSTRAINING_RULES}}",
            "",
            "Pre-registered hypotheses (the agent has these on record; you do "
            "not need to align with them — independent answers are the point):",
            "{{PRE_REGISTERED_HYPOTHESES_BY_NAME_ONLY}}",
            "",
            "Please cite all claims inline with Title, Author, Year, Venue, "
            "DOI/URL in the same sentence as the claim — not at the end and not "
            "via links to other parts of the answer. Distinguish what is "
            "validated vs. proposed/experimental.",
            BRIEF_END,
        ]
    )

    notes.append(
        "still to fill from preflight: {{RELEVANT_DISCARDED_ALTERNATIVES}}, "
        "{{RELATED_PRIOR_TRACKER_ROWS}}, {{ACTIVE_CONSTRAINING_RULES}} (write "
        '"None." if preflight surfaced nothing relevant), '
        "{{PRE_REGISTERED_HYPOTHESES_BY_NAME_ONLY}}, and the excellence bar."
    )
    return body, notes
