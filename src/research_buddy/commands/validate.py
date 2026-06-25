"""`validate` command — check a v2 Markdown document without building."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research_buddy.validator_md import validate_md


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate v2 Markdown document(s) without building.

    The --prior flag enables diff-based checks (anchor preservation +
    append-only invariants) against a prior version of the same file.
    """
    exit_code = 0
    prior_path: Path | None = None
    if getattr(args, "prior", None):
        prior_path = Path(args.prior).resolve()
        if not prior_path.is_file():
            print(f"Error: --prior {prior_path} not found.", file=sys.stderr)
            return 2

    for p in args.paths:
        path = Path(p).resolve()

        if path.suffix != ".md":
            print(
                f"Error: {path} is not a .md file. v1 JSON support was removed in v2.0.",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        if not path.is_file():
            print(f"Error: {path} not found.", file=sys.stderr)
            exit_code = 1
            continue

        print(f"Validating {path.name}…")
        md_issues = validate_md(path, prior=prior_path)
        errors = [i for i in md_issues if i.severity == "error"]
        warnings = [i for i in md_issues if i.severity == "warning"]
        infos = [i for i in md_issues if i.severity == "info"]

        if not md_issues:
            print(f"✔  {path.name}: No issues found.")
        else:
            summary_parts = [f"{len(errors)} error(s)"]
            if warnings:
                summary_parts.append(f"{len(warnings)} warning(s)")
            if infos:
                summary_parts.append(f"{len(infos)} info")
            print(f"\n⚠  {', '.join(summary_parts)} in {path.name}:")
            for md_issue in md_issues:
                line_str = f" (line {md_issue.line})" if md_issue.line else ""
                sev = md_issue.severity.upper()
                print(f"   [{sev}] {md_issue.code}: {md_issue.message}{line_str}")
            if errors:
                exit_code = 1

    return exit_code
