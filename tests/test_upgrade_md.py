"""Tests for the v2 Markdown upgrade path."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from research_buddy import __version__
from research_buddy.upgrade_md import (
    FRAMEWORK_END,
    FRAMEWORK_START,
    UpgradeError,
    upgrade_md,
)


def _starter_text() -> str:
    """Read the bundled v2 starter.md text."""
    ref = resources.files("research_buddy") / "starter.md"
    with ref.open("r", encoding="utf-8") as f:
        return f.read()


def _replace_framework(starter: str, replacement_body: str) -> str:
    """Swap the framework block of `starter` with the given body, keeping the
    boundary markers. Used to build "stale" source files for tests."""
    lines = starter.splitlines()
    start = end = -1
    for i, line in enumerate(lines):
        if line.strip() == FRAMEWORK_START and start < 0:
            start = i
        elif line.strip() == FRAMEWORK_END:
            end = i
    new_lines = [
        *lines[: start + 1],
        "",
        *replacement_body.splitlines(),
        "",
        *lines[end:],
    ]
    return "\n".join(new_lines) + "\n"


class TestFrameworkBlockReplacement:
    def test_idempotent_when_already_in_sync(self) -> None:
        starter = _starter_text()
        upgraded, changes = upgrade_md(starter, starter, __version__)
        assert changes == []
        assert upgraded == starter

    def test_swaps_stale_framework_block(self) -> None:
        starter = _starter_text()
        stale = _replace_framework(starter, "## Old framework block — to be replaced.")
        assert "Old framework block" in stale

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert "framework block ← starter.md" in changes
        assert "Old framework block" not in upgraded
        # Markers are preserved
        assert FRAMEWORK_START in upgraded
        assert FRAMEWORK_END in upgraded

    def test_preserves_body_below_framework(self) -> None:
        starter = _starter_text()
        stale = _replace_framework(starter, "## Stale.")
        # Inject a project-specific marker into the body (after the framework
        # block, in the project specification area which is project-owned).
        marker = "PROJECT-OWNED-CANARY-LINE-XYZ"
        stale = stale.replace("## Project Specification", f"## Project Specification\n\n{marker}\n")
        upgraded, _ = upgrade_md(stale, starter, __version__)
        assert marker in upgraded

    def test_missing_framework_start_raises(self) -> None:
        starter = _starter_text()
        # Strip the start marker line entirely.
        broken = starter.replace(FRAMEWORK_START + "\n", "")
        with pytest.raises(UpgradeError, match=r"missing.*framework\.core"):
            upgrade_md(broken, starter, __version__)

    def test_missing_framework_end_raises(self) -> None:
        starter = _starter_text()
        broken = starter.replace(FRAMEWORK_END + "\n", "")
        with pytest.raises(UpgradeError, match=r"missing.*framework\.reference"):
            upgrade_md(broken, starter, __version__)

    def test_ignores_marker_lines_inside_fenced_code_blocks(self) -> None:
        """A fenced code example showing the marker lines must not shadow the
        real boundaries. Without fence-skipping, the bogus FRAMEWORK_END inside
        the fence (which appears AFTER the real one in the file) would win
        because end-detection takes the last match."""
        starter = _starter_text()
        stale = _replace_framework(starter, "## Old framework block.")
        bogus_fence = f"\n```\n{FRAMEWORK_START}\nfake content\n{FRAMEWORK_END}\n```\n"
        stale_with_fence = stale + bogus_fence

        upgraded, changes = upgrade_md(stale_with_fence, starter, __version__)
        assert "framework block ← starter.md" in changes
        assert "Old framework block" not in upgraded
        # The bogus fence and its contents must be preserved verbatim — the
        # upgrader treated those marker lines as inert prose.
        assert bogus_fence.rstrip("\n") in upgraded


class TestFrontmatterMigration:
    def test_renames_legacy_format_version_key(self) -> None:
        starter = _starter_text()
        # Build a stale source: replace `doc_format_version: 2` with the
        # legacy key `format_version: 2`.
        stale = starter.replace("doc_format_version: 2", "format_version: 2", 1)
        assert "format_version: 2" in stale
        assert "doc_format_version: 2" not in stale

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert "format_version → doc_format_version" in changes
        assert "doc_format_version: 2" in upgraded
        # No frontmatter line begins with the legacy key anymore.
        fm_block = upgraded.split("\n---\n", 2)[0]
        for line in fm_block.splitlines():
            assert not line.startswith("format_version:"), line
        assert "doc_format_version: 2" in fm_block

    def test_bumps_research_buddy_version(self) -> None:
        starter = _starter_text()
        stale = starter.replace(
            f'research_buddy_version: "{__version__}"',
            'research_buddy_version: "0.0.1"',
            1,
        )
        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert any(c.startswith("research_buddy_version:") for c in changes)
        assert f'research_buddy_version: "{__version__}"' in upgraded

    def test_no_op_when_version_already_current(self) -> None:
        starter = _starter_text()
        # The starter is by definition at the current tool version — no
        # version-related change should fire.
        _, changes = upgrade_md(starter, starter, __version__)
        assert not any(c.startswith("research_buddy_version:") for c in changes)

    def test_inserts_missing_project_source_tiers(self) -> None:
        starter = _starter_text()
        # Strip the source_tiers block from the source; keep everything else.
        stale_lines = []
        skip = False
        for line in starter.splitlines():
            if line.startswith("  source_tiers:"):
                skip = True
                continue
            if skip and line.startswith("    "):
                continue
            skip = False
            stale_lines.append(line)
        stale = "\n".join(stale_lines) + "\n"
        assert "source_tiers" not in stale.split("\n---\n", 2)[0]

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert any("source_tiers added" in c for c in changes)
        fm_block = upgraded.split("\n---\n", 2)[0]
        assert "source_tiers:" in fm_block
        assert "tier_1:" in fm_block
        assert "tier_2:" in fm_block
        assert "discovery:" in fm_block

    def test_inserts_missing_agent_state(self) -> None:
        starter = _starter_text()
        # Simulate a pre-1.9 doc by stripping the agent_state line entirely.
        stale_lines = [line for line in starter.splitlines() if not line.startswith("agent_state:")]
        stale = "\n".join(stale_lines) + "\n"
        assert "agent_state" not in stale.split("\n---\n", 2)[0]

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert any("agent_state added" in c for c in changes)
        fm_block = upgraded.split("\n---\n", 2)[0]
        assert "agent_state: ready" in fm_block
        # Backfill value MUST be `ready`, not `needs_session_zero` — by the
        # time a doc is being upgraded, session zero is necessarily complete.
        assert "agent_state: needs_session_zero" not in fm_block

    def test_inserts_missing_project_domain_rules(self) -> None:
        starter = _starter_text()
        stale = starter.replace("  domain_rules: null", "", 1).replace("  domain_rules:", "", 1)
        # Strip any line that contained domain_rules; we only care that the
        # key is gone.
        stale_lines = [line for line in stale.splitlines() if "domain_rules" not in line]
        stale = "\n".join(stale_lines) + "\n"
        assert "domain_rules" not in stale.split("\n---\n", 2)[0]

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert any("domain_rules added" in c for c in changes)
        fm_block = upgraded.split("\n---\n", 2)[0]
        assert "domain_rules:" in fm_block

    def test_preserves_filled_in_user_values(self) -> None:
        starter = _starter_text()
        # Simulate a user who filled in the project metadata.
        filled = (
            starter.replace("title: null", 'title: "My Project"', 1)
            .replace("domain: null", 'domain: "machine learning"', 1)
            .replace("file_name: null", 'file_name: "my-project"', 1)
        )
        # Force a framework refresh by staling the framework block.
        stale = _replace_framework(filled, "## Stale.")
        upgraded, _ = upgrade_md(stale, starter, __version__)
        fm_block = upgraded.split("\n---\n", 2)[0]
        assert 'title: "My Project"' in fm_block
        assert 'domain: "machine learning"' in fm_block
        assert 'file_name: "my-project"' in fm_block

    def test_missing_frontmatter_raises(self) -> None:
        starter = _starter_text()
        with pytest.raises(UpgradeError, match="frontmatter"):
            upgrade_md("# Just a body\n\nNo frontmatter here.\n", starter, __version__)

    def test_wrong_doc_format_version_raises(self) -> None:
        starter = _starter_text()
        stale = starter.replace("doc_format_version: 2", "doc_format_version: 1", 1)
        with pytest.raises(UpgradeError, match="doc_format_version"):
            upgrade_md(stale, starter, __version__)

    def test_doc_ahead_of_tool_raises(self) -> None:
        """A doc stamped with a future research_buddy_version refuses downgrade.

        The field is sometimes used as 'framework version this doc was authored
        against' — silently rolling it back would lose user intent. Force the
        user to choose between upgrading the tool and manually editing the doc.
        """
        starter = _starter_text()
        ahead = starter.replace(
            f'research_buddy_version: "{__version__}"',
            'research_buddy_version: "99.0.0"',
            1,
        )
        with pytest.raises(UpgradeError, match="AHEAD of the tool"):
            upgrade_md(ahead, starter, __version__)


class TestPreambleReplacement:
    """The operating-manual HTML comment between frontmatter and the first
    @anchor is template-owned and refreshed on upgrade."""

    def _replace_preamble(self, starter: str, body: str) -> str:
        """Swap the preamble (everything between frontmatter close and the
        first `<!-- @anchor:` line) with `body`."""
        lines = starter.splitlines()
        fm_close = -1
        for i in range(1, len(lines)):
            if lines[i].rstrip() == "---":
                fm_close = i
                break
        anchor = -1
        for i in range(fm_close + 1, len(lines)):
            if lines[i].lstrip().startswith("<!-- @anchor:"):
                anchor = i
                break
        new_lines = [*lines[: fm_close + 1], "", body, "", *lines[anchor:]]
        return "\n".join(new_lines) + "\n"

    def test_swaps_stale_preamble(self) -> None:
        starter = _starter_text()
        stale = self._replace_preamble(starter, "<!-- OLD PREAMBLE -->")
        assert "OLD PREAMBLE" in stale

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert "preamble ← starter.md" in changes
        assert "OLD PREAMBLE" not in upgraded
        # Starter's preamble landmark is present.
        assert "DO NOT CALL ANY TOOL" in upgraded

    def test_idempotent_when_preamble_already_in_sync(self) -> None:
        starter = _starter_text()
        _, changes = upgrade_md(starter, starter, __version__)
        assert "preamble ← starter.md" not in changes

    def test_missing_anchor_after_frontmatter_raises(self) -> None:
        starter = _starter_text()
        # Strip every @anchor line — nothing for the preamble to bound against.
        broken = "\n".join(line for line in starter.splitlines() if "<!-- @anchor:" not in line)
        with pytest.raises(UpgradeError, match=r"no `<!-- @anchor:"):
            upgrade_md(broken, starter, __version__)


class TestAgentReminderRefresh:
    """The visible `> **Agent: ...` blockquote inside the title block is
    template-owned and refreshed on upgrade."""

    def test_swaps_stale_blockquote(self) -> None:
        starter = _starter_text()
        # Find the blockquote line in the starter and produce a stale version.
        star_line = next(line for line in starter.splitlines() if line.startswith("> **Agent:"))
        stale = starter.replace(star_line, "> **Agent: old reminder text.**", 1)
        assert "old reminder text" in stale

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert "agent-reminder blockquote ← starter.md" in changes
        assert "old reminder text" not in upgraded
        assert star_line in upgraded

    def test_idempotent_when_blockquote_in_sync(self) -> None:
        starter = _starter_text()
        _, changes = upgrade_md(starter, starter, __version__)
        assert "agent-reminder blockquote ← starter.md" not in changes

    def test_no_op_when_source_has_no_blockquote(self) -> None:
        starter = _starter_text()
        star_line = next(line for line in starter.splitlines() if line.startswith("> **Agent:"))
        # Drop the blockquote line entirely. Older docs may predate it.
        no_blockquote = starter.replace(star_line + "\n", "")
        upgraded, changes = upgrade_md(no_blockquote, starter, __version__)
        # No blockquote change applied; preamble/framework may still be in sync.
        assert "agent-reminder blockquote ← starter.md" not in changes
        assert star_line not in upgraded

    def test_replaces_multi_line_blockquote_without_orphans(self) -> None:
        """If a source doc has a wrapped/multi-line blockquote, the entire
        contiguous block is replaced — no continuation lines orphaned."""
        starter = _starter_text()
        star_line = next(line for line in starter.splitlines() if line.startswith("> **Agent:"))
        wrapped = (
            "> **Agent: OLD reminder text line one.**\n"
            "> wrapped continuation line two.\n"
            "> wrapped continuation line three."
        )
        stale = starter.replace(star_line, wrapped, 1)
        assert "wrapped continuation line three" in stale

        upgraded, changes = upgrade_md(stale, starter, __version__)
        assert "agent-reminder blockquote ← starter.md" in changes
        # None of the wrapped continuation lines survive as orphans.
        assert "wrapped continuation line two" not in upgraded
        assert "wrapped continuation line three" not in upgraded
        assert "OLD reminder text line one" not in upgraded
        # Starter's single-line blockquote is present.
        assert star_line in upgraded


class TestCli:
    def test_md_upgrade_dry_run(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        starter = _starter_text()
        stale = _replace_framework(starter, "## Stale framework.")
        target = tmp_path / "doc_v1.0-source.md"
        target.write_text(stale, encoding="utf-8")

        class _Args:
            def __init__(self) -> None:
                self.paths = [str(target)]
                self.apply = False
                self.no_validate = True

        rc = cmd_upgrade(_Args())
        # Dry-run with changes returns 1 per per-file convention.
        assert rc == 1
        # File untouched.
        assert "## Stale framework." in target.read_text(encoding="utf-8")

    def test_md_upgrade_apply_writes(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        starter = _starter_text()
        stale = _replace_framework(starter, "## Stale framework.")
        target = tmp_path / "doc_v1.0-source.md"
        target.write_text(stale, encoding="utf-8")

        class _Args:
            def __init__(self) -> None:
                self.paths = [str(target)]
                self.apply = True
                self.no_validate = True

        rc = cmd_upgrade(_Args())
        # Apply with changes and validation skipped → 0.
        assert rc == 0
        upgraded = target.read_text(encoding="utf-8")
        assert "## Stale framework." not in upgraded
        assert FRAMEWORK_START in upgraded
        assert FRAMEWORK_END in upgraded

    def test_md_upgrade_idempotent_apply(self, tmp_path: Path) -> None:
        from research_buddy.main import cmd_upgrade

        starter = _starter_text()
        target = tmp_path / "doc_v1.0-source.md"
        target.write_text(starter, encoding="utf-8")

        class _Args:
            def __init__(self) -> None:
                self.paths = [str(target)]
                self.apply = True
                self.no_validate = True

        rc = cmd_upgrade(_Args())
        assert rc == 0
        # File unchanged on a no-op.
        assert target.read_text(encoding="utf-8") == starter
