"""`upgrade` command — refresh project source(s) against the installed starter.

Dispatches on file extension: `.md` paths use the v2 Markdown upgrade
(framework block + frontmatter migration); other paths use the v1 JSON
upgrade (agent_guidelines refresh + key reordering).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research_buddy.commands._shared import (
    _load_starter_md_text,
    _load_starter_template,
    _resolve_source,
)
from research_buddy.fileio import atomic_write
from research_buddy.upgrade import docs_equivalent, stamp_format_note, upgrade_doc
from research_buddy.upgrade_md import UpgradeError, upgrade_md
from research_buddy.validator import validate
from research_buddy.validator_md import validate_md


def _upgrade_md_file(path: Path, args: argparse.Namespace) -> int:
    """Upgrade a single v2 Markdown source file. Returns exit code (0/1/2)."""
    from research_buddy import __version__

    try:
        starter_text = _load_starter_md_text()
    except Exception as e:
        print(f"Error loading starter.md: {e}", file=sys.stderr)
        return 2

    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        return 2

    print(f"── {path.name} ──")
    source_text = path.read_text(encoding="utf-8")

    try:
        upgraded, changes = upgrade_md(source_text, starter_text, __version__)
    except UpgradeError as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 2

    if not changes:
        print("  Already in sync with starter.md.")
        print()
        return 0

    for line in changes:
        print(f"  {line}")

    if not args.apply:
        print("  (dry-run — pass --apply to write)")
        print()
        return 1

    atomic_write(path, upgraded)
    print(f"  → wrote {path}")

    exit_code = 0
    if not args.no_validate:
        issues = validate_md(path)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            print(f"  ⚠  {len(errors)} validation error(s) after upgrade:")
            for issue in errors:
                print(f"     {issue}")
            exit_code = 2
    print()
    return exit_code


def cmd_upgrade(args: argparse.Namespace) -> int:
    """Refresh project source(s) against the installed starter template.

    Dispatches on file extension: `.md` paths use the v2 Markdown upgrade
    (framework block + frontmatter migration); other paths use the v1 JSON
    upgrade (agent_guidelines refresh + key reordering).
    """
    from research_buddy import __version__

    try:
        starter = _load_starter_template()
    except Exception as e:
        print(f"Error loading starter template: {e}", file=sys.stderr)
        return 2

    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix == ".md":
            exit_code = max(exit_code, _upgrade_md_file(path, args))
            continue

        res = _resolve_source(path)
        if not res:
            print(
                f"Error: no versioned document (*_v*.json) found for {path}",
                file=sys.stderr,
            )
            exit_code = 2
            continue
        json_path, _root = res

        print(f"── {json_path.name} ──")
        try:
            with json_path.open(encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(
                f"  Error: {json_path.name} is not valid JSON or has invalid encoding: {e}",
                file=sys.stderr,
            )
            exit_code = 2
            continue

        upgraded, changes, key_diffs = upgrade_doc(doc, starter, __version__)

        if docs_equivalent(doc, upgraded):
            print("  Already in sync with starter.json.")
            print()
            continue

        for line in changes:
            print(f"  {line}")

        diff_lines = [
            f"    {label}: {', '.join(keys)}" for label, keys in key_diffs.items() if keys
        ]
        if diff_lines:
            print("  Framework / session_protocol key changes:")
            for line in diff_lines:
                print(line)

        if not args.apply:
            print("  (dry-run — pass --apply to write)")
            print()
            exit_code = 1
            continue

        stamp_format_note(upgraded, __version__)
        payload = json.dumps(upgraded, indent=2, ensure_ascii=False) + "\n"
        atomic_write(json_path, payload)
        print(f"  → wrote {json_path}")

        if not args.no_validate:
            issues = validate(upgraded)
            if issues:
                print(f"  ⚠  {len(issues)} issue(s) after upgrade:")
                for issue in issues:
                    print(f"     {issue}")
                exit_code = 2
        print()

    return exit_code
