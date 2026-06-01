"""`validate` command — check a document without building (v1 JSON or v2 MD)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research_buddy.commands._shared import _resolve_source
from research_buddy.validator import validate
from research_buddy.validator_md import validate_md


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate document(s) without building.

    Dispatches on file extension: .md → v2 Markdown validator; all other paths
    → v1 JSON validator (existing behavior). The --prior flag enables diff-based
    checks for .md files; it is silently ignored when validating .json files.
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

        # ── v2 Markdown ─────────────────────────────────────────────────────
        if path.suffix == ".md":
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
            continue

        # ── v1 JSON ─────────────────────────────────────────────────────────
        res = _resolve_source(path)
        if not res:
            print(f"Error: no versioned document (*_v*.json) found for {path}", file=sys.stderr)
            exit_code = 1
            continue
        json_path, _root = res

        print(f"Validating {json_path.name}…")
        with json_path.open(encoding="utf-8") as f:
            doc = json.load(f)

        issues = validate(doc)
        if issues:
            print(f"\n⚠  {len(issues)} issue(s) in {json_path.name}:")
            for issue in issues:
                print(f"   {issue}")
            exit_code = 1
        else:
            print(f"✔  {json_path.name}: No issues found.")

    return exit_code
