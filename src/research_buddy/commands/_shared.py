"""Helpers shared across CLI command handlers."""

from __future__ import annotations

from importlib import resources


def _load_starter_md_text() -> str:
    """Load the v2 starter Markdown text from package assets."""
    ref = resources.files("research_buddy") / "starter.md"
    with ref.open("r", encoding="utf-8") as f:
        return f.read()
