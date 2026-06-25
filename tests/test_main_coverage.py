"""Supplementary CLI coverage — error paths, MD pipeline, main() dispatch.

Companion to test_main.py: that file covers the init happy path; this one targets
the branches the original suite skipped — argparse wiring, migrate / clean /
upgrade-md / validate-md handlers, prior-flag validation, and the theme-cascade
fallbacks.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_V1_FIXTURE = Path(__file__).parent / "fixtures" / "v1_starter.json"


def _write_v1_json(dest: Path) -> Path:
    """Write the representative v1 JSON sample to `dest` (for migrate handler tests)."""
    dest.write_text(_V1_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _scaffold_md(tmp_path: Path) -> Path:
    """Scaffold a fresh v2 Markdown source via `init` and return its path."""
    from argparse import Namespace

    from research_buddy.main import cmd_init

    cmd_init(Namespace(path=str(tmp_path / "p"), title=None, subtitle=None))
    return tmp_path / "p" / "source" / "research-document.md"


# ---------------------------------------------------------------------------
# main() — argparse + dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    """`main()` parses argv, picks a handler, and calls sys.exit(rc)."""

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

    def test_build_via_main(self, tmp_path: Path) -> None:
        md = _scaffold_md(tmp_path)
        rc = self._run_main(["research-buddy", "build", str(md), "--no-versioning"])
        assert rc in (0, 1)

    def test_validate_via_main(self, tmp_path: Path) -> None:
        md = _scaffold_md(tmp_path)
        rc = self._run_main(["research-buddy", "validate", str(md)])
        assert rc in (0, 1)

    def test_no_subcommand_errors(self) -> None:
        # argparse exits with code 2 on missing required subcommand
        from research_buddy.main import main

        with patch.object(sys, "argv", ["research-buddy"]), pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# cmd_migrate — v1 JSON → v2 Markdown (the retained escape hatch)
# ---------------------------------------------------------------------------


class TestMigrate:
    """`research-buddy migrate-v1-to-v2 <file>.json` → v2 Markdown source."""

    def _args(self, paths: list[str], output: str | None = None, force: bool = False) -> object:
        from argparse import Namespace

        return Namespace(paths=paths, output=output, force=force)

    def test_migrate_happy_path(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_migrate

        json_path = _write_v1_json(tmp_path / "demo_v1.0.json")
        rc = cmd_migrate(self._args([str(json_path)]))
        assert rc == 0
        assert list(tmp_path.glob("*-source.md")), "expected a migrated .md sibling"

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

    def test_migrate_refuses_existing_without_force(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_migrate

        json_path = _write_v1_json(tmp_path / "demo_v1.0.json")
        out = tmp_path / "blocker.md"
        out.write_text("existing\n")
        rc = cmd_migrate(self._args([str(json_path)], output=str(out)))
        assert rc == 2

    def test_migrate_force_overwrites(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_migrate

        json_path = _write_v1_json(tmp_path / "demo_v1.0.json")
        out = tmp_path / "out.md"
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
        src = _scaffold_md(tmp_path)
        # The fresh starter has `project.domain: null` and `version: null`,
        # which clean_md rejects. Patch the frontmatter so the file represents
        # a real post-session-zero source.
        text = src.read_text(encoding="utf-8")
        text = text.replace("version: null", 'version: "1.0"', 1)
        text = text.replace("date: null", 'date: "2026-05-17"', 1)
        text = text.replace("  domain: null", '  domain: "Test domain"', 1)
        out = tmp_path / "p" / "source" / "demo_v1.0-source.md"
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
    """The MD path of `cmd_validate`, including the --prior flag."""

    def _args(self, paths: list[str], prior: str | None = None) -> object:
        from argparse import Namespace

        return Namespace(paths=paths, prior=prior)

    def test_validate_md_clean(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_validate

        md = _scaffold_md(tmp_path)
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

        md = _scaffold_md(tmp_path)
        rc = cmd_validate(self._args([str(md)], prior=str(tmp_path / "no-such-prior.md")))
        # --prior pointing to a non-existent file is a hard error: exit 2
        assert rc == 2

    def test_validate_rejects_non_md(self, tmp_path: Path) -> None:
        """A non-.md path is an error now that v1 JSON support is gone."""
        from research_buddy.main import cmd_validate

        bogus = tmp_path / "x.json"
        bogus.write_text("{}")
        rc = cmd_validate(self._args([str(bogus)]))
        assert rc == 1


# ---------------------------------------------------------------------------
# _upgrade_md_file — v2 framework refresh
# ---------------------------------------------------------------------------


class TestUpgradeMd:
    """The MD path of `cmd_upgrade`."""

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

        md = _scaffold_md(tmp_path)
        rc = cmd_upgrade(self._args([str(md)]))
        assert rc == 0

    def test_upgrade_md_dry_run_when_drifted(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        md = _scaffold_md(tmp_path)
        # Knock the framework block out of sync via the legacy format-version key.
        text = md.read_text(encoding="utf-8")
        md.write_text(text.replace("doc_format_version: 2", "format_version: 2"))
        rc = cmd_upgrade(self._args([str(md)]))
        assert rc == 1  # dry-run with diffs returns 1

    def test_upgrade_md_apply_writes_file(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        md = _scaffold_md(tmp_path)
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

    def test_upgrade_rejects_non_md(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        bogus = tmp_path / "x.json"
        bogus.write_text("{}")
        rc = cmd_upgrade(self._args([str(bogus)]))
        assert rc == 1


# ---------------------------------------------------------------------------
# cmd_build — argument-validation branches
# ---------------------------------------------------------------------------


class TestBuildErrors:
    """Error branches in `cmd_build` (now .md-only)."""

    def _args(self, **kwargs: object) -> object:
        from argparse import Namespace

        defaults = {
            "paths": [],
            "no_versioning": False,
            "theme": None,
            "output": None,
        }
        defaults.update(kwargs)
        return Namespace(**defaults)

    def test_rejects_json_input(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        bogus = tmp_path / "doc.json"
        bogus.write_text("{}")
        rc = cmd_build(self._args(paths=[str(bogus)]))
        assert rc == 1

    def test_md_file_not_found(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        rc = cmd_build(self._args(paths=[str(tmp_path / "ghost.md")]))
        assert rc == 1

    def test_directory_is_rejected(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_build

        empty = tmp_path / "empty"
        empty.mkdir()
        rc = cmd_build(self._args(paths=[str(empty)]))
        assert rc == 1


# ---------------------------------------------------------------------------
# perform_build_md — MD-specific helper that drives the .md → HTML pipeline
# ---------------------------------------------------------------------------


class TestPerformBuildMd:
    """Direct tests of `perform_build_md` to exercise the theme cascade."""

    def test_explicit_theme_flag_takes_precedence(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        md = _scaffold_md(tmp_path)
        theme = tmp_path / "custom.css"
        theme.write_text(":root { --rb-test: 1 }\n")
        rc = perform_build_md(md, md.parent.parent, theme=str(theme))
        assert rc in (0, 1)
        html = (md.parent.parent / "research-document.html").read_text(encoding="utf-8")
        assert "--rb-test: 1" in html

    def test_frontmatter_theme_css_resolves_relative_to_md(self, tmp_path: Path) -> None:
        from research_buddy.main import perform_build_md

        md = _scaffold_md(tmp_path)
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

        md = _scaffold_md(tmp_path)
        out = tmp_path / "p" / "custom.html"
        rc = perform_build_md(md, md.parent.parent, output=str(out), no_versioning=True)
        assert rc in (0, 1)
        assert out.exists()
        # versions/ should still exist (created by init) but be empty
        versions = md.parent.parent / "versions"
        assert versions.exists()
        assert not list(versions.glob("*.html"))

    def test_invalid_utf8_source_reports_cleanly(self, tmp_path: Path, capsys) -> None:
        """A non-UTF-8 .md source returns exit 1 with a clean error, no traceback."""
        from research_buddy.main import perform_build_md

        md = _scaffold_md(tmp_path)
        md.write_bytes(b"---\nbad\xff bytes\n---\n")
        rc = perform_build_md(md, md.parent.parent)
        assert rc == 1
        err = capsys.readouterr().err
        assert "invalid UTF-8 encoding" in err

    def test_invalid_utf8_theme_reports_cleanly(self, tmp_path: Path, capsys) -> None:
        """A non-UTF-8 theme file returns exit 1 with a clean error, no traceback."""
        from research_buddy.main import perform_build_md

        md = _scaffold_md(tmp_path)
        theme = tmp_path / "bad-theme.css"
        theme.write_bytes(b":root { --x: \xff }\n")
        rc = perform_build_md(md, md.parent.parent, theme=str(theme))
        assert rc == 1
        err = capsys.readouterr().err
        assert "invalid UTF-8 encoding" in err


# ---------------------------------------------------------------------------
# _set_frontmatter_scalar — YAML edge cases
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
