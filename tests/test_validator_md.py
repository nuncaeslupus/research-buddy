"""Tests for the v2 Markdown validator (`research_buddy.validator_md`)."""

from __future__ import annotations

from pathlib import Path

from research_buddy.validator_md import Issue, validate_md


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _codes(issues: list[Issue]) -> list[str]:
    return [i.code for i in issues]


# Minimal frontmatter that satisfies the required-fields check in *project mode*
# (project.domain set). Body sections are added per-test as needed.
_PROJECT_FM = """\
---
format_version: 2
research_buddy_version: "1.4.0"
version: "1.0"
date: "2026-05-07"
file_name: "demo"
title: "Demo"
language:
  code: en
  label: English
project:
  domain: "demo project"
ui_strings:
  status_open: OPEN
  status_done: "Done"
  status_wip: "WIP"
---
"""


def _project_doc(body: str = "", *, file_name: str = "demo_v1.0.md") -> str:
    return _PROJECT_FM + "\n" + body


class TestFrontmatter:
    def test_missing_frontmatter_errors(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "x.md", "# No frontmatter here\n")
        codes = _codes(validate_md(path))
        assert "frontmatter-parse" in codes

    def test_unparseable_yaml_errors(self, tmp_path: Path) -> None:
        bad = "---\nthis: : is not yaml\n  bad indent\n---\n# body\n"
        path = _write(tmp_path / "x.md", bad)
        codes = _codes(validate_md(path))
        assert "frontmatter-parse" in codes

    def test_wrong_format_version_short_circuits(self, tmp_path: Path) -> None:
        text = "---\nformat_version: 1\n---\n# body\n"
        path = _write(tmp_path / "x.md", text)
        issues = validate_md(path)
        assert any(i.code == "wrong-format-version" for i in issues)
        # Should not run other checks (no anchor/cross-link/etc. issues).
        assert all(i.code in {"wrong-format-version", "frontmatter-parse"} for i in issues)

    def test_missing_required_field_in_project_mode(self, tmp_path: Path) -> None:
        text = """\
---
format_version: 2
research_buddy_version: "1.4.0"
version: "1.0"
date: "2026-05-07"
file_name: "demo"
title: "Demo"
language:
  code: en
project:
  domain: "demo"
---
"""
        path = _write(tmp_path / "demo_v1.0.md", text)
        codes = _codes(validate_md(path))
        # No nulls — should not flag null-in-project; required fields all present.
        assert "frontmatter-missing-field" not in codes
        assert "frontmatter-null-in-project" not in codes

    def test_null_field_in_project_mode_errors(self, tmp_path: Path) -> None:
        text = """\
---
format_version: 2
research_buddy_version: "1.4.0"
version: null
date: "2026-05-07"
file_name: "demo"
title: "Demo"
language:
  code: en
project:
  domain: "demo project"
---
"""
        path = _write(tmp_path / "demo_v1.0.md", text)
        codes = _codes(validate_md(path))
        assert "frontmatter-null-in-project" in codes

    def test_starter_mode_allows_nulls(self, tmp_path: Path) -> None:
        text = """\
---
format_version: 2
research_buddy_version: "1.4.0"
version: null
date: null
file_name: null
title: null
language:
  code: en
project:
  domain: null
---
"""
        path = _write(tmp_path / "starter.md", text)
        codes = _codes(validate_md(path))
        assert "frontmatter-null-in-project" not in codes


class TestAnchorPairing:
    def test_matched_anchors_pass(self, tmp_path: Path) -> None:
        body = "<!-- @anchor: foo -->\nbody\n<!-- @end: foo -->\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        codes = _codes(validate_md(path))
        assert "anchor-no-end" not in codes
        assert "end-no-anchor" not in codes

    def test_orphan_opener_errors(self, tmp_path: Path) -> None:
        body = "<!-- @anchor: foo -->\nbody\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "anchor-no-end" in _codes(validate_md(path))

    def test_orphan_closer_errors(self, tmp_path: Path) -> None:
        body = "body\n<!-- @end: foo -->\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "end-no-anchor" in _codes(validate_md(path))

    def test_anchors_inside_fenced_code_ignored(self, tmp_path: Path) -> None:
        body = "```\n<!-- @anchor: foo -->\n<!-- @end: foo -->\n```\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        codes = _codes(validate_md(path))
        assert "anchor-no-end" not in codes
        assert "end-no-anchor" not in codes


class TestEntryAnchors:
    def test_rule_with_matching_id_passes(self, tmp_path: Path) -> None:
        body = '<!-- @rule: R-FM-1 -->\n<a id="r-fm-1"></a>\n\n**R-FM-1.** Body.\n'
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        codes = _codes(validate_md(path))
        assert "entry-no-link-target" not in codes
        assert "entry-id-mismatch" not in codes

    def test_rule_missing_link_target(self, tmp_path: Path) -> None:
        body = "<!-- @rule: R-FM-1 -->\n\n**R-FM-1.** body\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "entry-no-link-target" in _codes(validate_md(path))

    def test_rule_id_mismatch(self, tmp_path: Path) -> None:
        body = '<!-- @rule: R-FM-1 -->\n<a id="r-fm-2"></a>\n'
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "entry-id-mismatch" in _codes(validate_md(path))

    def test_da_with_matching_id(self, tmp_path: Path) -> None:
        body = '<!-- @da: DA-Q1-1 -->\n<a id="da-q1-1"></a>\n\n**DA-Q1-1.** body\n'
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        codes = _codes(validate_md(path))
        assert "entry-no-link-target" not in codes
        assert "entry-id-mismatch" not in codes

    def test_session_with_matching_id(self, tmp_path: Path) -> None:
        body = '<!-- @session: Q-001 -->\n<a id="q-001"></a>\n\n### Q-001 Topic\n'
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        codes = _codes(validate_md(path))
        assert "entry-no-link-target" not in codes
        assert "entry-id-mismatch" not in codes


class TestCrossLinks:
    def test_link_to_existing_heading_slug_passes(self, tmp_path: Path) -> None:
        body = "## A Section\n\nSee [link](#a-section).\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "broken-cross-link" not in _codes(validate_md(path))

    def test_link_to_a_id_passes(self, tmp_path: Path) -> None:
        body = '<a id="my-target"></a>\n\nText [link](#my-target).\n'
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "broken-cross-link" not in _codes(validate_md(path))

    def test_broken_link_warns(self, tmp_path: Path) -> None:
        body = "Some [broken](#nope).\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        issues = validate_md(path)
        broken = [i for i in issues if i.code == "broken-cross-link"]
        assert len(broken) == 1
        assert broken[0].severity == "warning"

    def test_link_inside_inline_code_ignored(self, tmp_path: Path) -> None:
        body = "Use `[label](#nope)` literal syntax.\n"
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "broken-cross-link" not in _codes(validate_md(path))


class TestIDUniqueness:
    def test_duplicate_queue_id(self, tmp_path: Path) -> None:
        body = (
            "<!-- @anchor: queue -->\n"
            "## Queue\n\n"
            "| ID | Topic |\n"
            "|---|---|\n"
            "| Q-001 | a |\n"
            "| Q-001 | b |\n\n"
            "<!-- @end: queue -->\n"
        )
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "duplicate-queue-id" in _codes(validate_md(path))

    def test_duplicate_tracker_id(self, tmp_path: Path) -> None:
        body = (
            "<!-- @anchor: tracker -->\n"
            "## Tracker\n\n"
            "| ID | Topic |\n"
            "|---|---|\n"
            "| Q-002 | a |\n"
            "| Q-002 | b |\n\n"
            "<!-- @end: tracker -->\n"
        )
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "duplicate-tracker-id" in _codes(validate_md(path))

    def test_id_in_both_queue_and_tracker(self, tmp_path: Path) -> None:
        body = (
            "<!-- @anchor: queue -->\n## Queue\n\n"
            "| ID | Topic |\n|---|---|\n| Q-003 | a |\n\n"
            "<!-- @end: queue -->\n\n"
            "<!-- @anchor: tracker -->\n## Tracker\n\n"
            "| ID | Topic |\n|---|---|\n| Q-003 | a |\n\n"
            "<!-- @end: tracker -->\n"
        )
        path = _write(tmp_path / "demo_v1.0.md", _project_doc(body))
        assert "id-in-queue-and-tracker" in _codes(validate_md(path))


class TestPriorMode:
    def _make_pair(self, tmp_path: Path, prior_body: str, new_body: str) -> tuple[Path, Path]:
        prior = _write(tmp_path / "demo_v1.0.md", _project_doc(prior_body))
        new = _write(tmp_path / "demo_v1.1.md", _project_doc(new_body))
        return new, prior

    def test_anchor_preserved_passes(self, tmp_path: Path) -> None:
        body = "<!-- @anchor: foo -->\nx\n<!-- @end: foo -->\n"
        new, prior = self._make_pair(tmp_path, body, body)
        assert "anchor-removed" not in _codes(validate_md(new, prior))

    def test_anchor_removed_errors(self, tmp_path: Path) -> None:
        prior_body = "<!-- @anchor: foo -->\nx\n<!-- @end: foo -->\n"
        new_body = "no anchors here\n"
        new, prior = self._make_pair(tmp_path, prior_body, new_body)
        assert "anchor-removed" in _codes(validate_md(new, prior))

    def test_da_removed_errors(self, tmp_path: Path) -> None:
        prior_body = '<!-- @da: DA-Q1-1 -->\n<a id="da-q1-1"></a>\n\n**DA-Q1-1.** x\n'
        new_body = "no DAs\n"
        new, prior = self._make_pair(tmp_path, prior_body, new_body)
        assert "da-removed" in _codes(validate_md(new, prior))

    def test_changelog_entry_removed_errors(self, tmp_path: Path) -> None:
        prior_body = (
            "<!-- @anchor: changelog -->\n## Changelog\n\n### v1.0\n\nfirst\n\n"
            "<!-- @end: changelog -->\n"
        )
        new_body = (
            "<!-- @anchor: changelog -->\n## Changelog\n\n### v1.1\n\nsecond\n\n"
            "<!-- @end: changelog -->\n"
        )
        new, prior = self._make_pair(tmp_path, prior_body, new_body)
        assert "changelog-entry-removed" in _codes(validate_md(new, prior))


class TestStarterFile:
    def test_bundled_starter_md_validates_clean(self) -> None:
        from importlib import resources

        starter_path = Path(str(resources.files("research_buddy") / "starter.md"))
        assert starter_path.is_file()
        issues = validate_md(starter_path)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == [], (
            "bundled starter.md must pass all mechanical checks at error level; "
            f"found: {[i.format() for i in errors]}"
        )
