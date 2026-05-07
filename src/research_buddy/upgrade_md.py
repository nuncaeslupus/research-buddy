"""Refresh a v2 Markdown source file's framework block from the installed starter.

The framework block is everything between (inclusive) the lines:
    <!-- @anchor: framework.core -->
    <!-- @end: framework.reference -->

That block is template-owned and replaced wholesale on upgrade. Project-owned
content (frontmatter values the user filled in, title body, project
specification, queue, tracker, rules, DAs, sessions, journey, references,
changelog) is preserved exactly.

Frontmatter is migrated structurally:

- Legacy key `format_version` is renamed to `doc_format_version` (same value).
- `research_buddy_version` is updated to the installed tool version.
- Missing `project.source_tiers` (with `tier_1`, `tier_2`, `discovery` subkeys)
  is inserted with null values so `validator_md` does not complain about
  unresolved `{{project.source_tiers.tier_1}}` placeholders introduced by
  newer framework blocks.
- Missing `project.domain_rules` is inserted with a null value for the same
  reason.

Edits are line-based to preserve YAML comments and value formatting wherever
possible. Two helper passes handle the awkward cases:

- Renaming the format-version key swaps `format_version` → `doc_format_version`
  on the same line, leaving everything after the colon untouched.
- Inserting missing `project.*` subkeys finds the existing `project:` block
  by scanning indentation, then appends the new key at the end of the block
  using a 2-space indent (matching the starter's style).

The CLI handler in `main.py` owns I/O, dry-run/--apply gating, atomic write,
and post-upgrade validation. This module is pure.
"""

from __future__ import annotations

from typing import Any

import yaml

FRAMEWORK_START = "<!-- @anchor: framework.core -->"
FRAMEWORK_END = "<!-- @end: framework.reference -->"


class UpgradeError(Exception):
    """Raised when the source file is structurally unfit for upgrade."""


def upgrade_md(source: str, starter: str, tool_version: str) -> tuple[str, list[str]]:
    """Upgrade a v2 source file against the installed starter.md.

    Returns (upgraded_text, change_descriptions). The change list is empty
    when the source is already in sync; in that case `upgraded_text` equals
    `source` modulo a trailing-newline normalization the caller can ignore.

    Raises UpgradeError when:
    - source has no framework block (missing either marker);
    - source frontmatter is missing or unparseable;
    - source `doc_format_version` (or legacy `format_version`) is not 2.
    """
    changes: list[str] = []

    # 1. Frontmatter migration first — done on the unmodified source so we can
    #    reason about indentation and existing keys without the framework
    #    swap interfering.
    source, fm_changes = _migrate_frontmatter(source, tool_version)
    changes.extend(fm_changes)

    # 2. Framework block replacement.
    source, body_changes = _replace_framework_block(source, starter)
    changes.extend(body_changes)

    return source, changes


# ---------------------------------------------------------------------------
# Framework block
# ---------------------------------------------------------------------------


def _replace_framework_block(source: str, starter: str) -> tuple[str, list[str]]:
    """Swap the source's framework block with the starter's framework block.

    Boundaries are matched by full-line equality with the marker (after
    strip()), the same convention `clean_md.collect_framework_targets` uses,
    so prose mentions of the markers inside fenced code blocks are ignored.
    """
    src_start, src_end = _find_framework_bounds(source, "source")
    star_start, star_end = _find_framework_bounds(starter, "starter")

    src_lines = source.splitlines()
    star_lines = starter.splitlines()
    src_block = src_lines[src_start : src_end + 1]
    star_block = star_lines[star_start : star_end + 1]

    if src_block == star_block:
        return source, []

    new_lines = src_lines[:src_start] + star_block + src_lines[src_end + 1 :]
    out = "\n".join(new_lines)
    if source.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out, ["framework block ← starter.md"]


def _find_framework_bounds(text: str, label: str) -> tuple[int, int]:
    """Return (start_index, end_index) of the framework block, both inclusive,
    counted as 0-based line indexes. Raises UpgradeError if either marker
    is missing or the closing precedes the opening.

    `label` is "source" or "starter" — included in error messages so the user
    can tell which file is malformed.
    """
    lines = text.splitlines()
    start = end = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == FRAMEWORK_START and start < 0:
            start = i
        elif stripped == FRAMEWORK_END:
            end = i  # last match wins, mirroring clean_md
    if start < 0:
        raise UpgradeError(f"{label}: missing '{FRAMEWORK_START}' marker")
    if end < 0:
        raise UpgradeError(f"{label}: missing '{FRAMEWORK_END}' marker")
    if end <= start:
        raise UpgradeError(f"{label}: '{FRAMEWORK_END}' precedes '{FRAMEWORK_START}'")
    return start, end


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def _migrate_frontmatter(source: str, tool_version: str) -> tuple[str, list[str]]:
    """Apply structural frontmatter migrations.

    Returns (new_text, changes). Operates line-based on the frontmatter
    region (between the leading `---` and its closing `---`), leaving the
    body untouched.
    """
    fm_start, fm_end = _find_frontmatter_bounds(source)
    fm_text = "\n".join(source.splitlines()[fm_start + 1 : fm_end])

    try:
        fm_dict = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise UpgradeError(f"frontmatter: YAML parse error: {exc}") from exc
    if not isinstance(fm_dict, dict):
        raise UpgradeError("frontmatter: expected a YAML mapping")

    fmt_ver = fm_dict.get("doc_format_version", fm_dict.get("format_version"))
    if fmt_ver != 2:
        raise UpgradeError(
            f"frontmatter: doc_format_version is {fmt_ver!r}, expected 2 "
            "(this command only upgrades v2 Markdown files)"
        )

    fm_lines = source.splitlines()[fm_start + 1 : fm_end]
    changes: list[str] = []

    fm_lines, key_changes = _rename_format_version_key(fm_lines)
    changes.extend(key_changes)

    fm_lines, ver_changes = _bump_research_buddy_version(fm_lines, tool_version)
    changes.extend(ver_changes)

    fm_lines, st_changes = _ensure_project_source_tiers(fm_lines, fm_dict)
    changes.extend(st_changes)

    fm_lines, dr_changes = _ensure_project_domain_rules(fm_lines, fm_dict)
    changes.extend(dr_changes)

    if not changes:
        return source, []

    src_lines = source.splitlines()
    new_lines = src_lines[: fm_start + 1] + fm_lines + src_lines[fm_end:]
    out = "\n".join(new_lines)
    if source.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out, changes


def _find_frontmatter_bounds(source: str) -> tuple[int, int]:
    """Return (start_index, end_index) of the YAML frontmatter delimiters.

    Both indexes point at `---` lines; YAML content is between them. Raises
    UpgradeError when no frontmatter is present.
    """
    lines = source.splitlines()
    if not lines or lines[0].rstrip() != "---":
        raise UpgradeError("frontmatter: missing leading '---' delimiter")
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return 0, i
    raise UpgradeError("frontmatter: missing closing '---' delimiter")


def _rename_format_version_key(fm_lines: list[str]) -> tuple[list[str], list[str]]:
    """Rename `format_version:` to `doc_format_version:` on its line.

    Only the key is changed — the value, comments, and indentation are left
    untouched. No-op if the key is already `doc_format_version` or absent.
    """
    out = list(fm_lines)
    for i, line in enumerate(out):
        # Match a top-level `format_version:` (no leading whitespace) so we
        # never confuse it with a project-scoped sibling.
        if line.startswith("format_version:"):
            out[i] = "doc_format_version:" + line[len("format_version:") :]
            return out, ["format_version → doc_format_version"]
    return out, []


def _bump_research_buddy_version(
    fm_lines: list[str], tool_version: str
) -> tuple[list[str], list[str]]:
    """Update `research_buddy_version: "X.Y.Z"` to the installed tool version.

    Forward-only: if the existing version parses as semver and is *ahead* of
    the installed tool, raises UpgradeError. This is intentional — silently
    downgrading a deliberately-stamped future version (the user using the
    field as "framework version this doc was authored against") would lose
    information. The user is asked to either upgrade the installed tool or
    manually edit the doc before re-running.

    Quoting is preserved: if the existing value is double-quoted it stays
    double-quoted; bare values stay bare. Inline comments after the value
    are preserved.
    """
    from research_buddy.validator import _parse_semver

    out = list(fm_lines)
    for i, line in enumerate(out):
        if not line.startswith("research_buddy_version:"):
            continue
        old_value = _extract_scalar_value(line)
        if old_value == tool_version:
            return out, []

        old_semver = _parse_semver(old_value)
        new_semver = _parse_semver(tool_version)
        if old_semver and new_semver and old_semver > new_semver:
            raise UpgradeError(
                f"frontmatter: research_buddy_version is {old_value!r} but the "
                f"installed tool is {tool_version!r} — the document is AHEAD of "
                f"the tool. Refusing to downgrade. Either upgrade the installed "
                f"tool (`pip install --upgrade research-buddy`) or manually edit "
                f"the doc's research_buddy_version to {tool_version!r} before "
                f"re-running."
            )

        out[i] = _replace_scalar_value(line, old_value, tool_version)
        return out, [f"research_buddy_version: {old_value!r} → {tool_version!r}"]
    return out, []


def _extract_scalar_value(line: str) -> str:
    """Strip key, leading whitespace, surrounding quotes, and trailing comment
    from `key: value  # comment` and return just the bare value."""
    after_colon = line.split(":", 1)[1]
    # Drop trailing comment first (only if the # is preceded by whitespace —
    # `#` inside a quoted value is rare but legal).
    if " #" in after_colon:
        after_colon = after_colon.split(" #", 1)[0]
    val = after_colon.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]
    return val


def _replace_scalar_value(line: str, old_value: str, new_value: str) -> str:
    """Replace `old_value` with `new_value` on a `key: value` line.

    Preserves the key, the colon, leading whitespace before the value, the
    quoting style (or lack thereof), and any trailing inline comment.
    """
    key_part, after_colon = line.split(":", 1)
    comment = ""
    val_part = after_colon
    if " #" in val_part:
        val_part, comment_body = val_part.split(" #", 1)
        comment = " #" + comment_body
    leading_ws = val_part[: len(val_part) - len(val_part.lstrip())]
    raw = val_part.strip()
    quote = ""
    if raw.startswith('"') and raw.endswith('"'):
        quote = '"'
    elif raw.startswith("'") and raw.endswith("'"):
        quote = "'"
    return f"{key_part}:{leading_ws}{quote}{new_value}{quote}{comment}"


def _ensure_project_source_tiers(
    fm_lines: list[str], fm_dict: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Insert `project.source_tiers` block if absent in the parsed frontmatter."""
    project = fm_dict.get("project")
    if not isinstance(project, dict):
        return fm_lines, []
    if "source_tiers" in project:
        return fm_lines, []

    insertion = [
        "  source_tiers:",
        "    tier_1: null",
        "    tier_2: null",
        "    discovery: null",
    ]
    new_lines = _insert_in_project_block(fm_lines, insertion)
    return new_lines, ["frontmatter: project.source_tiers added (null values)"]


def _ensure_project_domain_rules(
    fm_lines: list[str], fm_dict: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Insert `project.domain_rules: null` if absent."""
    project = fm_dict.get("project")
    if not isinstance(project, dict):
        return fm_lines, []
    if "domain_rules" in project:
        return fm_lines, []

    new_lines = _insert_in_project_block(fm_lines, ["  domain_rules: null"])
    return new_lines, ["frontmatter: project.domain_rules added (null)"]


def _insert_in_project_block(fm_lines: list[str], insertion: list[str]) -> list[str]:
    """Append `insertion` lines at the end of the `project:` block.

    The block is identified by the line `project:` at column 0 followed by
    children indented by ≥1 space. Insertion happens just before the first
    line whose indentation drops back to column 0 (or at end-of-frontmatter).
    """
    project_idx = -1
    for i, line in enumerate(fm_lines):
        if line.startswith("project:") or line.rstrip() == "project:":
            project_idx = i
            break
    if project_idx < 0:
        # No project: block — append at end. Should not happen for v2.
        return [*fm_lines, "project:", *insertion]

    end_idx = len(fm_lines)
    for j in range(project_idx + 1, len(fm_lines)):
        line = fm_lines[j]
        if line.strip() == "":
            continue
        if not line.startswith(" ") and not line.startswith("\t"):
            end_idx = j
            break

    return fm_lines[:end_idx] + insertion + fm_lines[end_idx:]
