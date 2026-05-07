"""Mechanical validation for Research Buddy v2 Markdown research documents.

Implements the Self-validation spec from the v2 starter. Returns a list of
Issue objects; empty list = pass.

Checks performed on a single file:
  1. YAML frontmatter parses; required fields present (and non-null in
     project mode).
  2. Anchor pairing: every <!-- @anchor: X --> has matching <!-- @end: X -->.
  3. Entry-block link targets: every <!-- @rule: R-XXX-N --> has a matching
     <a id="r-xxx-n"></a>; same for @da and @session.
  4. Cross-link resolution: every [text](#anchor) resolves to a real heading
     slug or <a id> tag.
  5. Filename / version / changelog consistency.
  6. ID uniqueness in the queue and tracker tables.

Diff-based checks (require --prior):
  7. Anchor preservation: no anchors removed since prior version.
  8. Append-only invariant: Discarded Alternatives, References, and Changelog
     never lose entries.

Plain-text-reference scanning is intentionally not in this version — it is
hard to do without false positives on illustrative examples in the framework
prose. The agent handles it semantically.

Usage:
    python -m research_buddy.validator_md FILE [--prior PRIOR] [--json]

Exit codes:
    0 — all mechanical checks passed (warnings allowed)
    1 — one or more errors
    2 — file not found / unreadable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Issue type and helpers
# ---------------------------------------------------------------------------

REQUIRED_FRONTMATTER_FIELDS: list[str | tuple[str, ...]] = [
    "doc_format_version",
    "research_buddy_version",
    "version",
    "date",
    "file_name",
    "title",
    ("language", "code"),
    ("project", "domain"),
]

# Fields that may legitimately be null in "starter mode" (project.domain is null).
STARTER_NULLABLE: set[str] = {
    "version",
    "date",
    "file_name",
    "title",
    ("project", "domain"),  # type: ignore[arg-type]
}


@dataclass
class Issue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    line: int = 0  # 1-indexed; 0 = no line context

    def format(self, filename: str = "") -> str:
        loc = (
            f"{filename}:{self.line}"
            if self.line and filename
            else (f"line {self.line}" if self.line else "")
        )
        prefix = f"[{self.severity.upper()}] {self.code}"
        if loc:
            return f"  {loc:>20}  {prefix}: {self.message}"
        return f"  {'':>20}  {prefix}: {self.message}"


# ---------------------------------------------------------------------------
# Fence-aware line scanning
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def _line_in_fence(lines: list[str]) -> list[bool]:
    """Return a list of bool: True if line is inside a fenced code block.

    Tracks fence markers by the opening character + length so nested fences
    (e.g. a ``` block inside a ```` block) are handled correctly.
    """
    in_fence: list[bool] = []
    current: str | None = None  # the opening fence string, or None
    for line in lines:
        stripped = line.lstrip()
        if current is None:
            m = _FENCE_RE.match(stripped)
            if m:
                current = m.group(1)
                in_fence.append(True)
            else:
                in_fence.append(False)
        else:
            # Look for matching closer: same character class, same or longer length
            m = re.match(rf"^({re.escape(current[0])}){{{len(current)},}}\s*$", stripped)
            if m and stripped.startswith(current):
                in_fence.append(True)
                current = None
            else:
                in_fence.append(True)
    return in_fence


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, int]:
    """Parse YAML frontmatter delimited by --- on first and second lines.

    Returns (parsed_dict_or_None, end_line_index). end_line_index is the
    1-indexed line number of the closing --- (or 0 if no frontmatter).
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None, 0
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            block = "\n".join(lines[1:i])
            try:
                parsed = yaml.safe_load(block)
                if isinstance(parsed, dict):
                    return parsed, i + 1
                return None, i + 1
            except yaml.YAMLError:
                return None, i + 1
    return None, 0


def _get_nested(d: dict[str, Any], path: str | tuple[str, ...]) -> Any:
    if isinstance(path, str):
        path = (path,)
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return _MISSING
        cur = cur[key]
    return cur


_MISSING = object()


def _is_starter(fm: dict[str, Any]) -> bool:
    """A file is in 'starter mode' if project.domain is null."""
    return _get_nested(fm, ("project", "domain")) is None


def _path_to_str(p: str | tuple[str, ...]) -> str:
    return p if isinstance(p, str) else ".".join(p)


def _check_frontmatter(text: str, path: Path) -> list[Issue]:
    issues: list[Issue] = []
    fm, end_line = _parse_frontmatter(text)
    if fm is None:
        issues.append(
            Issue(
                "error",
                "frontmatter-parse",
                "YAML frontmatter at top of file is missing or unparseable",
                1,
            )
        )
        return issues

    fmt_ver = fm.get("doc_format_version")
    legacy_ver = fm.get("format_version")
    if fmt_ver is None and legacy_ver is not None:
        issues.append(
            Issue(
                "warning",
                "deprecated-format-version-key",
                "frontmatter uses the deprecated key 'format_version'; "
                "rename to 'doc_format_version' (same value).",
                end_line,
            )
        )
        fmt_ver = legacy_ver
        fm["doc_format_version"] = legacy_ver  # satisfy required-fields check
    if fmt_ver != 2:
        issues.append(
            Issue(
                "error",
                "wrong-format-version",
                f"doc_format_version is {fmt_ver!r}, expected 2 "
                "(this validator handles v2 Markdown only)",
                end_line,
            )
        )
        # Don't continue with v2-specific checks if it's not v2
        return issues

    starter_mode = _is_starter(fm)
    for field_path in REQUIRED_FRONTMATTER_FIELDS:
        val = _get_nested(fm, field_path)
        path_str = _path_to_str(field_path)
        if val is _MISSING:
            issues.append(
                Issue(
                    "error",
                    "frontmatter-missing-field",
                    f"required frontmatter field '{path_str}' is missing",
                    end_line,
                )
            )
            continue
        if val is None and not starter_mode:
            issues.append(
                Issue(
                    "error",
                    "frontmatter-null-in-project",
                    f"frontmatter field '{path_str}' is null but project.domain is set "
                    f"(file is no longer a starter — fill this field)",
                    end_line,
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Anchor pairing
# ---------------------------------------------------------------------------

_ANCHOR_RE = re.compile(r"^\s*<!-- @anchor:\s*(\S+)\s*-->\s*$")
_END_RE = re.compile(r"^\s*<!-- @end:\s*(\S+)\s*-->\s*$")


def _check_anchor_pairing(lines: list[str]) -> list[Issue]:
    in_fence = _line_in_fence(lines)
    anchors: dict[str, int] = {}
    ends: dict[str, int] = {}
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        m = _ANCHOR_RE.match(line)
        if m:
            name = m.group(1)
            if name in anchors:
                # Duplicate anchor declaration
                pass  # Not strictly an error — covered by other checks if relevant
            anchors[name] = i + 1
            continue
        m = _END_RE.match(line)
        if m:
            ends[m.group(1)] = i + 1

    issues: list[Issue] = []
    for name, ln in sorted(anchors.items()):
        if name not in ends:
            issues.append(
                Issue("error", "anchor-no-end", f"@anchor: {name} has no matching @end", ln)
            )
    for name, ln in sorted(ends.items()):
        if name not in anchors:
            issues.append(
                Issue("error", "end-no-anchor", f"@end: {name} has no matching @anchor", ln)
            )
    return issues


# ---------------------------------------------------------------------------
# Entry-block link targets (rule / da / session)
# ---------------------------------------------------------------------------

_ENTRY_RE = re.compile(r"^\s*<!-- @(rule|da|session):\s*(\S+)\s*-->\s*$")
_A_ID_RE = re.compile(r'<a\s+id="([^"]+)"\s*>\s*</a>')


def _check_entry_link_targets(lines: list[str]) -> list[Issue]:
    in_fence = _line_in_fence(lines)
    issues: list[Issue] = []
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        m = _ENTRY_RE.match(line)
        if not m:
            continue
        kind, eid = m.group(1), m.group(2)
        expected = eid.lower()
        # Look ahead up to 3 non-empty lines for matching <a id>
        seen_id: str | None = None
        seen_line: int = 0
        for j in range(i + 1, min(i + 4, len(lines))):
            if in_fence[j]:
                continue
            am = _A_ID_RE.search(lines[j])
            if am:
                seen_id = am.group(1)
                seen_line = j + 1
                break
        if seen_id is None:
            issues.append(
                Issue(
                    "error",
                    "entry-no-link-target",
                    f'@{kind}: {eid} has no <a id="{expected}"></a> within 3 lines',
                    i + 1,
                )
            )
        elif seen_id != expected:
            issues.append(
                Issue(
                    "error",
                    "entry-id-mismatch",
                    f'@{kind}: {eid} expects <a id="{expected}"> but found <a id="{seen_id}">',
                    seen_line,
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Cross-link resolution
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _slugify(text: str) -> str:
    """GitHub-flavored Markdown slug (approximate)."""
    s = text.strip().lower()
    # Drop punctuation that's stripped by GFM
    s = re.sub(r"[^\w\s-]", "", s)
    # Collapse whitespace runs to single dash
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def _collect_link_targets(lines: list[str]) -> set[str]:
    in_fence = _line_in_fence(lines)
    targets: set[str] = set()
    seen_slugs: dict[str, int] = {}
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        m = _HEADING_RE.match(line)
        if m:
            slug = _slugify(m.group(2))
            # GFM disambiguates duplicates with -1, -2, ...
            count = seen_slugs.get(slug, 0)
            if count == 0:
                targets.add(slug)
            else:
                targets.add(f"{slug}-{count}")
            seen_slugs[slug] = count + 1
        for am in _A_ID_RE.finditer(line):
            targets.add(am.group(1))
    return targets


def _check_cross_links(text: str, lines: list[str]) -> list[Issue]:
    in_fence = _line_in_fence(lines)
    targets = _collect_link_targets(lines)
    issues: list[Issue] = []

    fm, _ = _parse_frontmatter(text)
    starter_mode = bool(fm and _is_starter(fm))

    # Targets used illustratively in framework prose (e.g. #r-chunk-4 in examples).
    # In starter mode these are expected to be unresolved; downgrade to info.
    illustrative_patterns = re.compile(r"^(r-chunk-\d+|r-xxx-\w+|da-q\d+-\d+|da-xxx|q-\d{3})$")

    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        # Strip inline code spans so backtick-wrapped link syntax is ignored
        clean = _INLINE_CODE_RE.sub("", line)
        for m in _LINK_RE.finditer(clean):
            label, target = m.group(1), m.group(2)
            if target in targets:
                continue
            severity = "warning"
            if starter_mode and illustrative_patterns.match(target):
                severity = "info"
            issues.append(
                Issue(
                    severity,
                    "broken-cross-link",
                    f"[{label}](#{target}) does not resolve to any heading slug or <a id>",
                    i + 1,
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Filename / version / changelog consistency
# ---------------------------------------------------------------------------


def _check_filename_version(path: Path, text: str) -> list[Issue]:
    issues: list[Issue] = []
    fm, _ = _parse_frontmatter(text)
    if fm is None:
        return issues
    if _is_starter(fm):
        # Starter file: skip filename and changelog version checks
        return issues

    version = fm.get("version")
    file_name = fm.get("file_name")

    # Detect whether this is a source file (has framework block) or a clean view
    has_framework = "<!-- @anchor: framework.core -->" in text

    # Filename check
    if version and file_name:
        if has_framework:
            expected = f"{file_name}_v{version}-source.md"
        else:
            expected = f"{file_name}_v{version}.md"
        if path.name != expected:
            issues.append(
                Issue(
                    "error",
                    "filename-mismatch",
                    f"filename {path.name!r} does not match expected {expected!r}",
                    0,
                )
            )

    # Changelog top-entry version check
    cl_anchor = re.search(r"^<!-- @anchor: changelog -->\s*$", text, re.MULTILINE)
    if cl_anchor:
        rest = text[cl_anchor.end() :]
        h3_m = re.search(r"^### (.+?)\s*$", rest, re.MULTILINE)
        if h3_m and version:
            heading = h3_m.group(1)
            if f"v{version}" not in heading:
                issues.append(
                    Issue(
                        "error",
                        "changelog-version-mismatch",
                        f"first changelog entry '{heading}' does not contain v{version}",
                        0,
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# ID uniqueness in queue / tracker tables
# ---------------------------------------------------------------------------


def _extract_section(text: str, anchor_id: str) -> str | None:
    """Return the text between <!-- @anchor: anchor_id --> and <!-- @end: anchor_id -->."""
    escaped = re.escape(anchor_id)
    pattern = re.compile(
        rf"<!-- @anchor:\s*{escaped}\s*-->(.*?)<!-- @end:\s*{escaped}\s*-->",
        re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def _extract_table_first_column(section: str) -> list[str]:
    """Extract first-column values from any markdown tables in the section."""
    out: list[str] = []
    in_table = False
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            continue
        # Detect header separator row (|---|---|...)
        if re.match(r"^\|\s*[-:]+", s):
            in_table = True
            continue
        if in_table:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells:
                out.append(cells[0])
    return out


def _check_id_uniqueness(text: str, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []

    queue_text = _extract_section(text, "queue")
    tracker_text = _extract_section(text, "tracker")

    queue_ids: list[str] = []
    if queue_text:
        for cell in _extract_table_first_column(queue_text):
            if re.match(r"^Q-\d+$", cell):
                queue_ids.append(cell)

    tracker_ids: list[str] = []
    if tracker_text:
        for cell in _extract_table_first_column(tracker_text):
            if re.match(r"^[QT]-\w+$", cell):
                tracker_ids.append(cell)

    # Duplicates within queue
    seen: set[str] = set()
    for qid in queue_ids:
        if qid in seen:
            issues.append(
                Issue("error", "duplicate-queue-id", f"queue ID {qid} appears more than once")
            )
        seen.add(qid)

    # Duplicates within tracker
    seen = set()
    for tid in tracker_ids:
        if tid in seen:
            issues.append(
                Issue("error", "duplicate-tracker-id", f"tracker ID {tid} appears more than once")
            )
        seen.add(tid)

    # Q-NNN appearing in both queue and tracker
    queue_q_set = set(qid for qid in queue_ids if qid.startswith("Q-"))
    tracker_q_set = set(tid for tid in tracker_ids if tid.startswith("Q-"))
    overlap = queue_q_set & tracker_q_set
    for qid in sorted(overlap):
        issues.append(
            Issue(
                "error",
                "id-in-queue-and-tracker",
                f"{qid} appears in both the queue and the tracker — "
                "done items must leave the queue",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Diff-based checks (require --prior)
# ---------------------------------------------------------------------------


def _collect_anchors(text: str) -> set[str]:
    """Collect every @anchor / @rule / @da / @session ID present in the text
    (outside fenced code blocks)."""
    lines = text.splitlines()
    in_fence = _line_in_fence(lines)
    out: set[str] = set()
    patterns = [
        re.compile(r"^\s*<!-- @anchor:\s*(\S+)\s*-->\s*$"),
        re.compile(r"^\s*<!-- @rule:\s*(\S+)\s*-->\s*$"),
        re.compile(r"^\s*<!-- @da:\s*(\S+)\s*-->\s*$"),
        re.compile(r"^\s*<!-- @session:\s*(\S+)\s*-->\s*$"),
    ]
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        for pat in patterns:
            m = pat.match(line)
            if m:
                out.add(m.group(1))
    return out


def _check_anchor_preservation(prior_text: str, new_text: str, new_lines: list[str]) -> list[Issue]:
    prior = _collect_anchors(prior_text)
    new = _collect_anchors(new_text)
    removed = prior - new
    issues: list[Issue] = []
    for name in sorted(removed):
        issues.append(
            Issue(
                "error",
                "anchor-removed",
                f"anchor {name!r} present in prior version is missing from new version "
                f"(anchors must never be renamed or deleted)",
            )
        )
    return issues


def _collect_entry_ids(text: str, kind: str) -> set[str]:
    """Collect all entry IDs of a given kind (rule | da | session)."""
    pattern = re.compile(rf"^\s*<!-- @{kind}:\s*(\S+)\s*-->\s*$", re.MULTILINE)
    return set(pattern.findall(text))


def _check_append_only(prior_text: str, new_text: str) -> list[Issue]:
    issues: list[Issue] = []
    # Discarded Alternatives: @da entries
    prior_das = _collect_entry_ids(prior_text, "da")
    new_das = _collect_entry_ids(new_text, "da")
    for name in sorted(prior_das - new_das):
        issues.append(
            Issue(
                "error",
                "da-removed",
                f"DA {name!r} from prior version is missing — "
                "Discarded Alternatives are append-only",
            )
        )

    # Reasoning Journey, References, Changelog don't use @ ID anchors per entry; we approximate
    # by counting H3 headings under each section.
    for section_id, section_label in (
        ("references", "References"),
        ("changelog", "Changelog"),
    ):
        prior_section = _extract_section(prior_text, section_id) or ""
        new_section = _extract_section(new_text, section_id) or ""
        prior_h3s = re.findall(r"^### (.+?)$", prior_section, re.MULTILINE)
        new_h3s = re.findall(r"^### (.+?)$", new_section, re.MULTILINE)
        # Every prior H3 should still be present (verbatim) in new.
        new_h3_set = set(new_h3s)
        for heading in prior_h3s:
            if heading not in new_h3_set:
                issues.append(
                    Issue(
                        "error",
                        f"{section_id}-entry-removed",
                        f"{section_label} entry '{heading}' from prior version is missing "
                        "— append-only",
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Brief-context-slot vs. live-section preflight check
# ---------------------------------------------------------------------------


# Maps the brief context-slot heading (case-insensitive prefix match) to the
# anchor ID of the source section whose entries it summarizes.
_BRIEF_SLOT_TO_ANCHOR: list[tuple[str, str, str]] = [
    ("Already-rejected approaches", "discarded", "@da"),
    ("Related prior research already settled", "tracker", "tracker-rows"),
    ("Active rules that constrain new conclusions", "rules", "@rule"),
]


def _section_has_entries(text: str, anchor: str, marker: str) -> bool:
    """True if the named section contains at least one live entry."""
    section = _extract_section(text, anchor)
    if section is None:
        return False
    if marker == "tracker-rows":
        # Count tracker rows that are not the seed T-000 placeholder.
        ids = _extract_table_first_column(section)
        return any(re.match(r"^[QT]-\w+$", i) and i != "T-000" for i in ids)
    # @rule / @da entries: just count the comment markers
    return bool(re.search(rf"^\s*<!-- {re.escape(marker)}:\s*\S+\s*-->\s*$", section, re.MULTILINE))


def _check_brief_context_slots(text: str, lines: list[str]) -> list[Issue]:
    """If the document includes a Turn 1 brief, verify that any context slot
    filled with a literal "None." actually corresponds to an empty source
    section. Mismatch suggests the agent skipped preflight."""
    issues: list[Issue] = []
    m = re.search(r"<!--\s*@brief-start\s*-->(.*?)<!--\s*@brief-end\s*-->", text, re.DOTALL)
    if not m:
        return issues
    brief = m.group(1)
    brief_start_line = text[: m.start()].count("\n") + 1

    for slot_heading, anchor, marker in _BRIEF_SLOT_TO_ANCHOR:
        # Find the heading line and the value line(s) immediately after.
        # The brief template uses a single-line value; "None." on its own
        # line is the trigger.
        heading_re = re.compile(
            rf"^{re.escape(slot_heading)}.*?$\s*(.*?)(?:^\s*$|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        slot_match = heading_re.search(brief)
        if not slot_match:
            continue
        value = slot_match.group(1).strip()
        # "None." or a placeholder still reading "{{...}}" both count as empty
        if value not in {"None.", "None", ""} and not value.startswith("{{"):
            continue
        if value.startswith("{{"):
            # Unfilled placeholder is a different kind of failure; skip here
            continue
        if _section_has_entries(text, anchor, marker):
            issues.append(
                Issue(
                    "warning",
                    "brief-slot-empty-but-section-non-empty",
                    f"second-opinion brief context slot '{slot_heading}' is "
                    f"empty ('{value}') but [{anchor}] contains live entries — "
                    "preflight may have been skipped (or the agent decided "
                    "none of the live entries are relevant; if so, replace "
                    "the empty value with 'None relevant.' plus a one-line "
                    "reason)",
                    brief_start_line,
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def validate_md(path: Path, prior: Path | None = None) -> list[Issue]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    issues: list[Issue] = []
    issues.extend(_check_frontmatter(text, path))
    # If frontmatter is unparseable or wrong doc_format_version, bail early —
    # the other checks assume v2 structure.
    if any(
        i.code in {"frontmatter-parse", "wrong-format-version"} and i.severity == "error"
        for i in issues
    ):
        return issues

    issues.extend(_check_anchor_pairing(lines))
    issues.extend(_check_entry_link_targets(lines))
    issues.extend(_check_cross_links(text, lines))
    issues.extend(_check_filename_version(path, text))
    issues.extend(_check_id_uniqueness(text, lines))
    issues.extend(_check_brief_context_slots(text, lines))

    if prior is not None:
        prior_text = prior.read_text(encoding="utf-8")
        issues.extend(_check_anchor_preservation(prior_text, text, lines))
        issues.extend(_check_append_only(prior_text, text))

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Research Buddy v2 Markdown research document."
    )
    parser.add_argument("file", type=Path, help="Path to the .md file to validate")
    parser.add_argument(
        "--prior",
        type=Path,
        default=None,
        help="Optional prior version of the same file (enables anchor-preservation "
        "and append-only checks)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a human-readable report",
    )
    args = parser.parse_args(argv)

    if not args.file.is_file():
        print(f"Error: {args.file} not found or not a file", file=sys.stderr)
        return 2
    if args.prior is not None and not args.prior.is_file():
        print(f"Error: --prior {args.prior} not found or not a file", file=sys.stderr)
        return 2

    issues = validate_md(args.file, args.prior)
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    infos = [i for i in issues if i.severity == "info"]

    if args.json:
        out = {
            "file": str(args.file),
            "prior": str(args.prior) if args.prior else None,
            "passed": len(errors) == 0,
            "counts": {
                "error": len(errors),
                "warning": len(warnings),
                "info": len(infos),
            },
            "issues": [
                {"severity": i.severity, "code": i.code, "message": i.message, "line": i.line}
                for i in issues
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        if not issues:
            print(f"\u2714  {args.file.name}: all mechanical checks passed.")
        else:
            print(
                f"\n  {args.file.name}: {len(errors)} error(s), "
                f"{len(warnings)} warning(s), {len(infos)} info\n"
            )
            for issue in issues:
                print(issue.format(args.file.name))
            print()
            if errors:
                print(f"\u2718  {len(errors)} error(s).")
            else:
                print("\u2714  no errors (warnings/info only).")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
