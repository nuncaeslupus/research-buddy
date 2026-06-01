"""`locate` command — find the live `@end: <anchor>` insertion point in a v2 file.

Agents append new entries "immediately before the section's `@end` marker".
A plain `grep` for `@end: rules` can match prose mentions or fenced template
examples as well as the real marker, forcing a retry with more context. This
command resolves the *live* marker only: it matches full-line
`<!-- @end: <anchor> -->` markers that are not inside a fenced code block
(reusing `validator_md._line_in_fence`), and prints the line number plus a few
lines of surrounding context so the agent can jump straight to the insertion
point.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from research_buddy.validator_md import _line_in_fence


def _normalize_anchor(raw: str) -> str:
    """Accept `rules`, `@end: rules`, or `<!-- @end: rules -->` and return the
    bare anchor ID."""
    s = raw.strip()
    s = re.sub(r"^<!--\s*", "", s)
    s = re.sub(r"\s*-->$", "", s)
    s = re.sub(r"^@(?:end|anchor):\s*", "", s)
    return s.strip()


def find_end_marker(lines: list[str], anchor: str) -> list[int]:
    """Return 0-based indices of live `<!-- @end: anchor -->` markers — full-line
    matches that are not inside a fenced code block."""
    in_fence = _line_in_fence(lines)
    pat = re.compile(rf"^\s*<!-- @end:\s*{re.escape(anchor)}\s*-->\s*$")
    return [i for i, line in enumerate(lines) if not in_fence[i] and pat.match(line)]


def cmd_locate(args: argparse.Namespace) -> int:
    """Print the live `@end` insertion point for an anchor."""
    path = Path(args.path).resolve()
    if path.suffix != ".md":
        print(f"Error: `locate` only processes v2 Markdown files; got {path.name}", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"Error: {path} not found", file=sys.stderr)
        return 2

    anchor = _normalize_anchor(args.anchor)
    if not anchor:
        print("Error: empty anchor", file=sys.stderr)
        return 2

    lines = path.read_text(encoding="utf-8").splitlines()
    hits = find_end_marker(lines, anchor)

    if not hits:
        print(f"Error: no live `<!-- @end: {anchor} -->` marker in {path.name}", file=sys.stderr)
        return 2

    ctx = max(0, args.context)
    for idx in hits:
        lineno = idx + 1
        print(f"{path.name}:{lineno}  (insert new entries on the line above)")
        start = max(0, idx - ctx)
        end = min(len(lines), idx + ctx + 1)
        for j in range(start, end):
            marker = "→" if j == idx else " "
            print(f"  {marker} {j + 1:>5}  {lines[j]}")
    if len(hits) > 1:
        print(
            f"Warning: {len(hits)} live `@end: {anchor}` markers — the file may be malformed",
            file=sys.stderr,
        )
    return 0
