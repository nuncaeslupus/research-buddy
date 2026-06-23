"""Tests for `research_buddy.turn1` and the `turn1` command."""

from __future__ import annotations

import argparse
import re
from importlib import resources
from pathlib import Path

import pytest

import research_buddy
from research_buddy.commands.turn1 import cmd_turn1
from research_buddy.turn1 import (
    BRIEF_END,
    BRIEF_START,
    Turn1Error,
    build_brief_skeleton,
    first_queue_row,
)

_FM = """\
---
doc_format_version: 2
research_buddy_version: "1.0.0"
agent_state: ready
version: "1.2"
date: "2026-06-08"
file_name: "demo"
title: "Demo"
language:
  code: es
  label: Español
project:
  domain: "optimización de prompts"
  deliverable_type: document
  final_goal: "reglas validadas"
  source_tiers:
    tier_1: "arXiv/ACL"
    tier_2: "docs oficiales"
    discovery: "blogs"
  domain_rules: null
---
"""

_QUEUE = """\
<!-- @anchor: queue -->
## Open Research Queue

| ID | Topic | Objective / Key Question |
|----|-------|--------------------------|
| Q-003 | Auto-chequeo negativo | ¿Qué formulación reduce los saltos? |
| Q-004 | Otra cosa | ¿Algo más? |

<!--
| Q-EX1 | ejemplo en comentario | no debe aparecer |
-->

<!-- @end: queue -->
"""


def _doc(fm: str = _FM, queue: str = _QUEUE) -> str:
    return fm + "\n" + queue


class TestFirstQueueRow:
    def test_returns_first_live_row(self) -> None:
        row = first_queue_row(_doc())
        assert row == ("Q-003", "Auto-chequeo negativo", "¿Qué formulación reduce los saltos?")

    def test_skips_example_rows_in_comments(self) -> None:
        # The Q-EX1 row lives inside an HTML comment and must never be picked.
        _, topic, _ = first_queue_row(_doc()) or ("", "", "")
        assert "ejemplo" not in topic

    def test_returns_none_when_no_live_rows(self) -> None:
        empty_queue = (
            "<!-- @anchor: queue -->\n## Open Research Queue\n\n"
            "| ID | Topic | Objective / Key Question |\n"
            "|----|-------|------|\n\n<!-- @end: queue -->\n"
        )
        assert first_queue_row(_FM + "\n" + empty_queue) is None

    def test_returns_none_when_no_queue_section(self) -> None:
        assert first_queue_row(_FM + "\n# nothing here\n") is None


class TestBuildBriefSkeleton:
    def test_wrapped_in_markers(self) -> None:
        brief, _ = build_brief_skeleton(_doc())
        assert brief.startswith(BRIEF_START)
        assert brief.rstrip().endswith(BRIEF_END)

    def test_prefills_project_topic_questions_and_tiers(self) -> None:
        brief, notes = build_brief_skeleton(_doc())
        assert "optimización de prompts" in brief
        assert "deliverable: document" in brief
        assert "Auto-chequeo negativo" in brief
        assert "¿Qué formulación reduce los saltos?" in brief
        assert "arXiv/ACL" in brief
        assert "docs oficiales" in brief
        # the fixed Never tier is filled in verbatim
        assert "without traceable authorship" in brief
        assert any("Q-003" in n for n in notes)

    def test_leaves_judgement_slots_as_placeholders(self) -> None:
        brief, _ = build_brief_skeleton(_doc())
        for ph in (
            "{{RELEVANT_DISCARDED_ALTERNATIVES}}",
            "{{RELATED_PRIOR_TRACKER_ROWS}}",
            "{{ACTIVE_CONSTRAINING_RULES}}",
            "{{PRE_REGISTERED_HYPOTHESES_BY_NAME_ONLY}}",
            "{{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}",
        ):
            assert ph in brief

    def test_no_finding_leakage_markers(self) -> None:
        # The brief must not contain Turn-1 findings; the skeleton certainly
        # shouldn't invent VALIDATED/REJECTED verdicts.
        brief, _ = build_brief_skeleton(_doc())
        assert "VALIDATED:" not in brief

    def test_empty_queue_uses_topic_placeholders_and_warns(self) -> None:
        empty_queue = (
            "<!-- @anchor: queue -->\n## Open Research Queue\n\n"
            "| ID | Topic | Objective / Key Question |\n"
            "|----|-------|------|\n\n<!-- @end: queue -->\n"
        )
        brief, notes = build_brief_skeleton(_FM + "\n" + empty_queue)
        assert "{{RESEARCH_TOPIC_IN_CONTEXT}}" in brief
        assert "{{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}" in brief
        assert any("no live row" in n for n in notes)

    def test_missing_tiers_fall_back_to_placeholder(self) -> None:
        fm = _FM.replace('tier_1: "arXiv/ACL"', "tier_1: null").replace(
            'tier_2: "docs oficiales"', "tier_2: null"
        )
        brief, _ = build_brief_skeleton(_doc(fm=fm))
        assert "{{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}" in brief

    def test_starter_file_raises(self) -> None:
        starter_fm = _FM.replace('domain: "optimización de prompts"', "domain: null")
        with pytest.raises(Turn1Error, match="starter file"):
            build_brief_skeleton(_doc(fm=starter_fm))

    def test_missing_frontmatter_raises(self) -> None:
        with pytest.raises(Turn1Error, match="frontmatter"):
            build_brief_skeleton("# no frontmatter\n")

    def test_malformed_project_raises_clean_error_not_attributeerror(self) -> None:
        # `project` parsed as a string (malformed YAML) must not crash with
        # AttributeError on `.get()` — surface a clean Turn1Error instead.
        bad = "---\ndoc_format_version: 2\nproject: oops-a-string\n---\n\n# body\n"
        with pytest.raises(Turn1Error):
            build_brief_skeleton(bad)

    def test_helpers_tolerate_non_dict_sections(self) -> None:
        from research_buddy.turn1 import _accepted_sources, _project_description

        assert _project_description({"project": "oops"}) == "{{PROJECT_AND_BASIC_CHARACTERISTICS}}"
        assert (
            _accepted_sources({"project": {"source_tiers": "oops"}})
            == "{{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}"
        )


class TestCmdTurn1:
    def _write(self, tmp_path: Path, text: str, name: str = "demo_v1.2-source.md") -> Path:
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_prints_brief_and_returns_zero(self, tmp_path: Path, capsys) -> None:
        path = self._write(tmp_path, _doc())
        rc = cmd_turn1(argparse.Namespace(path=str(path)))
        out = capsys.readouterr()
        assert rc == 0
        assert BRIEF_START in out.out
        assert "Auto-chequeo negativo" in out.out
        # guidance goes to stderr, not the copy-paste block
        assert BRIEF_START not in out.err
        assert "Q-003" in out.err

    def test_rejects_non_md(self, tmp_path: Path) -> None:
        p = tmp_path / "demo.json"
        p.write_text("{}", encoding="utf-8")
        assert cmd_turn1(argparse.Namespace(path=str(p))) == 2

    def test_missing_file_returns_two(self, tmp_path: Path) -> None:
        assert cmd_turn1(argparse.Namespace(path=str(tmp_path / "nope.md"))) == 2

    def test_starter_file_returns_two(self, tmp_path: Path, capsys) -> None:
        starter_fm = _FM.replace('domain: "optimización de prompts"', "domain: null")
        path = self._write(tmp_path, _doc(fm=starter_fm))
        rc = cmd_turn1(argparse.Namespace(path=str(path)))
        assert rc == 2
        assert "starter file" in capsys.readouterr().err


class TestBriefSkeletonSyncWithCanonicalTemplate:
    """PR-4 sync guard: turn1 output must stay structurally consistent with the
    canonical brief template in starter.md (framework.reference.brief)."""

    def _canonical_template(self) -> str:
        starter = resources.files(research_buddy).joinpath("starter.md").read_text(encoding="utf-8")
        m = re.search(
            r"<!-- @anchor: framework\.reference\.brief -->.*?```text\n(.*?)```",
            starter,
            re.DOTALL,
        )
        assert m, "canonical brief template not found in starter.md"
        return m.group(1)

    def test_static_prose_lines_appear_in_brief_output(self) -> None:
        canonical = self._canonical_template()
        # Lines with no placeholders and no blank — the structural prose.
        static_lines = [
            ln for ln in canonical.splitlines() if ln.strip() and "{{" not in ln and "}}" not in ln
        ]
        assert static_lines, "no static prose lines found in canonical template"

        # Build a maximally-unfilled brief (no tiers, no queue).
        fm_no_tiers = _FM.replace('tier_1: "arXiv/ACL"', "tier_1: null").replace(
            'tier_2: "docs oficiales"', "tier_2: null"
        )
        empty_queue = (
            "<!-- @anchor: queue -->\n## Open Research Queue\n\n"
            "| ID | Topic | Objective / Key Question |\n"
            "|----|-------|------|\n\n<!-- @end: queue -->\n"
        )
        brief, _ = build_brief_skeleton(fm_no_tiers + "\n" + empty_queue)

        for ln in static_lines:
            assert ln in brief, (
                f"structural prose from canonical template missing in turn1 output:\n  {ln!r}"
            )

    def test_placeholder_names_in_turn1_source_match_canonical(self) -> None:
        import inspect

        import research_buddy.turn1 as turn1_mod

        canonical = self._canonical_template()
        canonical_phs = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", canonical))

        # TIER_REJECT_RULES is pre-filled in turn1 with the literal Never-tier text
        # (it is never emitted as a placeholder). All others must appear as string
        # literals in turn1.py — either as the placeholder fallback or in the body.
        expected_in_src = canonical_phs - {"TIER_REJECT_RULES"}

        src = inspect.getsource(turn1_mod)
        for ph in expected_in_src:
            assert ph in src, (
                f"placeholder {{{{{ph}}}}} from the canonical template in starter.md "
                "is not referenced in turn1.py — names have diverged"
            )


class TestCompleteState:
    """agent_state: complete raises Turn1Error before attempting to build a brief."""

    def _complete_fm(self) -> str:
        return _FM.replace("agent_state: ready", "agent_state: complete")

    def test_complete_state_raises_turn1_error(self) -> None:
        text = self._complete_fm() + "\n" + _QUEUE
        with pytest.raises(Turn1Error) as exc_info:
            build_brief_skeleton(text)
        assert "complete" in str(exc_info.value).lower()

    def test_complete_state_error_message_mentions_remedy(self) -> None:
        text = self._complete_fm() + "\n" + _QUEUE
        with pytest.raises(Turn1Error) as exc_info:
            build_brief_skeleton(text)
        assert "agent_state: ready" in str(exc_info.value)

    def test_complete_state_cmd_returns_nonzero(self, tmp_path: Path) -> None:
        md = tmp_path / "demo_v1.2-source.md"
        md.write_text(self._complete_fm() + "\n" + _QUEUE, encoding="utf-8")
        args = argparse.Namespace(path=str(md))
        assert cmd_turn1(args) == 2
