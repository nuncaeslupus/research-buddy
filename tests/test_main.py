"""Tests for the CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from research_docs.main import cmd_build, cmd_init, cmd_validate


class _Args:
    """Minimal argparse.Namespace substitute."""

    def __init__(self, **kwargs: object) -> None:
        self.watch = False
        self.pdf = False
        self.all = False
        self.validate_only = False
        self.title = None
        self.subtitle = None
        self.ver = "1.0"
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestInit:
    def test_creates_structure(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target)))
        assert result == 0
        assert (target / "source" / "document_v1.0.json").exists()
        assert (target / "versions").is_dir()

    def test_refuses_existing(self, tmp_project: Path) -> None:
        result = cmd_init(_Args(path=str(tmp_project)))
        assert result == 1


class TestBuild:
    def test_build_from_directory(self, tmp_project: Path) -> None:
        result = cmd_build(
            _Args(paths=[str(tmp_project)], theme=None, output="docs.html", validate_only=False)
        )
        assert result == 0
        assert (tmp_project / "docs.html").exists()
        assert (tmp_project / "versions" / "v1.0.html").exists()

    def test_build_custom_output(self, tmp_project: Path) -> None:
        result = cmd_build(
            _Args(paths=[str(tmp_project)], theme=None, output="my-docs.html", validate_only=False)
        )
        assert result == 0
        assert (tmp_project / "my-docs.html").exists()

    def test_build_with_theme(self, tmp_project: Path) -> None:
        theme = tmp_project / "theme.css"
        theme.write_text(":root { --bg: #ffffff; }")
        result = cmd_build(
            _Args(paths=[str(tmp_project)], theme=str(theme), output="docs.html", validate_only=False)
        )
        assert result == 0
        html = (tmp_project / "docs.html").read_text()
        assert "--bg: #ffffff" in html

    def test_validate_only(self, tmp_project: Path) -> None:
        result = cmd_build(
            _Args(paths=[str(tmp_project)], theme=None, output="docs.html", validate_only=True)
        )
        assert result == 0
        assert not (tmp_project / "docs.html").exists()


class TestValidate:
    def test_valid_project(self, tmp_project: Path) -> None:
        result = cmd_validate(_Args(paths=[str(tmp_project)]))
        assert result == 0

    def test_invalid_project(self, tmp_project: Path) -> None:
        doc_path = tmp_project / "source" / "document_v1.0.json"
        with open(doc_path) as f:
            doc = json.load(f)
        del doc["meta"]
        with open(doc_path, "w") as f:
            json.dump(doc, f)
        result = cmd_validate(_Args(paths=[str(tmp_project)]))
        assert result == 1
