"""`diff-summary` command — emit the mechanical Turn-2 change-summary block.

`research-buddy diff-summary <old.md> <new.md>` prints the
`<!-- @summary-start --> ... <!-- @summary-end -->` block for the change from
`old` to `new`, with the agent-authored narrative left as a `{{placeholder}}`.
Exit code is 1 when the append-only invariant is violated (so scripts can gate
on it), 0 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research_buddy.diff_summary import (
    build_downstream_action,
    build_summary,
    has_append_only_violation,
)


def cmd_diff_summary(args: argparse.Namespace) -> int:
    """Print the mechanical change-summary block for old → new."""
    old_path = Path(args.old).resolve()
    new_path = Path(args.new).resolve()

    for p in (old_path, new_path):
        if p.suffix != ".md":
            print(
                f"Error: `diff-summary` only processes v2 Markdown files; got {p.name}",
                file=sys.stderr,
            )
            return 2
        if not p.is_file():
            print(f"Error: {p} not found", file=sys.stderr)
            return 2

    old_text = old_path.read_text(encoding="utf-8")
    new_text = new_path.read_text(encoding="utf-8")

    print(build_summary(old_text, new_text))
    action = build_downstream_action(old_text, new_text)
    if action:
        print()
        print(action)
    return 1 if has_append_only_violation(old_text, new_text) else 0
