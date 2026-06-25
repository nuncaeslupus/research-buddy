"""`upgrade` command — refresh a v2 Markdown source against the installed starter.md.

Replaces the template-owned regions (preamble, framework block, agent-reminder
blockquote) and migrates frontmatter; project-owned content is preserved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research_buddy.commands._shared import _load_starter_md_text
from research_buddy.fileio import atomic_write
from research_buddy.upgrade_md import UpgradeError, upgrade_md
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

    if upgraded == source_text:
        # changes were informational only; nothing to write
        print()
        return 0

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
    """Refresh v2 Markdown source(s) against the installed starter.md."""
    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix != ".md":
            print(
                f"Error: {path} is not a .md file. v1 JSON support was removed in v2.0.",
                file=sys.stderr,
            )
            exit_code = max(exit_code, 1)
            continue
        exit_code = max(exit_code, _upgrade_md_file(path, args))
    return exit_code
