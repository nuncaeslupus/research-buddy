"""Tests for the CLI commands."""

from __future__ import annotations

import json
import re
from pathlib import Path

from research_buddy.main import cmd_build, cmd_init, cmd_validate


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
        self.theme = None
        self.output = None
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestInit:
    def test_creates_research_document(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target)))
        assert result == 0
        assert (target / "source" / "research-document.json").exists()
        assert (target / "versions").is_dir()

    def test_created_file_is_valid_json(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target)))
        doc_path = target / "source" / "research-document.json"
        with open(doc_path) as f:
            doc = json.load(f)
        assert "meta" in doc
        assert "tabs" in doc
        assert "agent_guidelines" in doc

    def test_created_file_has_rb_version(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target)))
        doc_path = target / "source" / "research-document.json"
        with open(doc_path) as f:
            doc = json.load(f)
        assert doc["meta"].get("research_buddy_version") == "1.0.3"

    def test_refuses_existing(self, tmp_project: Path) -> None:
        result = cmd_init(_Args(path=str(tmp_project)))
        assert result == 1

    def test_init_with_title(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target), title="My Project"))
        assert result == 0
        doc_path = target / "source" / "research-document.json"
        with open(doc_path) as f:
            doc = json.load(f)
        assert doc["meta"]["title"] == "My Project"


class TestBuild:
    def _get_base_name(self, doc_path: Path) -> str:
        with open(doc_path) as f:
            doc = json.load(f)
        base = doc.get("meta", {}).get("file_name")
        if not base:
            base = re.sub(r"_v\d+[_.]\d+$", "", doc_path.stem)
        return base

    def test_build_from_versioned_file(self, tmp_project: Path) -> None:
        json_path = next((tmp_project / "source").glob("*_v*.json"))
        base = self._get_base_name(json_path)
        result = cmd_build(_Args(paths=[str(json_path)]))
        assert result == 0
        assert (tmp_project / f"{base}.html").exists()

    def test_build_from_directory(self, tmp_project: Path) -> None:
        json_path = next((tmp_project / "source").glob("*_v*.json"))
        base = self._get_base_name(json_path)
        result = cmd_build(_Args(paths=[str(tmp_project)]))
        assert result == 0
        assert (tmp_project / f"{base}.html").exists()

    def test_build_custom_output(self, tmp_project: Path) -> None:
        out_path = tmp_project / "my-docs.html"
        result = cmd_build(_Args(paths=[str(tmp_project)], output=str(out_path)))
        assert result == 0
        assert out_path.exists()

    def test_build_with_theme(self, tmp_project: Path) -> None:
        json_path = next((tmp_project / "source").glob("*_v*.json"))
        base = self._get_base_name(json_path)
        theme = tmp_project / "theme.css"
        theme.write_text(":root { --bg: #ffffff; }")
        result = cmd_build(_Args(paths=[str(tmp_project)], theme=str(theme)))
        assert result == 0
        html = (tmp_project / f"{base}.html").read_text()
        assert "--bg: #ffffff" in html

    def test_validate_only_no_html(self, tmp_project: Path) -> None:
        json_path = next((tmp_project / "source").glob("*_v*.json"))
        base = self._get_base_name(json_path)
        result = cmd_build(_Args(paths=[str(tmp_project)], validate_only=True))
        assert result == 0
        assert not (tmp_project / f"{base}.html").exists()

    def test_html_contains_rb_footer(self, tmp_project: Path) -> None:
        json_path = next((tmp_project / "source").glob("*_v*.json"))
        base = self._get_base_name(json_path)
        cmd_build(_Args(paths=[str(tmp_project)]))
        html = (tmp_project / f"{base}.html").read_text()
        assert "Research Buddy" in html
        assert "rb-powered-by" in html

    def test_html_lang_attribute(self, tmp_project: Path) -> None:
        json_path = next((tmp_project / "source").glob("*_v*.json"))
        base = self._get_base_name(json_path)
        cmd_build(_Args(paths=[str(tmp_project)]))
        html = (tmp_project / f"{base}.html").read_text()
        assert 'lang="en"' in html

    def test_build_unversioned_template(self, tmp_path: Path) -> None:
        """research-document.json (no version in name) should be found and built."""
        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target)))
        json_path = target / "source" / "research-document.json"
        base = self._get_base_name(json_path)
        # research-document.json exists, no *_v*.json
        result = cmd_build(_Args(paths=[str(target)]))
        assert result == 0
        assert (target / f"{base}.html").exists()

    def test_versioned_name_takes_priority(self, tmp_project: Path) -> None:
        """When both versioned and unversioned files exist, versioned wins."""
        source = tmp_project / "source"
        # Add unversioned template alongside versioned file
        (source / "research-document.json").write_text(
            '{"meta": {"version": "0.0", "date": "test"}, "tabs": []}'
        )
        json_path = next(source.glob("*_v*.json"))
        base = self._get_base_name(json_path)
        result = cmd_build(_Args(paths=[str(tmp_project)]))
        # Should succeed (uses the versioned file, not the 0.0 template)
        assert result in (0, 1)  # may have validation warnings, but must not crash
        assert (tmp_project / f"{base}.html").exists()

    def test_build_batch_files(self, tmp_project: Path) -> None:
        v1_path = next((tmp_project / "source").glob("*_v*.json"))
        v2_path = tmp_project / "source" / "test-project_v2.0.json"
        with open(v1_path) as f:
            doc = json.load(f)
        doc["meta"]["version"] = "2.0"
        with open(v2_path, "w") as f:
            json.dump(doc, f)

        base = self._get_base_name(v1_path)
        result = cmd_build(_Args(paths=[str(v1_path), str(v2_path)]))
        assert result == 0
        assert (tmp_project / "versions" / f"{base}_v1.0.html").exists()
        assert (tmp_project / "versions" / f"{base}_v2.0.html").exists()


class TestValidate:
    def test_valid_project(self, tmp_project: Path) -> None:
        result = cmd_validate(_Args(paths=[str(tmp_project)]))
        assert result == 0

    def test_invalid_project(self, tmp_project: Path) -> None:
        doc_path = next((tmp_project / "source").glob("*_v*.json"))
        with open(doc_path) as f:
            doc = json.load(f)
        del doc["meta"]
        with open(doc_path, "w") as f:
            json.dump(doc, f)
        result = cmd_validate(_Args(paths=[str(tmp_project)]))
        assert result == 1
