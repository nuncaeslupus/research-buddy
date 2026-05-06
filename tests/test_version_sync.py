"""Lock down the version-sync invariant.

Catches drift between the wheel version (pyproject.toml) and the four files
that mirror it: __init__.py, starter.json, starter.md, README.md.

This is a belt-and-suspenders companion to `make check-version-sync` (the CI
gate). The script lives in `scripts/`; this test exercises the same checks
from inside the pytest suite so a developer running `make test` locally also
catches drift before pushing.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def _init_version() -> str:
    content = (REPO_ROOT / "src/research_buddy/__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', content, re.MULTILINE)
    assert m, "missing __version__ in __init__.py"
    return m.group(1)


def _starter_json_version() -> str:
    doc = json.loads((REPO_ROOT / "src/research_buddy/starter.json").read_text(encoding="utf-8"))
    return str(doc["meta"]["research_buddy_version"])


def _starter_md_version() -> str:
    content = (REPO_ROOT / "src/research_buddy/starter.md").read_text(encoding="utf-8")
    m = re.search(r'^research_buddy_version:\s*"([^"]+)"', content, re.MULTILINE)
    assert m, "missing research_buddy_version in starter.md frontmatter"
    return m.group(1)


def _readme_version() -> str:
    content = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"^# Research Buddy v(\S+)", content, re.MULTILINE)
    assert m, "missing '# Research Buddy v…' heading in README.md"
    return m.group(1)


class TestVersionSync:
    def test_init_matches_pyproject(self) -> None:
        assert _init_version() == _pyproject_version()

    def test_starter_json_matches_pyproject(self) -> None:
        assert _starter_json_version() == _pyproject_version()

    def test_starter_md_matches_pyproject(self) -> None:
        assert _starter_md_version() == _pyproject_version()

    def test_readme_matches_pyproject(self) -> None:
        assert _readme_version() == _pyproject_version()

    def test_package_version_attribute_matches(self) -> None:
        from research_buddy import __version__

        assert __version__ == _pyproject_version()
