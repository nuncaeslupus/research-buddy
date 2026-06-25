"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# A representative v1 JSON document, kept as test data (no longer shipped in the
# package after the v2.0 v1 removal) so the `migrate-v1-to-v2` escape hatch stays
# tested against a realistic input.
_V1_FIXTURE = Path(__file__).parent / "fixtures" / "v1_starter.json"


@pytest.fixture
def starter_doc() -> dict:
    """Return a fresh copy of the representative v1 JSON document (for migrate tests)."""
    return json.loads(_V1_FIXTURE.read_text(encoding="utf-8"))
