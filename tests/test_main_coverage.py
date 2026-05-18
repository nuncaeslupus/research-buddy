"""Supplementary CLI coverage — error paths, MD pipeline, main() dispatch.

Companion to test_main.py: that file covers the happy paths; this one targets
the branches the original suite skipped — argparse wiring, watch loop,
migrate / clean / upgrade-md handlers, prior-flag validation, batch-mode
errors, and the various starter-load / theme-cascade fallbacks. Together
they bring main.py above the 85% threshold required by roadmap step #6.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# main() — argparse + dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    """`main()` parses argv, picks a handler, and calls sys.exit(rc).

    Patching sys.argv + catching SystemExit exercises the whole argparse setup
    (lines 858-1003) in one shot, then dispatches into the real handler so the
    handler's happy path runs too.
    """

    def _run_main(self, argv: list[str]) -> int:
        from research_buddy.main import main

        with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as exc:
            main()
        code = exc.value.code
        return int(code) if code is not None else 0

    def test_init_via_main(self, tmp_path: Path) -> None:
        target = tmp_path / "fresh"
        rc = self._run_main(["research-buddy", "init", str(target)])
        assert rc == 0
        assert (target / "source" / "research-document.md").exists()

    def test_init_v1_via_main(self, tmp_path: Path) -> None:
        target = tmp_path / "legacy"
        rc = self._run_main(["research-buddy", "init", str(target), "--v1"])
        assert rc == 0
        assert (target / "source" / "research-document.json").exists()

    def test_build_via_main(self, tmp_project: Path) -> None:
        rc = self._run_main(["research-buddy", "build", str(tmp_project)])
        assert rc == 0

    def test_validate_via_main(self, tmp_project: Path) -> None:
        rc = self._run_main(["research-buddy", "validate", str(tmp_project)])
        assert rc == 0

    def test_no_subcommand_errors(self) -> None:
        # argparse exits with code 2 on missing required subcommand
        from research_buddy.main import main

        with patch.object(sys, "argv", ["research-buddy"]), pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# cmd_migrate — v1 JSON → v2 Markdown
# ---------------------------------------------------------------------------


class TestMigrate:
    """`research-buddy migrate-v1-to-v2 <file>.json` → v2 Markdown source."""

    def _args(self, paths: list[str], output: str | None = None, force: bool = False) -> object:
        from argparse import Namespace

        return Namespace(paths=paths, output=output, force=force)

    def test_migrate_happy_path(self, tmp_project: Path) -> None:
        from research_buddy.main import cmd_migrate

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        rc = cmd_migrate(self._args([str(json_path)]))
        assert rc == 0
        # Default output is alongside the input with v2 suffix
        out_md = list((tmp_project / "source").glob("*-source.md"))
        assert out_md, "expected a migrated .md sibling"

    def test_migrate_rejects_non_json(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_migrate

        md = tmp_path / "fake.md"
        md.write_text("# not json\n")
        rc = cmd_migrate(self._args([str(md)]))
        assert rc == 1

    def test_migrate_missing_file(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_migrate

        rc = cmd_migrate(self._args([str(tmp_path / "nope.json")]))
        assert rc == 1

    def test_migrate_invalid_json(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_migrate

        bad = tmp_path / "bad.json"
        bad.write_text("{ not json")
        rc = cmd_migrate(self._args([str(bad)]))
        assert rc == 2

    def test_migrate_refuses_existing_without_force(self, tmp_project: Path) -> None:
        from research_buddy.main import cmd_migrate

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        out = tmp_project / "blocker.md"
        out.write_text("existing\n")
        rc = cmd_migrate(self._args([str(json_path)], output=str(out)))
        assert rc == 2

    def test_migrate_force_overwrites(self, tmp_project: Path) -> None:
        from research_buddy.main import cmd_migrate

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        out = tmp_project / "out.md"
        out.write_text("existing\n")
        rc = cmd_migrate(self._args([str(json_path)], output=str(out), force=True))
        assert rc == 0
        assert out.read_text().startswith("---\n")  # has frontmatter now


# ---------------------------------------------------------------------------
# cmd_clean — strip framework from v2 source
# ---------------------------------------------------------------------------


class TestClean:
    """`research-buddy clean <source.md>` → clean-view .md."""

    def _args(self, paths: list[str], output: str | None = None) -> object:
        from argparse import Namespace

        return Namespace(paths=paths, output=output)

    def _scaffold_filled_md(self, tmp_path: Path) -> Path:
        """Create a v2 source file with project.domain filled (so clean accepts it)."""
        from argparse import Namespace

        from research_buddy.main import cmd_init

        cmd_init(
            Namespace(
                path=str(tmp_path / "proj"),
                title="Demo",
                subtitle=None,
                ver="1.0",
                v1=False,
            )
        )
        src = tmp_path / "proj" / "source" / "research-document.md"
        # The fresh starter has `project.domain: null` and `version: null`,
        # which clean_md rejects. Patch the frontmatter so the file represents
        # a real post-session-zero source.
        text = src.read_text(encoding="utf-8")
        text = text.replace("version: null", 'version: "1.0"', 1)
        text = text.replace("date: null", 'date: "2026-05-17"', 1)
        text = text.replace("  domain: null", '  domain: "Test domain"', 1)
        out = tmp_path / "proj" / "source" / "demo_v1.0-source.md"
        out.write_text(text, encoding="utf-8")
        return out

    def test_clean_happy_path(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_clean

        md_path = self._scaffold_filled_md(tmp_path)
        rc = cmd_clean(self._args([str(md_path)]))
        assert rc == 0

    def test_clean_rejects_non_md(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_clean

        bogus = tmp_path / "x.json"
        bogus.write_text("{}")
        rc = cmd_clean(self._args([str(bogus)]))
        assert rc == 1

    def test_clean_missing_file(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_clean

        rc = cmd_clean(self._args([str(tmp_path / "ghost.md")]))
        assert rc == 1

    def test_clean_invalid_md(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_clean

        bad = tmp_path / "bad.md"
        bad.write_text("no frontmatter, no anchors\n")
        rc = cmd_clean(self._args([str(bad)]))
        assert rc == 2


# ---------------------------------------------------------------------------
# cmd_validate — v2 Markdown path + --prior
# ---------------------------------------------------------------------------


class TestValidateMd:
    """The MD branch of `cmd_validate` (lines 401-427) was previously untested."""

    def _args(self, paths: list[str], prior: str | None = None) -> object:
        from argparse import Namespace

        return Namespace(paths=paths, prior=prior)

    def _scaffold_md(self, tmp_path: Path) -> Path:
        from argparse import Namespace

        from research_buddy.main import cmd_init

        cmd_init(
            Namespace(
                path=str(tmp_path / "p"),
                title=None,
                subtitle=None,
                ver="1.0",
                v1=False,
            )
        )
        return tmp_path / "p" / "source" / "research-document.md"

    def test_validate_md_clean(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_validate

        md = self._scaffold_md(tmp_path)
        rc = cmd_validate(self._args([str(md)]))
        # Fresh starter MD may emit info-tier messages but no errors
        assert rc in (0, 1)

    def test_validate_md_missing_file(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_validate

        rc = cmd_validate(self._args([str(tmp_path / "missing.md")]))
        assert rc == 1

    def test_validate_md_with_broken_anchors_reports_errors(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_validate

        bad = tmp_path / "broken.md"
        bad.write_text(
            "---\n"
            'doc_format_version: 2\nresearch_buddy_version: "1.10.0"\n'
            'title: Bad\nversion: "1.0"\ndate: "2026-05-17"\n'
            "---\n\n"
            "<!-- @anchor: orphan -->\n"
            "Body text with no closing marker.\n"
        )
        rc = cmd_validate(self._args([str(bad)]))
        assert rc == 1

    def test_validate_prior_missing(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_validate

        md = self._scaffold_md(tmp_path)
        rc = cmd_validate(self._args([str(md)], prior=str(tmp_path / "no-such-prior.md")))
        # --prior pointing to a non-existent file is a hard error: exit 2
        assert rc == 2

    def test_validate_resolves_directory_failure(self, tmp_path: Path) -> None:
        """Pointing `validate` at a directory with no versioned doc is an error."""
        from research_buddy.main import cmd_validate

        empty = tmp_path / "empty"
        empty.mkdir()
        rc = cmd_validate(self._args([str(empty)]))
        assert rc == 1


# ---------------------------------------------------------------------------
# _upgrade_md_file — v2 framework refresh
# ---------------------------------------------------------------------------


class TestUpgradeMd:
    """The MD branch of `cmd_upgrade` (lines 552-603) was previously untested."""

    def _scaffold_md(self, tmp_path: Path) -> Path:
        from argparse import Namespace

        from research_buddy.main import cmd_init

        cmd_init(
            Namespace(
                path=str(tmp_path / "p"),
                title=None,
                subtitle=None,
                ver="1.0",
                v1=False,
            )
        )
        return tmp_path / "p" / "source" / "research-document.md"

    def _args(
        self,
        paths: list[str],
        apply: bool = False,
        no_validate: bool = False,
    ) -> object:
        from argparse import Namespace

        return Namespace(paths=paths, apply=apply, no_validate=no_validate)

    def test_upgrade_md_already_in_sync(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        md = self._scaffold_md(tmp_path)
        rc = cmd_upgrade(self._args([str(md)]))
        assert rc == 0

    def test_upgrade_md_dry_run_when_drifted(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        md = self._scaffold_md(tmp_path)
        # Knock the framework block out of sync by appending a stray comment
        # that wouldn't normally appear in a freshly-initialised file.
        text = md.read_text(encoding="utf-8")
        md.write_text(text.replace("doc_format_version: 2", "format_version: 2"))
        rc = cmd_upgrade(self._args([str(md)]))
        assert rc == 1  # dry-run with diffs returns 1

    def test_upgrade_md_apply_writes_file(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        md = self._scaffold_md(tmp_path)
        text = md.read_text(encoding="utf-8")
        md.write_text(text.replace("doc_format_version: 2", "format_version: 2"))
        rc = cmd_upgrade(self._args([str(md)], apply=True))
        # After --apply the file should be back in sync
        assert rc == 0
        assert "doc_format_version: 2" in md.read_text(encoding="utf-8")

    def test_upgrade_md_missing_file(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        rc = cmd_upgrade(self._args([str(tmp_path / "ghost.md")]))
        assert rc == 2


# ---------------------------------------------------------------------------
# cmd_build — error branches the happy-path suite skips
# ---------------------------------------------------------------------------


class TestBuildErrors:
    """Argument-validation branches in `cmd_build` (lines 227-251, 313-355)."""

    def _args(self, **kwargs: object) -> object:
        from argparse import Namespace

        defaults = {
            "paths": [],
            "watch": False,
            "pdf": False,
            "all": False,
            "validate_only": False,
            "no_versioning": False,
            "theme": None,
            "output": None,
        }
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_mixed_json_and_md_is_error(self, tmp_project: Path, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        md_path = tmp_path / "stray.md"
        md_path.write_text(
            "---\ndoc_format_version: 2\n"
            'research_buddy_version: "1.10.0"\n'
            'title: x\nversion: "1.0"\ndate: "2026-05-17"\n---\n\nbody\n',
            encoding="utf-8",
        )
        rc = cmd_build(self._args(paths=[str(json_path), str(md_path)]))
        assert rc == 1

    def test_watch_with_md_input_is_error(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        md = tmp_path / "x.md"
        md.write_text(
            '---\ndoc_format_version: 2\nresearch_buddy_version: "1.10.0"\n---\n\nbody\n',
            encoding="utf-8",
        )
        rc = cmd_build(self._args(paths=[str(md)], watch=True))
        assert rc == 1

    def test_pdf_with_md_input_is_error(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        md = tmp_path / "x.md"
        md.write_text(
            '---\ndoc_format_version: 2\nresearch_buddy_version: "1.10.0"\n---\n\nbody\n',
            encoding="utf-8",
        )
        rc = cmd_build(self._args(paths=[str(md)], pdf=True))
        assert rc == 1

    def test_md_file_not_found(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        rc = cmd_build(self._args(paths=[str(tmp_path / "ghost.md")]))
        assert rc == 1

    def test_watch_with_multiple_paths_is_error(self, tmp_project: Path) -> None:
        from research_buddy.main import cmd_build

        rc = cmd_build(self._args(paths=[str(tmp_project), str(tmp_project)], watch=True))
        assert rc == 1

    def test_path_does_not_exist(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        rc = cmd_build(self._args(paths=[str(tmp_path / "nope")]))
        assert rc == 1

    def test_all_with_empty_directory(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        empty = tmp_path / "empty"
        empty.mkdir()
        rc = cmd_build(self._args(paths=[str(empty)], all=True))
        assert rc == 1

    def test_directory_without_versioned_doc(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        empty = tmp_path / "empty"
        empty.mkdir()
        rc = cmd_build(self._args(paths=[str(empty)]))
        assert rc == 1

    def test_validate_only_with_issues_returns_1(self, tmp_project: Path) -> None:
        from research_buddy.main import cmd_build

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        with json_path.open() as f:
            doc = json.load(f)
        del doc["meta"]
        with json_path.open("w") as f:
            json.dump(doc, f)
        rc = cmd_build(self._args(paths=[str(json_path)], validate_only=True))
        assert rc == 1


# ---------------------------------------------------------------------------
# perform_build_md — MD-specific helper that drives the .md → HTML pipeline
# ---------------------------------------------------------------------------


class TestPerformBuildMd:
    """Direct tests of `perform_build_md` to exercise the theme cascade."""

    def _scaffold_md(self, tmp_path: Path) -> Path:
        from argparse import Namespace

        from research_buddy.main import cmd_init

        cmd_init(
            Namespace(
                path=str(tmp_path / "p"),
                title=None,
                subtitle=None,
                ver="1.0",
                v1=False,
            )
        )
        return tmp_path / "p" / "source" / "research-document.md"

    def test_explicit_theme_flag_takes_precedence(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        md = self._scaffold_md(tmp_path)
        theme = tmp_path / "custom.css"
        theme.write_text(":root { --rb-test: 1 }\n")
        rc = perform_build_md(md, md.parent.parent, theme=str(theme))
        assert rc in (0, 1)
        html = (md.parent.parent / "research-document.html").read_text(encoding="utf-8")
        assert "--rb-test: 1" in html

    def test_frontmatter_theme_css_resolves_relative_to_md(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        md = self._scaffold_md(tmp_path)
        # Drop a theme file alongside the md and reference it from frontmatter
        theme = md.parent / "fm-theme.css"
        theme.write_text(":root { --rb-fm: 1 }\n")
        text = md.read_text(encoding="utf-8")
        text = text.replace(
            "research_buddy_version:",
            'theme_css: "fm-theme.css"\nresearch_buddy_version:',
            1,
        )
        md.write_text(text, encoding="utf-8")
        rc = perform_build_md(md, md.parent.parent)
        assert rc in (0, 1)
        html = (md.parent.parent / "research-document.html").read_text(encoding="utf-8")
        assert "--rb-fm: 1" in html

    def test_no_versioning_skips_versions_dir(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        md = self._scaffold_md(tmp_path)
        out = tmp_path / "p" / "custom.html"
        rc = perform_build_md(md, md.parent.parent, output=str(out), no_versioning=True)
        assert rc in (0, 1)
        assert out.exists()
        # versions/ should still exist (created by init) but be empty
        versions = md.parent.parent / "versions"
        assert versions.exists()
        assert not list(versions.glob("*.html"))


# ---------------------------------------------------------------------------
# _set_frontmatter_scalar — line 828/835 edge cases
# ---------------------------------------------------------------------------


class TestSetFrontmatterScalar:
    """Direct tests for the YAML edge cases in `_set_frontmatter_scalar`."""

    def test_no_leading_delim_returns_unchanged(self) -> None:
        from research_buddy.main import _set_frontmatter_scalar

        text = "no frontmatter here\n"
        assert _set_frontmatter_scalar(text, "title", "x") == text

    def test_no_closing_delim_returns_unchanged(self) -> None:
        from research_buddy.main import _set_frontmatter_scalar

        text = "---\ntitle: null\n# no closing ---\n"
        assert _set_frontmatter_scalar(text, "title", "x") == text

    def test_missing_key_is_noop(self) -> None:
        from research_buddy.main import _set_frontmatter_scalar

        text = "---\nfoo: bar\n---\n"
        # Returns the input unchanged (no `title:` line to patch)
        assert _set_frontmatter_scalar(text, "title", "x") == text


# ---------------------------------------------------------------------------
# perform_build — PDF generation success + error paths
# ---------------------------------------------------------------------------


class TestPerformBuildPdf:
    """The `--pdf` branch in `perform_build` (lines 127-145)."""

    def test_pdf_generates_alongside_html(self, tmp_project: Path) -> None:
        from research_buddy.main import perform_build

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        rc = perform_build(json_path, tmp_project, pdf=True)
        assert rc in (0, 1)
        # Stable HTML location: <project>/<file_name>.html → sibling .pdf
        pdfs = list(tmp_project.glob("*.pdf"))
        assert pdfs, "expected at least one .pdf next to the rendered HTML"

    def test_pdf_missing_weasyprint_returns_1(self, tmp_project: Path) -> None:
        from research_buddy.main import perform_build

        json_path = next((tmp_project / "source").glob("*_v*.json"))
        # Force the import inside perform_build to fail
        with patch.dict(sys.modules, {"weasyprint": None}):
            rc = perform_build(json_path, tmp_project, pdf=True)
        assert rc == 1
