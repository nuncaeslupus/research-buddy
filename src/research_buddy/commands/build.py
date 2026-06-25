"""`build` command — render HTML from a v2 Markdown source file."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from research_buddy.build_md import build_md_html
from research_buddy.clean_md import parse_frontmatter as parse_md_frontmatter
from research_buddy.fileio import FileReadError, read_text_or_error
from research_buddy.validator_md import validate_md


def perform_build_md(
    md_path: Path,
    project_root: Path,
    theme: str | None = None,
    output: str | None = None,
    no_versioning: bool = False,
) -> int:
    """Build HTML from a v2 Markdown source file."""
    print(f"Reading {md_path.name}…")
    try:
        text = read_text_or_error(md_path)
    except FileReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    md_issues = validate_md(md_path)
    errors = [i for i in md_issues if i.severity == "error"]
    if md_issues:
        sev_counts = (
            f"{len(errors)} error(s), "
            f"{sum(1 for i in md_issues if i.severity == 'warning')} warning(s)"
        )
        print(f"\n⚠  {sev_counts} in {md_path.name}:")
        for issue in md_issues:
            line_str = f" (line {issue.line})" if issue.line else ""
            print(f"   [{issue.severity.upper()}] {issue.code}: {issue.message}{line_str}")
        print()

    fm, _ = parse_md_frontmatter(text)
    fm = fm or {}

    # Theme cascade (highest priority first):
    # 1. Explicit `--theme PATH` CLI flag
    # 2. Frontmatter `theme_css` field (project-relative)
    # 3. Conventional `theme.css` next to the project root
    theme_css = None
    if theme:
        theme_path = Path(theme)
    elif fm.get("theme_css"):
        theme_path = (md_path.parent / str(fm["theme_css"])).resolve()
        if not theme_path.exists():
            theme_path = (project_root / str(fm["theme_css"])).resolve()
    else:
        theme_path = project_root / "theme.css"
    if theme_path.is_file():
        try:
            theme_css = read_text_or_error(theme_path)
        except FileReadError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(f"Using theme: {theme_path.name}")

    # Don't render a document the validator rejects — a broken anchor, dangling
    # cross-link, or unclosed fence produces corrupt HTML. Warnings don't block.
    if errors:
        print(
            f"Aborting: {len(errors)} validation error(s) — fix them (or build the "
            "prior version) before rendering.",
            file=sys.stderr,
        )
        return 1

    print("Building HTML…")
    html = build_md_html(text, theme_css=theme_css)

    base_name = fm.get("file_name") or re.sub(r"_v\d+(?:[._]\d+)*(?:-source)?$", "", md_path.stem)
    stable_path = Path(output).resolve() if output else project_root / f"{base_name}.html"

    if not no_versioning:
        versions_dir = project_root / "versions"
        versions_dir.mkdir(exist_ok=True)
        version = fm.get("version", "1.0")
        versioned_name = f"{base_name}_v{version}.html"
        versioned_path = versions_dir / versioned_name
        versioned_path.write_text(html, encoding="utf-8")
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(versioned_path, stable_path)
        print(f"Written → versions/{versioned_name}")
    else:
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        stable_path.write_text(html, encoding="utf-8")

    size_kb = len(html.encode()) / 1024
    print(f"Written → {stable_path} ({size_kb:.0f} KB)")
    return 1 if errors else 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build HTML from v2 Markdown source file(s)."""
    if args.output and len(args.paths) > 1:
        print(
            "Error: --output cannot be combined with multiple input files "
            "(each build would overwrite the same output). Build them one at a time.",
            file=sys.stderr,
        )
        return 1
    exit_code = 0
    for p in args.paths:
        md_path = Path(p).resolve()
        if md_path.suffix != ".md":
            print(
                f"Error: {md_path} is not a .md file. "
                "v1 JSON support was removed in v2.0; migrate with `research-buddy "
                "migrate-v1-to-v2`.",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        if not md_path.is_file():
            print(f"Error: {md_path} not found.", file=sys.stderr)
            exit_code = 1
            continue
        rc = perform_build_md(md_path, md_path.parent, args.theme, args.output, args.no_versioning)
        if rc != 0:
            exit_code = rc
    return exit_code
