#!/usr/bin/env python3
"""Fail with a non-zero exit code if the version strings in
src/research_buddy/__init__.py, src/research_buddy/starter.json,
and README.md have drifted from pyproject.toml.

Wired into CI as `make check-version-sync`. Unlike `sync_version.py`, this
script makes no changes — it just compares values.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path


def _pyproject_version() -> str:
    # tomllib is in the stdlib from 3.11+ (this project already requires 3.11);
    # parsing the TOML properly avoids false positives from regex-matching a
    # `version =` line that happens to live inside a [tool.*] table.
    with Path("pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    try:
        return str(data["project"]["version"])
    except KeyError as exc:
        raise SystemExit(f"Could not find project.version in pyproject.toml: {exc}") from exc


def _init_version() -> str:
    content = Path("src/research_buddy/__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not m:
        raise SystemExit("Could not find __version__ in src/research_buddy/__init__.py")
    return m.group(1)


def _starter_version() -> str:
    doc = json.loads(Path("src/research_buddy/starter.json").read_text(encoding="utf-8"))
    ver = doc.get("meta", {}).get("research_buddy_version")
    if not ver:
        raise SystemExit("starter.json is missing meta.research_buddy_version")
    return str(ver)


def _readme_version() -> str:
    content = Path("README.md").read_text(encoding="utf-8")
    # \S+ covers pre-release/build suffixes (e.g. "1.2.0-rc1", "1.2.0+build.5").
    m = re.search(r"^# Research Buddy v(\S+)", content, re.MULTILINE)
    if not m:
        raise SystemExit("Could not find '# Research Buddy v...' heading in README.md")
    return m.group(1)


def main() -> None:
    canonical = _pyproject_version()
    checks = {
        "src/research_buddy/__init__.py (__version__)": _init_version(),
        "src/research_buddy/starter.json (meta.research_buddy_version)": _starter_version(),
        "README.md (# Research Buddy v…)": _readme_version(),
    }
    drift = {k: v for k, v in checks.items() if v != canonical}
    if drift:
        print(f"Version drift detected (pyproject.toml: {canonical}):", file=sys.stderr)
        for where, found in drift.items():
            print(f"  - {where} = {found}", file=sys.stderr)
        print("\nRun `make version-sync` and commit the result.", file=sys.stderr)
        sys.exit(1)
    print(f"Version in sync: {canonical}")


if __name__ == "__main__":
    main()
