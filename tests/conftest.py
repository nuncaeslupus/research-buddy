"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def starter_doc() -> dict:
    """Return the starter document that `init` generates."""
    from research_docs.cli import STARTER_DOCUMENT

    return json.loads(json.dumps(STARTER_DOCUMENT))


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Scaffold a project in tmp_path and return the directory."""
    from research_docs.cli import STARTER_DOCUMENT

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (tmp_path / "versions").mkdir()
    doc = json.loads(json.dumps(STARTER_DOCUMENT))
    doc["meta"]["date"] = "January 2026"
    with open(source_dir / "document_v1.0.json", "w") as f:
        json.dump(doc, f)
    return tmp_path
