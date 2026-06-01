"""`clean` command — generate a clean-view .md from a v2 source file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research_buddy.clean_md import clean_md


def cmd_clean(args: argparse.Namespace) -> int:
    """Generate clean-view .md from v2 source file(s)."""
    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix != ".md":
            print(
                f"Error: `clean` only processes v2 Markdown files; got {path.name}",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        if not path.is_file():
            print(f"Error: {path} not found.", file=sys.stderr)
            exit_code = 1
            continue

        try:
            out = clean_md(path, Path(args.output).resolve() if args.output else None)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            exit_code = 2
            continue

        src_size = path.stat().st_size
        out_size = out.stat().st_size
        pct = (1 - out_size / src_size) * 100 if src_size else 0
        print(
            f"✔  {path.name} → {out.name} ({src_size:,} → {out_size:,} bytes, {pct:.0f}% smaller)"
        )
    return exit_code
