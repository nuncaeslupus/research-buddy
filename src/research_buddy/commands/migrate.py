"""`migrate-v1-to-v2` command — convert a v1 JSON document to v2 Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research_buddy.fileio import atomic_write
from research_buddy.migrate_v1_to_v2 import (
    derive_output_path as derive_md_output_path,
)
from research_buddy.migrate_v1_to_v2 import (
    migrate as migrate_v1_to_v2,
)


def cmd_migrate(args: argparse.Namespace) -> int:
    """Migrate v1 JSON document(s) to v2 Markdown."""
    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix != ".json":
            print(
                f"Error: `migrate-v1-to-v2` only processes .json files; got {path.name}",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        if not path.is_file():
            print(f"Error: {path} not found.", file=sys.stderr)
            exit_code = 1
            continue

        try:
            with path.open(encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(
                f"Error: {path.name} is not valid JSON or has invalid encoding: {e}",
                file=sys.stderr,
            )
            exit_code = 2
            continue

        # Resolve output path: -o wins; otherwise derive from doc + input dir
        out = Path(args.output).resolve() if args.output else derive_md_output_path(path, doc)

        if out.exists() and not args.force:
            print(
                f"Error: {out} already exists. Use --force to overwrite, or specify -o.",
                file=sys.stderr,
            )
            exit_code = 2
            continue

        try:
            text = migrate_v1_to_v2(doc)
            atomic_write(out, text)
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            exit_code = 2
            continue

        src_size = path.stat().st_size
        out_size = out.stat().st_size
        print(f"✔  {path.name} → {out.name} ({src_size:,} → {out_size:,} bytes)")
        print(f"   Next: research-buddy validate {out.name}")
    return exit_code
