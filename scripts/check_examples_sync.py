#!/usr/bin/env python3
"""Fail with a non-zero exit code if the committed starter-example/*.html
files have drifted from what `research-buddy build` produces from the bundled
starters.

Mirrors `make regen-examples`: regenerates both examples into a temp dir and
byte-compares against the committed copies. Wired into CI as
`make check-examples-sync`. Makes no changes — if it fails, run
`make regen-examples` and commit the result.

Catches both content drift (a renderer/starter change that wasn't regenerated)
and version-footer drift (a version bump where the example wasn't rebuilt).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

# (source file, committed example) — mirrors the regen-* Makefile targets.
EXAMPLES = [
    ("src/research_buddy/starter.json", "starter-example/starter.html"),
    ("src/research_buddy/starter.md", "starter-example/starter-md.html"),
]


def main() -> None:
    drift: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        for source, committed in EXAMPLES:
            out = Path(td) / Path(committed).name
            subprocess.run(
                [
                    "research-buddy",
                    "build",
                    source,
                    "--output",
                    str(out),
                    "--no-versioning",
                ],
                check=True,
            )
            committed_path = Path(committed)
            if not committed_path.exists():
                drift.append(f"  - {committed} is missing")
            elif out.read_bytes() != committed_path.read_bytes():
                drift.append(f"  - {committed} is stale")

    if drift:
        print("starter-example drift detected:", file=sys.stderr)
        for line in drift:
            print(line, file=sys.stderr)
        print("\nRun `make regen-examples` and commit the result.", file=sys.stderr)
        sys.exit(1)
    print("starter-example in sync")


if __name__ == "__main__":
    main()
