"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def starter_doc() -> dict:
    """Return a fresh copy of the default starter document."""
    from research_docs.main import _load_starter_template
    return _load_starter_template()


@pytest.fixture
def tmp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project directory with a valid document."""
    from research_docs.main import _load_starter_template
    doc = _load_starter_template()

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (tmp_path / "versions").mkdir()

    doc_path = source_dir / "document_v1.0.json"
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(doc, f)

    yield tmp_path
