"""`turn1` command — print the Turn-1 second-opinion brief skeleton.

Read-only helper: reads a v2 source file, pre-fills the brief from the
frontmatter + the top Open Research Queue row, and prints it wrapped in
`@brief-start` / `@brief-end` markers ready to paste into the Turn 1 response.
Guidance about what still needs filling goes to stderr so it never pollutes the
copy-paste block.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research_buddy.turn1 import Turn1Error, build_brief_skeleton


def cmd_turn1(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    if path.suffix != ".md":
        print(
            f"Error: `turn1` only processes v2 Markdown files; got {path.name}",
            file=sys.stderr,
        )
        return 2
    if not path.is_file():
        print(f"Error: {path} not found", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    try:
        skeleton, notes = build_brief_skeleton(text)
    except Turn1Error as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    print(skeleton)
    for note in notes:
        print(note, file=sys.stderr)
    return 0
