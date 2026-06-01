"""Helpers shared across CLI command handlers."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from research_buddy.build import find_latest_json


def _resolve_source(path: Path) -> tuple[Path, Path] | None:
    """Given a path (file or dir), return (json_path, project_root).

    Project root is the directory containing source/ and versions/.
    Returns None if no versioned document (*_v*.json) is found.
    """
    if path.is_file():
        # Any .json file: project root is parent, or grandparent if inside source/
        if path.parent.name == "source":
            return path, path.parent.parent
        return path, path.parent

    # directory: look for source/ subdir
    source_dir = path / "source" if (path / "source").is_dir() else path
    latest = find_latest_json(source_dir)
    if not latest:
        return None
    project_root = path if (path / "source").is_dir() else path.parent
    return latest, project_root


def _load_starter_template() -> dict[str, Any]:
    """Load the starter template from package assets."""
    ref = resources.files("research_buddy") / "starter.json"
    with ref.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _load_starter_md_text() -> str:
    """Load the v2 starter Markdown text from package assets."""
    ref = resources.files("research_buddy") / "starter.md"
    with ref.open("r", encoding="utf-8") as f:
        return f.read()
