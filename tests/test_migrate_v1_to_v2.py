"""Tests for `research_buddy.migrate_v1_to_v2` — v1 JSON → v2 MD source converter."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from research_buddy import __version__
from research_buddy.migrate_v1_to_v2 import (
    _dropped_research_sections,
    _render_verdict_as_da,
    _render_verdict_as_rule,
    _strip_done_rows_from_queue,
    _tracker_ids,
    build_changelog,
    build_domain_tab,
    build_frontmatter,
    build_overview_tab,
    derive_output_path,
    load_framework_block_from_starter,
    main,
    migrate,
    parse_rule_label,
    render_block,
    render_blocks,
    render_subsections,
    resolve_language,
    resolve_project_spec,
)
from research_buddy.validator_md import validate_md


class TestFrontmatterBuild:
    def test_includes_required_fields(self, starter_doc: dict) -> None:
        fm_text = build_frontmatter(starter_doc)
        assert fm_text.startswith("---\n")
        assert fm_text.endswith("---")
        body = fm_text[4:-3]
        fm = yaml.safe_load(body)
        assert fm["doc_format_version"] == 2
        assert fm["research_buddy_version"] == __version__
        assert "language" in fm
        assert "project" in fm
        assert "ui_strings" in fm

    def test_research_buddy_version_sourced_from_package(self, starter_doc: dict) -> None:
        # Even if the source doc had a different rb_version, the migration
        # stamps the current installed version.
        doc = copy.deepcopy(starter_doc)
        doc["meta"]["research_buddy_version"] = "0.0.1"
        fm = yaml.safe_load(build_frontmatter(doc)[4:-3])
        assert fm["research_buddy_version"] == __version__

    def test_version_int_normalized(self) -> None:
        doc = {"meta": {"version": 1}}
        fm = yaml.safe_load(build_frontmatter(doc)[4:-3])
        assert fm["version"] == "1.0"

    def test_version_float_normalized(self) -> None:
        doc = {"meta": {"version": 1.5}}
        fm = yaml.safe_load(build_frontmatter(doc)[4:-3])
        assert fm["version"] == "1.5"

    def test_version_string_passthrough(self) -> None:
        doc = {"meta": {"version": "2.3"}}
        fm = yaml.safe_load(build_frontmatter(doc)[4:-3])
        assert fm["version"] == "2.3"

    def test_file_name_strips_json_and_version_suffix(self) -> None:
        doc = {"meta": {"file_name": "my-research_v1_14.json", "version": "1.14"}}
        fm = yaml.safe_load(build_frontmatter(doc)[4:-3])
        assert fm["file_name"] == "my-research"

    def test_starter_placeholder_passes_through(self, starter_doc: dict) -> None:
        # The v1 starter uses [FILL: ...] placeholder strings (not nulls).
        # The migrator should pass them through verbatim — the agent (or
        # session zero) replaces them with real values later.
        fm = yaml.safe_load(build_frontmatter(starter_doc)[4:-3])
        assert isinstance(fm["project"]["domain"], str)
        assert "FILL" in fm["project"]["domain"]


class TestFrameworkInjection:
    def test_loads_framework_from_bundled_starter(self) -> None:
        block = load_framework_block_from_starter()
        assert "<!-- @anchor: framework.core -->" in block
        assert "<!-- @end: framework.reference -->" in block

    def test_migrate_includes_framework_block(self, starter_doc: dict) -> None:
        out = migrate(starter_doc)
        assert "<!-- @anchor: framework.core -->" in out
        assert "<!-- @end: framework.reference -->" in out

    def test_load_raises_when_starter_missing_anchors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Replace the bundled starter loader with one that returns a body
        # without the framework markers, and verify load_* raises.
        from research_buddy import migrate_v1_to_v2 as mod

        class FakeRef:
            def read_text(self, encoding: str = "utf-8") -> str:
                return "no framework markers here\n"

        class FakePkg:
            def __truediv__(self, other: str) -> FakeRef:
                return FakeRef()

        def fake_files(_: str) -> FakePkg:
            return FakePkg()

        monkeypatch.setattr(mod.resources, "files", fake_files)
        with pytest.raises(RuntimeError, match="framework anchors"):
            load_framework_block_from_starter()


class TestRuleLabelParsing:
    def test_basic_rule(self) -> None:
        out = parse_rule_label("R-FM-1 [skill][portable] VALIDATED — pre-registered")
        assert out["id"] == "R-FM-1"
        assert out["tags"] == ["skill", "portable"]
        assert out["status"] == "VALIDATED"
        assert "pre-registered" in out["extras"]

    def test_da_label(self) -> None:
        out = parse_rule_label("DA-Q1-1 [reject] reasoning")
        assert out["id"] == "DA-Q1-1"
        assert out["tags"] == ["reject"]

    def test_unparseable_falls_back(self) -> None:
        out = parse_rule_label("free-form text")
        assert out["id"] == "free-form text"
        assert out["tags"] == []


class TestSectionMapping:
    def test_verdict_adopt_renders_as_rule(self) -> None:
        block = {
            "type": "verdict",
            "badge": "adopt",
            "label": "R-FM-1 VALIDATED — pre-registered",
            "md": "Body text.",
        }
        out = render_block(block)
        assert "<!-- @rule: R-FM-1 -->" in out
        assert '<a id="r-fm-1"></a>' in out
        assert "Body text." in out

    def test_verdict_reject_renders_as_da(self) -> None:
        block = {
            "type": "verdict",
            "badge": "reject",
            "label": "DA-Q1-1 reason",
            "md": "Why we rejected.",
        }
        out = render_block(block)
        assert "<!-- @da: DA-Q1-1 -->" in out
        assert '<a id="da-q1-1"></a>' in out

    def test_research_sections_become_top_level_h2s(self, starter_doc: dict) -> None:
        out = migrate(starter_doc)
        # Always produced by the migrator from the research tab:
        for h2 in (
            "## Open Research Queue",
            "## Research Tracker",
            "## Discarded Alternatives",
            "## Reasoning Journey",
            "## References",
            "## Session Notes",
            "## Changelog",
        ):
            assert h2 in out, f"missing top-level heading: {h2}"

    def test_project_specification_present(self, starter_doc: dict) -> None:
        out = migrate(starter_doc)
        assert "## Project Specification" in out

    def test_table_block_renders_pipe_table(self) -> None:
        out = render_block({"type": "table", "headers": ["A", "B"], "rows": [["1", "2"]]})
        assert "| A | B |" in out
        assert "|---|---|" in out
        assert "| 1 | 2 |" in out

    def test_paragraph_alias_renders_like_p(self) -> None:
        assert render_block({"type": "paragraph", "md": "Body."}) == "Body."


class TestRichBlockMapping:
    """v1 rich blocks must keep their chrome, not flatten to prose."""

    def test_svg_renders_verbatim(self) -> None:
        svg = '<svg viewbox="0 0 10 10"><rect x="0" y="0" width="5" height="5"></rect></svg>'
        out = render_block({"type": "svg", "html": svg})
        assert out == svg

    def test_svg_collapses_internal_blank_lines(self) -> None:
        # A blank line would split the CommonMark HTML block and truncate the
        # passthrough, so they must be removed.
        out = render_block({"type": "svg", "html": "<svg>\n\n<rect></rect>\n</svg>"})
        assert "\n\n" not in out
        assert "<rect></rect>" in out

    def test_empty_svg_drops(self) -> None:
        assert render_block({"type": "svg", "html": ""}) == ""

    def test_card_grid_becomes_rb_cards(self) -> None:
        out = render_block(
            {
                "type": "card_grid",
                "cards": [
                    {"title": "Research Tab", "md": "New ideas start here."},
                    {"title": "Theory Tab", "md": "Derivations live here."},
                ],
            }
        )
        assert out.startswith("```rb-cards")
        assert "title: Research Tab" in out
        assert "New ideas start here." in out

    def test_phase_cards_items_become_bullets(self) -> None:
        out = render_block(
            {
                "type": "phase_cards",
                "cards": [{"phase": "p1", "title": "Phase 1", "items": ["GPU", "RAM"]}],
            }
        )
        assert out.startswith("```rb-cards")
        assert "title: Phase 1" in out
        assert "- GPU" in out and "- RAM" in out

    def test_agnostic_banner_becomes_rb_banner(self) -> None:
        out = render_block(
            {"type": "agnostic_banner", "title": "Crypto-Agnostic", "md": "Body text."}
        )
        assert out.startswith("```rb-banner agnostic")
        assert "title: Crypto-Agnostic" in out
        assert "Body text." in out

    def test_cc_banner_becomes_rb_banner(self) -> None:
        out = render_block({"type": "cc_banner", "title": "CC", "md": "Body."})
        assert out.startswith("```rb-banner cc")

    def test_usage_banner_becomes_rb_banner(self) -> None:
        out = render_block({"type": "usage_banner", "title": "How to use", "items": ["a", "b"]})
        assert out.startswith("```rb-banner usage")
        assert "- a" in out and "- b" in out

    @pytest.mark.parametrize(
        "blk",
        [
            {"type": "card_grid", "cards": None},
            {"type": "phase_cards", "cards": None},
            {"type": "svg", "html": None},
            {"type": "svg", "html": 123},
        ],
    )
    def test_null_or_mistyped_fields_do_not_raise(self, blk: dict) -> None:
        # `.get(key, [])` returns None for an explicit null, so iteration must be
        # guarded; non-string `html` must not reach `.strip()`.
        render_block(blk)

    @pytest.mark.parametrize(
        "blk",
        [
            {"type": "card_grid", "cards": [{"title": None, "md": None}]},
            {"type": "phase_cards", "cards": [{"title": None, "phase": None, "items": None}]},
            {"type": "agnostic_banner", "title": None, "md": None},
            {"type": "cc_banner", "title": None, "md": None},
            {"type": "usage_banner", "title": None, "items": None},
        ],
    )
    def test_null_titles_never_serialize_literal_none(self, blk: dict) -> None:
        # An explicit null value must fall back to "" — never the string "None".
        out = render_block(blk)
        assert "None" not in out

    def test_phase_cards_string_items_not_split_into_chars(self) -> None:
        out = render_block({"type": "phase_cards", "cards": [{"title": "P", "items": "GPU"}]})
        assert "- GPU" in out
        assert "- G\n" not in out


class TestSubsectionRecursion:
    """The v1 schema nests content under `section.subsections`; migration must
    render that tree instead of silently dropping it."""

    def test_subsection_blocks_are_rendered(self) -> None:
        sec = {
            "blocks": [],
            "subsections": {
                "Inner Topic": {
                    "blocks": [{"type": "p", "md": "Deep content survives."}],
                },
            },
        }
        out = render_subsections(sec, start_level=4)
        assert "#### Inner Topic" in out
        assert "Deep content survives." in out

    def test_nested_subsections_recurse_deeper(self) -> None:
        sec = {
            "subsections": {
                "Outer": {
                    "blocks": [{"type": "p", "md": "outer body"}],
                    "subsections": {
                        "Inner": {"blocks": [{"type": "p", "md": "inner body"}]},
                    },
                },
            },
        }
        out = render_subsections(sec, start_level=3)
        assert "### Outer" in out
        assert "#### Inner" in out
        assert "inner body" in out

    def test_private_subsections_skipped(self) -> None:
        sec = {"subsections": {"_meta": {"blocks": [{"type": "p", "md": "hidden"}]}}}
        assert render_subsections(sec, start_level=3) == ""

    @pytest.mark.parametrize("value", [None, [], "oops", 42])
    def test_non_dict_subsections_returns_empty(self, value: object) -> None:
        assert render_subsections({"subsections": value}, start_level=3) == ""

    def test_domain_tab_includes_subsection_svg(self) -> None:
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [
                {
                    "id": "design",
                    "label": "Design",
                    "sections": {
                        "System Architecture": {
                            "blocks": [],
                            "subsections": {
                                "Pipeline": {
                                    "blocks": [{"type": "svg", "html": "<svg><g></g></svg>"}],
                                },
                            },
                        },
                    },
                },
            ],
        }
        out = migrate(doc)
        assert "#### Pipeline" in out
        assert "<svg><g></g></svg>" in out


class TestEndToEnd:
    def test_round_trip_validates(self, starter_doc: dict, tmp_path: Path) -> None:
        # Promote starter to project mode so frontmatter null-checks pass.
        doc = copy.deepcopy(starter_doc)
        doc["meta"]["version"] = "1.0"
        doc["meta"]["date"] = "2026-05-07"
        doc["meta"]["file_name"] = "demo"
        doc["meta"]["title"] = "Demo Project"
        doc["agent_guidelines"]["project_specific"]["domain"] = "demo domain"
        doc["agent_guidelines"]["project_specific"]["deliverable_type"] = "document"
        doc["agent_guidelines"]["project_specific"]["final_goal"] = "ship"
        doc["agent_guidelines"]["project_specific"]["timing"] = "none"
        doc["agent_guidelines"]["project_specific"]["validation_gate"] = "n/a"

        out_text = migrate(doc)
        out_path = tmp_path / "demo_v1.0-source.md"
        out_path.write_text(out_text, encoding="utf-8")

        issues = validate_md(out_path)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == [], "migrate output must validate clean (no errors); found: " + "; ".join(
            f"{i.code}:{i.message}" for i in errors
        )


class TestOutputPath:
    def test_derives_filename_v_version(self, tmp_path: Path) -> None:
        doc = {"meta": {"file_name": "demo", "version": "1.0"}}
        out = derive_output_path(tmp_path / "input.json", doc)
        assert out.name == "demo_v1.0-source.md"
        assert out.parent == tmp_path

    def test_strips_v_suffix_in_file_name(self, tmp_path: Path) -> None:
        doc = {"meta": {"file_name": "demo_v1_14.json", "version": "1.14"}}
        out = derive_output_path(tmp_path / "x.json", doc)
        assert out.name == "demo_v1.14-source.md"

    def test_falls_back_to_input_stem(self, tmp_path: Path) -> None:
        doc = {"meta": {"version": "1.0"}}
        out = derive_output_path(tmp_path / "freeform.json", doc)
        assert out.name == "freeform_v1.0-source.md"


class TestCli:
    def _write_input(self, tmp_path: Path, doc: dict) -> Path:
        in_path = tmp_path / "in.json"
        in_path.write_text(json.dumps(doc), encoding="utf-8")
        return in_path

    def test_refuses_to_overwrite_without_force(self, starter_doc: dict, tmp_path: Path) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["meta"]["file_name"] = "demo"
        doc["meta"]["version"] = "1.0"
        in_path = self._write_input(tmp_path, doc)
        out_path = tmp_path / "out.md"
        out_path.write_text("existing\n", encoding="utf-8")

        rc = main([str(in_path), "-o", str(out_path)])
        assert rc == 2
        assert out_path.read_text(encoding="utf-8") == "existing\n"

    def test_force_overwrites(self, starter_doc: dict, tmp_path: Path) -> None:
        doc = copy.deepcopy(starter_doc)
        doc["meta"]["file_name"] = "demo"
        doc["meta"]["version"] = "1.0"
        in_path = self._write_input(tmp_path, doc)
        out_path = tmp_path / "out.md"
        out_path.write_text("existing\n", encoding="utf-8")

        rc = main([str(in_path), "-o", str(out_path), "--force"])
        assert rc == 0
        assert "doc_format_version: 2" in out_path.read_text(encoding="utf-8")

    def test_missing_input_returns_2(self, tmp_path: Path) -> None:
        rc = main([str(tmp_path / "does-not-exist.json")])
        assert rc == 2

    def test_invalid_json_returns_2(self, tmp_path: Path) -> None:
        in_path = tmp_path / "bad.json"
        in_path.write_text("{not json", encoding="utf-8")
        rc = main([str(in_path)])
        assert rc == 2


class TestLanguageCoercion:
    """Bug 1 — meta.language may be a bare string in older docs."""

    def test_string_language_does_not_crash(self) -> None:
        # Regression: `(meta.get("language") or {}).get(...)` crashed with
        # AttributeError when language was the string "English".
        doc = {"meta": {"version": "1.0", "language": "English"}}
        fm = yaml.safe_load(build_frontmatter(doc)[4:-3])
        assert fm["language"] == {"code": "en", "label": "English"}

    def test_object_language_preserved(self) -> None:
        meta = {"language": {"code": "es", "label": "Spanish"}}
        assert resolve_language(meta) == {"code": "es", "label": "Spanish"}

    def test_unknown_string_label_falls_back_to_und(self) -> None:
        assert resolve_language({"language": "Klingon"}) == {"code": "und", "label": "Klingon"}

    def test_known_string_label_maps_to_code(self) -> None:
        assert resolve_language({"language": "Spanish"}) == {"code": "es", "label": "Spanish"}

    def test_missing_language_defaults_to_english(self) -> None:
        assert resolve_language({}) == {"code": "en", "label": "English"}

    def test_object_without_code_maps_from_label(self) -> None:
        assert resolve_language({"language": {"label": "French"}}) == {
            "code": "fr",
            "label": "French",
        }


class TestProjectSpecResolution:
    """Bug 2 — the real spec lives at top-level project_specific; the
    agent_guidelines copy is often the untouched [FILL] template."""

    def _doc(self) -> dict:
        return {
            "agent_guidelines": {
                "project_specific": {
                    "domain": "[FILL: one-line description]",
                    "deliverable_type": "[FILL: ...]",
                    "final_goal": "[FILL: ...]",
                    "source_tiers": {
                        "tier_1": "[FILL in session_zero]",
                        "tier_2": "[FILL in session_zero]",
                        "discovery": "[FILL in session_zero]",
                        "never": "[FILL in session_zero]",
                    },
                }
            },
            "project_specific": {
                "domain": "Distributed systems",
                "deliverable": "software",
                "final_goal": "Ship a consensus library",
                "timeline": "Q3 2026",
                "validation_gate": "All tests pass",
                "source_tiers": {
                    "tier_1": "Peer-reviewed papers",
                    "tier_2": "Official docs",
                    "tier_3": "Engineering blogs",
                    "never_tier": "Anonymous PDFs",
                },
            },
        }

    def test_recovers_top_level_scalars(self) -> None:
        ps = resolve_project_spec(self._doc())
        assert ps["domain"] == "Distributed systems"
        assert ps["final_goal"] == "Ship a consensus library"
        assert ps["validation_gate"] == "All tests pass"

    def test_normalizes_key_aliases(self) -> None:
        ps = resolve_project_spec(self._doc())
        assert ps["deliverable_type"] == "software"
        assert ps["timing"] == "Q3 2026"

    def test_normalizes_tier_aliases(self) -> None:
        ps = resolve_project_spec(self._doc())
        assert ps["source_tiers"]["discovery"] == "Engineering blogs"
        assert ps["source_tiers"]["never"] == "Anonymous PDFs"

    def test_filled_guidelines_wins_over_top_level(self) -> None:
        doc = self._doc()
        doc["agent_guidelines"]["project_specific"]["domain"] = "Real filled domain"
        ps = resolve_project_spec(doc)
        assert ps["domain"] == "Real filled domain"

    def test_migrate_renders_recovered_spec(self) -> None:
        doc = self._doc()
        doc["meta"] = {"version": "1.0"}
        out = migrate(doc)
        assert "Distributed systems" in out
        assert "Ship a consensus library" in out
        assert "Engineering blogs" in out
        # The [FILL] stub must not leak into the rendered spec.
        assert "[FILL" not in out.split("## Project Specification")[1].split("---")[0]

    def test_no_top_level_falls_back_to_guidelines(self) -> None:
        doc = {
            "agent_guidelines": {"project_specific": {"domain": "only here", "timing": "now"}},
        }
        ps = resolve_project_spec(doc)
        assert ps["domain"] == "only here"
        assert ps["timing"] == "now"


class TestOverviewTabSurvival:
    """Bug 3 — substantive overview content must survive; only nav is dropped."""

    def _overview_tab(self) -> dict:
        return {
            "id": "overview",
            "label": "Overview",
            "sections": {
                "Quick Links": {"blocks": [{"type": "p", "md": "see other tabs"}]},
                "How to Navigate": {"blocks": [{"type": "p", "md": "click around"}]},
                "Project Goal": {"blocks": [{"type": "p", "md": "Build the best thing."}]},
                "Working Hypotheses": {
                    "blocks": [{"type": "ul", "items": ["H1 holds", "H2 is open"]}]
                },
            },
        }

    def test_substantive_sections_survive_as_subsections(self) -> None:
        out = build_overview_tab(self._overview_tab())
        assert "## Overview" in out
        assert "### Project Goal" in out
        assert "Build the best thing." in out
        assert "### Working Hypotheses" in out
        assert "H1 holds" in out

    def test_nav_sections_dropped(self) -> None:
        out = build_overview_tab(self._overview_tab())
        assert "Quick Links" not in out
        assert "How to Navigate" not in out
        assert "click around" not in out

    def test_pure_nav_tab_returns_empty(self) -> None:
        tab = {
            "id": "overview",
            "sections": {
                "Quick Links": {"blocks": [{"type": "p", "md": "x"}]},
                "How to Navigate": {"blocks": [{"type": "p", "md": "y"}]},
            },
        }
        assert build_overview_tab(tab) == ""

    def test_migrate_places_overview_after_project_spec(self) -> None:
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [self._overview_tab()],
        }
        out = migrate(doc)
        assert "## Overview" in out
        assert "Build the best thing." in out
        assert out.index("## Project Specification") < out.index("## Overview")

    def test_migrate_omits_pure_nav_overview(self) -> None:
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [
                {
                    "id": "overview",
                    "label": "Overview",
                    "sections": {"Quick Links": {"blocks": [{"type": "p", "md": "x"}]}},
                }
            ],
        }
        out = migrate(doc)
        assert "## Overview" not in out


class TestQueueDoneDetection:
    """Bug 4 — completed rows without the ✦ glyph must leave the open queue."""

    def _queue_block(self) -> dict:
        return {
            "headers": ["Priority", "Topic", "Status"],
            "rows": [
                ["1", "Q-001 Pending topic", "OPEN"],
                ["2", "Q-002 Glyph done", "✦ Researched"],
                ["3", "Q-003 No-glyph done", "Researched v1.3"],
            ],
        }

    def test_no_glyph_researched_row_stripped(self) -> None:
        _, rows = _strip_done_rows_from_queue(self._queue_block(), {})
        topics = [" ".join(str(c) for c in r) for r in rows]
        assert any("Q-001" in t for t in topics)
        assert not any("Q-002" in t for t in topics)
        assert not any("Q-003" in t for t in topics)

    def test_not_researched_status_is_kept(self) -> None:
        # Regression: a leading-anchored match must not treat "Not Researched"
        # or "To be researched" (open statuses) as done.
        block = {
            "headers": ["Priority", "Topic", "Status"],
            "rows": [
                ["1", "Q-001 Open one", "Not Researched"],
                ["2", "Q-002 Open two", "To be researched"],
                ["3", "Q-003 Done one", "Researched v2.1"],
            ],
        }
        _, rows = _strip_done_rows_from_queue(block, {})
        topics = [" ".join(str(c) for c in r) for r in rows]
        assert any("Q-001" in t for t in topics)
        assert any("Q-002" in t for t in topics)
        assert not any("Q-003" in t for t in topics)

    def test_row_in_tracker_stripped_even_without_status(self) -> None:
        block = {
            "headers": ["Topic"],
            "rows": [["Q-001 Pending"], ["Q-009 Already tracked"]],
        }
        _, rows = _strip_done_rows_from_queue(block, {}, tracker_ids={"Q-009"})
        flat = [" ".join(str(c) for c in r) for r in rows]
        assert any("Q-001" in t for t in flat)
        assert not any("Q-009" in t for t in flat)

    def test_tracker_ids_extracted(self) -> None:
        research_tab = {
            "sections": {
                "Research Tracker": {
                    "blocks": [
                        {
                            "type": "table",
                            "headers": ["ID", "Topic"],
                            "rows": [["Q-002", "Done thing"], ["Q-003", "Other"]],
                        }
                    ]
                }
            }
        }
        assert _tracker_ids(research_tab) == {"Q-002", "Q-003"}

    def test_no_id_in_both_queue_and_tracker(self) -> None:
        # End-to-end: a no-glyph completed row that is also in the tracker must
        # appear in the Research Tracker but NOT in the Open Research Queue.
        research_tab = {
            "id": "research",
            "sections": {
                "Open Research Queue": {
                    "blocks": [
                        {
                            "type": "table",
                            "headers": ["Priority", "Topic", "Status"],
                            "rows": [
                                ["1", "Q-001 Pending", "OPEN"],
                                ["2", "Q-002 Completed", "Researched v1.3"],
                            ],
                        }
                    ]
                },
                "Research Tracker": {
                    "blocks": [
                        {
                            "type": "table",
                            "headers": ["ID", "Topic", "Status"],
                            "rows": [["Q-002", "Completed", "✦ Researched v1.3"]],
                        }
                    ]
                },
            },
        }
        doc = {
            "meta": {"version": "1.4"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [research_tab],
        }
        out = migrate(doc)
        # Anchors (not H2 text) — the framework block mentions the section names.
        queue = out.split("<!-- @anchor: queue -->")[1].split("<!-- @end: queue -->")[0]
        tracker = out.split("<!-- @anchor: tracker -->")[1].split("<!-- @end: tracker -->")[0]
        assert "Q-002" not in queue
        assert "Q-001" in queue
        assert "Q-002" in tracker


class TestSessionNotesCatchAll:
    """Regression guard — monolithic `Session Notes` section content survives
    the catch-all (worked in 1.12.0; keep it that way)."""

    def test_monolithic_session_notes_survive(self) -> None:
        research_tab = {
            "id": "research",
            "sections": {
                "Session Notes": {
                    "blocks": [
                        {"type": "h3", "md": "Topic Alpha"},
                        {"type": "p", "md": "Findings for alpha."},
                        {"type": "h3", "md": "Topic Beta"},
                        {"type": "p", "md": "Findings for beta."},
                    ]
                }
            },
        }
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [research_tab],
        }
        out = migrate(doc)
        # Anchors (not H2 text) — the framework block mentions "Session Notes".
        sessions = out.split("<!-- @anchor: sessions -->")[1].split("<!-- @end: sessions -->")[0]
        assert "Findings for alpha." in sessions
        assert "Findings for beta." in sessions
        assert "Topic Alpha" in sessions
        assert "Topic Beta" in sessions


class TestMigrateHardening:
    """PR-7: ID/version collision + frontmatter/changelog correctness fixes."""

    def test_changelog_sort_is_patch_aware(self) -> None:
        # The old (major, minor)-only sort key collapsed 1.1.0 and 1.1.4, so
        # they sorted unstably. Now patch precision keeps 1.1.4 above 1.1.0.
        doc = {
            "meta": {"version": "1.1.4", "date": "2026-02-01"},
            "changelog": {
                "entries": [
                    {"version": "1.1.0", "date": "2026-01-01", "blocks": []},
                    {"version": "1.1.4", "date": "2026-02-01", "blocks": []},
                ]
            },
        }
        cl = build_changelog(doc)
        assert cl.index("v1.1.4") < cl.index("v1.1.0")

    def test_changelog_renders_entry_date(self) -> None:
        doc = {
            "meta": {"version": "1.2", "date": "2026-06-22"},
            "changelog": {
                "entries": [
                    {"version": "1.2", "date": "2026-06-22", "blocks": []},
                ]
            },
        }
        cl = build_changelog(doc)
        assert "### v1.2 — 2026-06-22" in cl

    def test_synthetic_changelog_entry_carries_meta_date(self) -> None:
        # meta.version with no matching changelog entry → synthetic entry, which
        # should still carry a date (from meta) rather than render dateless.
        doc = {
            "meta": {"version": "2.0", "date": "2026-06-22"},
            "changelog": {"entries": [{"version": "1.0", "date": "2026-01-01", "blocks": []}]},
        }
        cl = build_changelog(doc)
        assert "### v2.0 — 2026-06-22" in cl

    def test_queue_id_synthesis_avoids_collisions(self) -> None:
        # First row unlabeled (so the synthesis path runs); a later row carries
        # an inline Q-003; the tracker already owns Q-001. Synthesized IDs must
        # avoid both — the old row-index scheme produced Q-001 (tracker dup) and
        # a second Q-003 (inline dup).
        tb = {
            "headers": ["Topic", "Status"],
            "rows": [["New A", "OPEN"], ["Q-003 B", "OPEN"], ["New C", "OPEN"]],
        }
        headers, rows = _strip_done_rows_from_queue(tb, {}, {"Q-001"})
        ids = [r[0] for r in rows]
        assert headers[0] == "ID"
        assert len(set(ids)) == len(ids)  # all unique
        assert "Q-001" not in ids  # no tracker collision
        assert ids.count("Q-003") == 1  # inline ID preserved, not duplicated

    def test_queue_id_synthesis_handles_empty_row(self) -> None:
        # A row that becomes empty after dropping the Priority/Status columns
        # must not raise IndexError during ID synthesis (regression: the two-pass
        # rewrite briefly indexed row[0] unconditionally).
        tb = {
            "headers": ["Topic", "Priority"],
            "rows": [["A", "hi"], [], ["C", "lo"]],
        }
        headers, rows = _strip_done_rows_from_queue(tb, {}, set())
        assert headers[0] == "ID"
        ids = [r[0] for r in rows]
        assert ids == ["Q-001", "Q-002", "Q-003"]
        assert rows[1] == ["Q-002"]  # empty row → just the ID cell

    def test_verdict_rule_anchor_id_is_slugified(self) -> None:
        # A label without a clean R-/DA- prefix must still yield a valid HTML id
        # (no spaces or punctuation in the <a id>).
        out = _render_verdict_as_da(
            {"type": "verdict", "badge": "reject", "label": "Why not X? (option)", "md": "no"}
        )
        assert '<a id="why-not-x-option"></a>' in out
        assert " " not in out.split('id="')[1].split('"')[0]

    def test_verdict_wellformed_rule_id_unchanged(self) -> None:
        out = _render_verdict_as_rule(
            {"type": "verdict", "badge": "adopt", "label": "R-FM-1 ADOPTED", "md": ""}
        )
        assert '<a id="r-fm-1"></a>' in out
        assert "<!-- @rule: R-FM-1 -->" in out

    def test_domain_tab_label_does_not_clobber_canonical_anchor(self) -> None:
        dt = build_domain_tab({"id": "x", "label": "References", "sections": {}})
        assert "<!-- @anchor: references-tab -->" in dt
        assert "<!-- @anchor: references -->" not in dt

    def test_frontmatter_carries_source_tiers_and_domain_rules(self) -> None:
        doc = {
            "meta": {"version": "1.0"},
            "project_specific": {
                "domain": "ML",
                "source_tiers": {"tier_1": "arXiv", "tier_3": "blogs"},
                "domain_rules": "Prefer RCTs",
            },
            "agent_guidelines": {"project_specific": {}},
        }
        fm = yaml.safe_load(build_frontmatter(doc).strip("-\n "))
        project = fm["project"]
        assert project["source_tiers"]["tier_1"] == "arXiv"
        # tier_3 is aliased to `discovery` by the top-level normalizer.
        assert project["source_tiers"]["discovery"] == "blogs"
        assert project["domain_rules"] == "Prefer RCTs"


class TestVerdictLabelDedup:
    """P2-10 — duplicate verdict <a id> values must be deduplicated."""

    def _rule_blk(self, label: str = "R-FM-1 VALIDATED") -> dict:
        return {"type": "verdict", "badge": "adopt", "label": label, "md": "body"}

    def _da_blk(self, label: str = "DA-Q1-1 reason") -> dict:
        return {"type": "verdict", "badge": "reject", "label": label, "md": "why"}

    def test_first_occurrence_unchanged(self) -> None:
        seen: set[str] = set()
        out = _render_verdict_as_rule(self._rule_blk(), seen)
        assert '<a id="r-fm-1"></a>' in out
        assert "r-fm-1" in seen

    def test_duplicate_rule_gets_numeric_suffix(self) -> None:
        seen = {"r-fm-1"}
        out = _render_verdict_as_rule(self._rule_blk(), seen)
        assert '<a id="r-fm-1-2"></a>' in out
        assert "r-fm-1-2" in seen

    def test_third_occurrence_gets_suffix_3(self) -> None:
        seen = {"r-fm-1", "r-fm-1-2"}
        out = _render_verdict_as_rule(self._rule_blk(), seen)
        assert '<a id="r-fm-1-3"></a>' in out

    def test_da_dedup(self) -> None:
        seen: set[str] = set()
        out1 = _render_verdict_as_da(self._da_blk(), seen)
        out2 = _render_verdict_as_da(self._da_blk(), seen)
        assert '<a id="da-q1-1"></a>' in out1
        assert '<a id="da-q1-1-2"></a>' in out2

    def test_none_seen_ids_no_dedup(self) -> None:
        # Backward compat: no seen_ids argument → ids are returned unchanged.
        out1 = _render_verdict_as_rule(self._rule_blk())
        out2 = _render_verdict_as_rule(self._rule_blk())
        assert out1.count('<a id="r-fm-1"></a>') == 1
        assert out2.count('<a id="r-fm-1"></a>') == 1

    def test_dedup_propagates_via_render_blocks(self) -> None:
        blk = self._rule_blk()
        seen: set[str] = set()
        out = render_blocks([blk, blk], seen_ids=seen)
        assert '<a id="r-fm-1"></a>' in out
        assert '<a id="r-fm-1-2"></a>' in out

    def test_dedup_propagates_via_render_subsections(self) -> None:
        blk = self._rule_blk()
        sec = {
            "subsections": {
                "Sub A": {"blocks": [blk]},
                "Sub B": {"blocks": [blk]},
            }
        }
        seen: set[str] = set()
        out = render_subsections(sec, start_level=3, seen_ids=seen)
        assert '<a id="r-fm-1"></a>' in out
        assert '<a id="r-fm-1-2"></a>' in out

    def test_dedup_across_domain_tabs_via_migrate(self) -> None:
        # Two domain tabs each carrying the same R-FM-1 rule — migrate() must
        # deduplicate so the HTML has only one <a id="r-fm-1">.
        rule_blk = {"type": "verdict", "badge": "adopt", "label": "R-FM-1 VALIDATED", "md": "x"}
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [
                {"id": "tab1", "label": "Tab One", "sections": {"Rules": {"blocks": [rule_blk]}}},
                {"id": "tab2", "label": "Tab Two", "sections": {"Rules": {"blocks": [rule_blk]}}},
            ],
        }
        out = migrate(doc)
        assert out.count('<a id="r-fm-1">') == 1
        assert '<a id="r-fm-1-2">' in out

    def test_dedup_across_tab_and_discarded(self) -> None:
        # A DA that appears in both a domain tab and the Discarded Alternatives
        # section should also be deduplicated document-wide.
        da_blk = {"type": "verdict", "badge": "reject", "label": "DA-Q1-1 reason", "md": "no"}
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [
                {
                    "id": "design",
                    "label": "Design",
                    "sections": {"Discards": {"blocks": [da_blk]}},
                },
                {
                    "id": "research",
                    "sections": {
                        "Discarded Alternatives": {"blocks": [da_blk]},
                    },
                },
            ],
        }
        out = migrate(doc)
        assert out.count('<a id="da-q1-1">') == 1
        assert '<a id="da-q1-1-2">' in out


class TestDroppedContentMarker:
    """P2-13c — intentionally-dropped v1 sections must emit a visible marker."""

    def _doc_with_methodology(self) -> dict:
        return {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [
                {
                    "id": "research",
                    "sections": {
                        "Research Methodology": {
                            "blocks": [{"type": "p", "md": "We use systematic review."}]
                        }
                    },
                }
            ],
        }

    def test_dropped_sections_helper_detects_methodology(self) -> None:
        research_tab = {
            "sections": {
                "Research Methodology": {"blocks": []},
                "Open Research Queue": {"blocks": []},
            }
        }
        assert _dropped_research_sections(research_tab) == ["Research Methodology"]

    def test_dropped_sections_helper_empty_when_absent(self) -> None:
        assert _dropped_research_sections({"sections": {"Open Research Queue": {}}}) == []

    def test_migrate_embeds_comment_when_methodology_present(self) -> None:
        out = migrate(self._doc_with_methodology())
        assert "MIGRATION NOTE" in out
        assert "Research Methodology" in out

    def test_migrate_comment_placed_before_project_spec(self) -> None:
        out = migrate(self._doc_with_methodology())
        assert out.index("MIGRATION NOTE") < out.index("## Project Specification")

    def test_methodology_content_not_in_output(self) -> None:
        # The section body is intentionally dropped; only the marker comment survives.
        out = migrate(self._doc_with_methodology())
        assert "We use systematic review." not in out

    def test_no_comment_when_methodology_absent(self) -> None:
        doc = {
            "meta": {"version": "1.0"},
            "agent_guidelines": {"project_specific": {}},
            "tabs": [],
        }
        assert "MIGRATION NOTE" not in migrate(doc)

    def test_main_prints_stderr_warning_when_methodology_present(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        in_path = tmp_path / "in.json"
        in_path.write_text(
            json.dumps(self._doc_with_methodology()),
            encoding="utf-8",
        )
        rc = main([str(in_path), "-o", str(tmp_path / "out.md")])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Research Methodology" in captured.err

    def test_main_no_stderr_when_no_dropped_sections(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        doc = {"meta": {"version": "1.0"}, "agent_guidelines": {"project_specific": {}}}
        in_path = tmp_path / "in.json"
        in_path.write_text(json.dumps(doc), encoding="utf-8")
        rc = main([str(in_path), "-o", str(tmp_path / "out.md")])
        assert rc == 0
        assert capsys.readouterr().err == ""
