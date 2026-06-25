"""Tests for the v2 CLI commands."""

from __future__ import annotations

from pathlib import Path

from research_buddy.main import cmd_init


class _Args:
    """Minimal argparse.Namespace substitute."""

    def __init__(self, **kwargs: object) -> None:
        self.no_versioning = False
        self.title = None
        self.subtitle = None
        self.theme = None
        self.output = None
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

    def test_refuses_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "docs"
        (target / "source").mkdir(parents=True)
        (target / "source" / "existing.md").write_text("x")
        result = cmd_init(_Args(path=str(target)))
        assert result == 1
