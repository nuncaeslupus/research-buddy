#!/usr/bin/env python3
"""Synchronize version strings across all project files.
Source of truth: pyproject.toml
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def get_version() -> str:
    content = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def update_init(version: str) -> None:
    path = Path("src/research_buddy/__init__.py")
    content = path.read_text(encoding="utf-8")
    pattern = r'^__version__\s*=\s*"[^"]+"'
    replacement = f'__version__ = "{version}"'
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    path.write_text(content, encoding="utf-8")
    print(f"Updated {path}")


def update_starter(version: str) -> None:
    path = Path("src/research_buddy/starter.json")
    content = path.read_text(encoding="utf-8")
    pattern = r'"research_buddy_version":\s*"[^"]+"'
    replacement = f'"research_buddy_version": "{version}"'
    content = re.sub(pattern, replacement, content)
    path.write_text(content, encoding="utf-8")
    print(f"Updated {path}")


def update_readme(version: str) -> None:
    path = Path("README.md")
    content = path.read_text(encoding="utf-8")
    pattern = r"^# Research Buddy v\d+\.\d+\.\d+"
    replacement = f"# Research Buddy v{version}"
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    path.write_text(content, encoding="utf-8")
    print(f"Updated {path}")


def main() -> None:
    try:
        version = get_version()
        print(f"Syncing version: {version}")
        update_init(version)
        update_starter(version)
        update_readme(version)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
