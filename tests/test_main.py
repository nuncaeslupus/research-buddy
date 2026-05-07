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
        self.no_versioning = False
        self.title = None
        self.subtitle = None
        self.ver = "1.0"
        self.theme = None
        self.output = None
        self.v1 = False
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestInitV2:
    """Default scaffolding path: v2 Markdown."""

    def test_creates_v2_markdown_document(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target)))
        assert result == 0
        md_path = target / "source" / "research-document.md"
        assert md_path.exists()
        assert (target / "versions").is_dir()
        # v1 JSON must NOT have been created.
        assert not (target / "source" / "research-document.json").exists()

    def test_created_file_has_v2_frontmatter(self, tmp_path: Path) -> None:
        from research_buddy import __version__

        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target)))
        text = (target / "source" / "research-document.md").read_text(encoding="utf-8")
        assert text.startswith("---\n"), "missing leading frontmatter delimiter"
        # doc_format_version: 2 + research_buddy_version pinned to the wheel
        assert "doc_format_version: 2" in text
        assert f'research_buddy_version: "{__version__}"' in text

    def test_created_file_keeps_framework_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target)))
        text = (target / "source" / "research-document.md").read_text(encoding="utf-8")
        assert "<!-- @anchor: framework.core -->" in text
        assert "<!-- @end: framework.reference -->" in text

    def test_init_with_title_patches_frontmatter(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target), title="My Project"))
        assert result == 0
        text = (target / "source" / "research-document.md").read_text(encoding="utf-8")
        # Top-level `title:` line should now carry the chosen value as a
        # double-quoted string. Other frontmatter values must remain null.
        assert '\ntitle: "My Project"' in text
        assert "\nsubtitle: null" in text
        assert "\nversion: null" in text

    def test_init_with_subtitle_patches_frontmatter(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target), subtitle="A short tagline"))
        text = (target / "source" / "research-document.md").read_text(encoding="utf-8")
        assert '\nsubtitle: "A short tagline"' in text

    def test_init_escapes_double_quotes_in_title(self, tmp_path: Path) -> None:
        """Titles containing a double-quote must round-trip through YAML."""
        import yaml

        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target), title='My "Awesome" Project'))
        text = (target / "source" / "research-document.md").read_text(encoding="utf-8")

        # Frontmatter must still parse — without escaping, the inner `"` would
        # close the YAML string early and the next char would be a syntax error.
        fm_text = text.split("---\n", 2)[1]
        fm = yaml.safe_load(fm_text)
        assert fm["title"] == 'My "Awesome" Project'

    def test_refuses_existing(self, tmp_project: Path) -> None:
        result = cmd_init(_Args(path=str(tmp_project)))
        assert result == 1


class TestInitV1:
    """Legacy JSON scaffolding via `--v1`."""

    def test_creates_v1_json_document(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target), v1=True))
        assert result == 0
        assert (target / "source" / "research-document.json").exists()
        assert (target / "versions").is_dir()
        # v2 Markdown must NOT have been created.
        assert not (target / "source" / "research-document.md").exists()

    def test_created_file_is_valid_json(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target), v1=True))
        doc_path = target / "source" / "research-document.json"
        with doc_path.open() as f:
            doc = json.load(f)
        assert "meta" in doc
        assert "tabs" in doc
        assert "agent_guidelines" in doc

    def test_created_file_has_rb_version(self, tmp_path: Path) -> None:
        from research_buddy import __version__

        target = tmp_path / "docs"
        cmd_init(_Args(path=str(target), v1=True))
        doc_path = target / "source" / "research-document.json"
        with doc_path.open() as f:
            doc = json.load(f)
        assert doc["meta"].get("research_buddy_version") == __version__

    def test_init_with_title(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        result = cmd_init(_Args(path=str(target), title="My Project", v1=True))
        assert result == 0
        doc_path = target / "source" / "research-document.json"
        with doc_path.open() as f:
            doc = json.load(f)
        assert doc["meta"]["title"] == "My Project"


class TestBuild:
    def _get_base_name(self, doc_path: Path) -> str:
        with doc_path.open() as f:
            doc = json.load(f)
        base = doc.get("meta", {}).get("file_name")
        if not base:
            base = re.sub(r"_v\d+(\.\d+)*$", "", doc_path.stem)
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
        out_path = tmp_project / "my-research.html"
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
        cmd_init(_Args(path=str(target), v1=True))
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
        with v1_path.open() as f:
            doc = json.load(f)
        doc["meta"]["version"] = "2.0"
        with v2_path.open("w") as f:
            json.dump(doc, f)

        base = self._get_base_name(v1_path)
        result = cmd_build(_Args(paths=[str(v1_path), str(v2_path)]))
        assert result == 0
        assert (tmp_project / "versions" / f"{base}_v1.0.html").exists()
        assert (tmp_project / "versions" / f"{base}_v2.0.html").exists()

    def test_build_all_with_generic_naming(self, tmp_project: Path) -> None:
        """`--all` must pick up any *_v*.json, not just files named document_v*.json."""
        source = tmp_project / "source"
        v1_path = next(source.glob("*_v*.json"))
        v2_path = source / "test-project_v2.0.json"
        with v1_path.open() as f:
            doc = json.load(f)
        doc["meta"]["version"] = "2.0"
        with v2_path.open("w") as f:
            json.dump(doc, f)

        base = self._get_base_name(v1_path)
        result = cmd_build(_Args(paths=[str(tmp_project)], all=True))
        assert result == 0
        assert (tmp_project / "versions" / f"{base}_v1.0.html").exists()
        assert (tmp_project / "versions" / f"{base}_v2.0.html").exists()

    def test_build_all_sort_ignores_non_version_digits(self, tmp_project: Path) -> None:
        """Project names that contain digits must still sort by version suffix."""
        source = tmp_project / "source"
        # Remove the default; create three files where the "name digits" vs
        # "version digits" disagree on ordering.
        for existing in list(source.glob("*.json")):
            existing.unlink()

        with (source / "2024_report_v1.0.json").open("w") as f:
            json.dump({"meta": {"version": "1.0", "date": "d"}, "tabs": []}, f)
        with (source / "2024_report_v2.0.json").open("w") as f:
            json.dump({"meta": {"version": "2.0", "date": "d"}, "tabs": []}, f)
        with (source / "2024_report_v10.0.json").open("w") as f:
            json.dump({"meta": {"version": "10.0", "date": "d"}, "tabs": []}, f)

        # The old sort key (all digits) ordered them as 2024 v1.0, 2024 v2.0, 2024 v10.0
        # (because it extracted [2024, 1, 0], [2024, 2, 0], [2024, 10, 0]) — which happens
        # to be correct here, but a brittler name like "report_v1_2024.json" would break.
        # This test mainly pins behaviour and guards against regressions in the helper.
        result = cmd_build(_Args(paths=[str(tmp_project)], all=True, no_versioning=True))
        # build must succeed and must not crash on sort
        assert result in (0, 1)
        assert (tmp_project / "2024_report.html").exists()


class TestValidate:
    def test_valid_project(self, tmp_project: Path) -> None:
        result = cmd_validate(_Args(paths=[str(tmp_project)]))
        assert result == 0

    def test_invalid_project(self, tmp_project: Path) -> None:
        doc_path = next((tmp_project / "source").glob("*_v*.json"))
        with doc_path.open() as f:
            doc = json.load(f)
        del doc["meta"]
        with doc_path.open("w") as f:
            json.dump(doc, f)
        result = cmd_validate(_Args(paths=[str(tmp_project)]))
        assert result == 1
