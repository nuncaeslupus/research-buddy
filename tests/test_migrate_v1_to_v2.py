"""Tests for `research_buddy.migrate_v1_to_v2` — v1 JSON → v2 MD source converter."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from research_buddy import __version__
from research_buddy.migrate_v1_to_v2 import (
    build_frontmatter,
    derive_output_path,
    load_framework_block_from_starter,
    main,
    migrate,
    parse_rule_label,
    render_block,
    render_subsections,
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
