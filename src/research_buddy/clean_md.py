"""Generate a clean-view Markdown file from a v2 source file.

Reads {file_name}_v{version}-source.md (the agent-edited source file with the
full framework block) and writes {file_name}_v{version}.md (the shareable
research artifact with framework removed).

Two transformations:

1. **Strip the framework block.** Everything between
   <!-- @anchor: framework.core --> and <!-- @end: framework.reference -->
   is removed, along with the redundant horizontal rule and blank lines that
   followed it.
2. **Regenerate the title block.** The source title contains agent-only
   metadata (the source-of-truth paragraph, filename convention list, agent
   read-this directive). The clean view replaces it with just the H1 plus a
   one-line version/date stamp built from the YAML frontmatter.

Refuses to run on a starter file (frontmatter project.domain is null) — there
is nothing to clean yet.

Usage:
    python -m research_buddy.clean_md FILE [-o OUTPUT] [--print]

Exit codes:
    0 — clean view written
    2 — input file missing, malformed, or in starter mode
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FRAMEWORK_START = "<!-- @anchor: framework.core -->"
FRAMEWORK_END = "<!-- @end: framework.reference -->"
TITLE_START = "<!-- @anchor: title -->"
TITLE_END = "<!-- @end: title -->"


def _slugify(heading_text: str) -> str:
    """GitHub-flavored Markdown heading slug (approximate)."""
    s = heading_text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def collect_framework_targets(text: str) -> set[str]:
    """Return the set of heading slugs and <a id> values defined INSIDE the
    framework block. These targets disappear when the framework is stripped,
    so any body link pointing to them must be unwrapped.

    Boundaries are matched as full lines (line.strip() == MARKER) so literal
    mentions of the markers in prose (e.g. inside backticks documenting the
    strip range) are ignored.
    """
    lines = text.splitlines()
    start_idx = end_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == FRAMEWORK_START and start_idx < 0:
            start_idx = i
        elif line.strip() == FRAMEWORK_END:
            end_idx = i  # keep updating; we want the last line-anchored match
    if start_idx < 0 or end_idx < 0 or end_idx <= start_idx:
        return set()
    inner = "\n".join(lines[start_idx : end_idx + 1])

    targets: set[str] = set()
    for m in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", inner, re.MULTILINE):
        slug = _slugify(m.group(2))
        if slug:
            targets.add(slug)
    for m in re.finditer(r'<a\s+id="([^"]+)"\s*>\s*</a>', inner):
        targets.add(m.group(1))
    return targets


def unwrap_framework_links(text: str, framework_targets: set[str]) -> str:
    """Replace [label](#X) with label for every X in framework_targets.
    Other links are left intact."""
    if not framework_targets:
        return text

    def repl(m: re.Match[str]) -> str:
        label = m.group(1)
        target = m.group(2)
        if target in framework_targets:
            return label
        return m.group(0)

    return re.sub(r"\[([^\]]+)\]\(#([^)]+)\)", repl, text)


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, int]:
    """Parse YAML frontmatter; return (parsed_dict_or_None, end_line_idx_1based)."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None, 0
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            try:
                fm = yaml.safe_load("\n".join(lines[1:i]))
                if isinstance(fm, dict):
                    return fm, i + 1
            except yaml.YAMLError:
                pass
            return None, i + 1
    return None, 0


# ---------------------------------------------------------------------------
# Framework stripping
# ---------------------------------------------------------------------------


def strip_framework_block(text: str) -> str:
    """Remove the framework block plus its trailing horizontal-rule separator.

    The leading --- (between title and framework) is preserved — it becomes
    the separator between the title and the next non-framework section.
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == FRAMEWORK_START:
            # Find the matching end
            j = i
            while j < len(lines) and lines[j].strip() != FRAMEWORK_END:
                j += 1
            if j >= len(lines):
                # Malformed: framework opener with no closer. Leave the file
                # untouched in that section to avoid silently destroying content.
                break
            j += 1  # past @end line
            # Skip trailing blank lines plus at most one --- separator
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and lines[j].strip() == "---":
                j += 1
            i = j
            continue
        out.append(line)
        i += 1
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return text


# ---------------------------------------------------------------------------
# Title regeneration
# ---------------------------------------------------------------------------


def _title_replacement(fm: dict[str, Any]) -> str:
    title_text = fm.get("title") or "Untitled"
    version = fm.get("version") or "?"
    date = fm.get("date") or ""
    subtitle = fm.get("subtitle") or ""

    parts: list[str] = [
        TITLE_START,
        "",
        f"# {title_text} — Research Document",
        "",
    ]
    if subtitle:
        parts.append(f"*{subtitle}*")
        parts.append("")
    stamp = f"**Version:** {version}"
    if date:
        stamp += f" · **Updated:** {date}"
    parts.append(stamp)
    parts.append("")
    parts.append(TITLE_END)
    return "\n".join(parts)


def regenerate_title_block(text: str, fm: dict[str, Any]) -> str:
    """Replace the verbose source-file title block with a minimal one."""
    pattern = re.compile(
        rf"{re.escape(TITLE_START)}.*?{re.escape(TITLE_END)}",
        re.DOTALL,
    )
    return pattern.sub(_title_replacement(fm), text, count=1)


# ---------------------------------------------------------------------------
# Top-level transform
# ---------------------------------------------------------------------------


def clean_md_text(text: str, fm: dict[str, Any]) -> str:
    """Apply all clean-view transformations."""
    framework_targets = collect_framework_targets(text)
    text = strip_framework_block(text)
    text = unwrap_framework_links(text, framework_targets)
    text = regenerate_title_block(text, fm)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def derive_clean_path(source_path: Path, fm: dict[str, Any]) -> Path:
    """Return the clean-view path: {file_name}_v{version}.md alongside source."""
    file_name = fm.get("file_name")
    version = fm.get("version")
    if file_name and version:
        return source_path.with_name(f"{file_name}_v{version}.md")
    # Fallback: strip -source from the source filename
    stem = source_path.stem
    if stem.endswith("-source"):
        stem = stem[: -len("-source")]
    return source_path.with_name(f"{stem}.md")


def clean_md(source_path: Path, output_path: Path | None = None) -> Path:
    """Generate the clean view and write it. Returns the output path."""
    text = source_path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    if fm is None:
        raise ValueError(f"{source_path}: missing or invalid YAML frontmatter")
    fmt_ver = fm.get("doc_format_version", fm.get("format_version"))
    if fmt_ver != 2:
        raise ValueError(
            f"{source_path}: doc_format_version is not 2 (this tool processes v2 Markdown only)"
        )
    if (fm.get("project") or {}).get("domain") is None:
        raise ValueError(
            f"{source_path}: this is a starter file (project.domain is null); "
            f"nothing to clean yet — fill it in via session zero first"
        )

    cleaned = clean_md_text(text, fm)

    if output_path is None:
        output_path = derive_clean_path(source_path, fm)
    if output_path.resolve() == source_path.resolve():
        raise ValueError(
            f"output path {output_path} would overwrite the source file; specify a different -o"
        )
    output_path.write_text(cleaned, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the clean view of a v2 Markdown research document."
    )
    parser.add_argument("file", type=Path, help="Path to the *_v*-source.md file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: {file_name}_v{version}.md alongside source)",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Write to stdout instead of a file",
    )
    args = parser.parse_args(argv)

    if not args.file.is_file():
        print(f"Error: {args.file} not found", file=sys.stderr)
        return 2

    if args.print:
        text = args.file.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        if fm is None or fm.get("doc_format_version", fm.get("format_version")) != 2:
            print(f"Error: {args.file} is not a v2 Markdown document", file=sys.stderr)
            return 2
        if (fm.get("project") or {}).get("domain") is None:
            print(f"Error: {args.file} is a starter file (project.domain is null)", file=sys.stderr)
            return 2
        sys.stdout.write(clean_md_text(text, fm))
        return 0

    try:
        out = clean_md(args.file, args.output)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    src_size = args.file.stat().st_size
    out_size = out.stat().st_size
    pct = (1 - out_size / src_size) * 100 if src_size else 0
    print(
        f"\u2714  {args.file.name} \u2192 {out.name} "
        f"({src_size:,} \u2192 {out_size:,} bytes, {pct:.0f}% smaller)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
