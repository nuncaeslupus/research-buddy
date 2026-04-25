"""Tests for schema validation."""

from __future__ import annotations

import re

from jsonschema import Draft202012Validator

from research_buddy.validator import _load_schema, validate


class TestSchemaIntegrity:
    """The bundled schema.json must itself be a valid Draft 2020-12 schema."""

    def test_schema_is_valid_draft_2020_12(self) -> None:
        Draft202012Validator.check_schema(_load_schema())


class TestSchemaValidation:
    def test_valid_starter(self, starter_doc: dict) -> None:
        errors = validate(starter_doc)
        assert errors == []

    def test_missing_meta(self) -> None:
        errors = validate({"tabs": []})
        assert any("meta" in e for e in errors)

    def test_missing_tabs(self) -> None:
        errors = validate({"meta": {"version": "1", "date": "now"}})
        assert any("tabs" in e for e in errors)

    def test_invalid_block_type(self, starter_doc: dict) -> None:
        starter_doc["tabs"][1]["sections"]["Reasoning Journey"]["blocks"].append({"type": "bogus"})
        errors = validate(starter_doc)
        assert any("bogus" in e for e in errors)


class TestResearchBuddyVersion:
    def test_valid_starter_has_version(self, starter_doc: dict) -> None:
        from research_buddy import __version__

        assert starter_doc["meta"].get("research_buddy_version") == __version__

    def test_missing_rb_version_warns(self, starter_doc: dict) -> None:
        del starter_doc["meta"]["research_buddy_version"]
        issues = validate(starter_doc)
        assert any("research_buddy_version" in i for i in issues)

    def test_present_rb_version_no_warn(self, starter_doc: dict) -> None:
        issues = validate(starter_doc)
        assert not any("research_buddy_version" in i for i in issues)


class TestVersionCompatibility:
    """Doc↔tool compatibility rules per MAJOR.MINOR.PATCH semver."""

    def test_exact_match_silent(self, starter_doc: dict) -> None:
        from research_buddy import __version__

        starter_doc["meta"]["research_buddy_version"] = __version__
        issues = validate(starter_doc)
        assert not any("VERSION MISMATCH" in i or "INFO" in i for i in issues)

    def test_patch_difference_silent(self, starter_doc: dict) -> None:
        from research_buddy import __version__
        from research_buddy.validator import _parse_semver

        tool = _parse_semver(__version__)
        assert tool is not None
        # Pin same major.minor, different patch
        starter_doc["meta"]["research_buddy_version"] = f"{tool[0]}.{tool[1]}.99"
        issues = validate(starter_doc)
        assert not any("MISMATCH" in i or "INFO" in i or "upgrade" in i.lower() for i in issues)

    def test_major_mismatch_is_hard_warning(self, starter_doc: dict) -> None:
        from research_buddy import __version__
        from research_buddy.validator import _parse_semver

        tool = _parse_semver(__version__)
        assert tool is not None
        starter_doc["meta"]["research_buddy_version"] = f"{tool[0] + 1}.0.0"
        issues = validate(starter_doc)
        assert any("VERSION MISMATCH" in i for i in issues)

    def test_tool_minor_older_than_doc_warns(self, starter_doc: dict) -> None:
        from research_buddy import __version__
        from research_buddy.validator import _parse_semver

        tool = _parse_semver(__version__)
        assert tool is not None
        # Doc is on a newer minor than the tool
        starter_doc["meta"]["research_buddy_version"] = f"{tool[0]}.{tool[1] + 1}.0"
        issues = validate(starter_doc)
        assert any("pip install --upgrade" in i for i in issues)

    def test_tool_minor_newer_than_doc_is_silent(self, starter_doc: dict) -> None:
        """Older-doc / newer-tool must emit no warning.

        The CLI returns a non-zero exit code whenever validate() returns a non-empty
        list, so "No action required" has to literally mean "no message". The agent
        will bump meta.research_buddy_version on the next write.
        """
        from research_buddy import __version__
        from research_buddy.validator import _parse_semver

        tool = _parse_semver(__version__)
        assert tool is not None
        if tool[1] == 0:
            # Can't go lower than minor=0 on the doc side; skip under this tool version.
            return
        starter_doc["meta"]["research_buddy_version"] = f"{tool[0]}.{tool[1] - 1}.0"
        issues = validate(starter_doc)
        assert not any("research_buddy_version" in i for i in issues)

    def test_unparseable_doc_version(self, starter_doc: dict) -> None:
        starter_doc["meta"]["research_buddy_version"] = "banana"
        issues = validate(starter_doc)
        assert any("Unrecognized version format" in i for i in issues)


class TestLanguageField:
    def test_language_as_object(self, starter_doc: dict) -> None:
        starter_doc["meta"]["language"] = {"code": "en", "label": "English"}
        issues = validate(starter_doc)
        assert not any("language" in i.lower() for i in issues)

    def test_language_as_string(self, starter_doc: dict) -> None:
        starter_doc["meta"]["language"] = "English"
        issues = validate(starter_doc)
        assert not any("[meta.language]" in i for i in issues)

    def test_language_object_missing_code(self, starter_doc: dict) -> None:
        starter_doc["meta"]["language"] = {"label": "English"}
        issues = validate(starter_doc)
        assert any("code" in i for i in issues)

    def test_language_invalid_type(self, starter_doc: dict) -> None:
        starter_doc["meta"]["language"] = 42
        issues = validate(starter_doc)
        assert any("language" in i.lower() for i in issues)


class TestFullValidation:
    def test_combined(self, starter_doc: dict) -> None:
        issues = validate(starter_doc)
        assert issues == []


class TestStarterDocIntegrity:
    def test_three_required_top_level_keys(self, starter_doc: dict) -> None:
        assert "agent_guidelines" in starter_doc
        assert "meta" in starter_doc
        assert "tabs" in starter_doc

    def test_agent_guidelines_structure(self, starter_doc: dict) -> None:
        ag = starter_doc["agent_guidelines"]
        assert "framework" in ag
        assert "session_protocol" in ag
        assert "project_specific" in ag

    def test_framework_keys(self, starter_doc: dict) -> None:
        fw = starter_doc["agent_guidelines"]["framework"]
        for key in (
            "about",
            "widget_library",
            "versioning",
            "failure_modes",
            "html_generation",
            "second_opinion_review",
            "source_discovery",
            "synthesis_matrix",
            "turn_markers",
        ):
            assert key in fw, f"framework missing key: {key}"

    def test_source_discovery_shape(self, starter_doc: dict) -> None:
        sd = starter_doc["agent_guidelines"]["framework"]["source_discovery"]
        for key in (
            "multi_database_principle",
            "author_verification",
            "preprint_caution",
            "paywalled_access",
        ):
            assert key in sd, f"source_discovery missing key: {key}"
        assert isinstance(sd["paywalled_access"], list)
        assert len(sd["paywalled_access"]) >= 1

    def test_synthesis_matrix_shape(self, starter_doc: dict) -> None:
        sm = starter_doc["agent_guidelines"]["framework"]["synthesis_matrix"]
        for key in ("format", "when_required", "pre_registration_rule"):
            assert key in sm, f"synthesis_matrix missing key: {key}"

    def test_pre_update_confirmation_gate(self, starter_doc: dict) -> None:
        ss = starter_doc["agent_guidelines"]["session_protocol"]["standard_session"]
        assert "pre_update_confirmation" in ss
        gate = ss["pre_update_confirmation"]
        assert isinstance(gate.get("steps"), list) and len(gate["steps"]) >= 1
        assert "invariant" in gate
        # The approval-test language must be present so implicit approval is recognised.
        steps_joined = " ".join(gate["steps"]).lower()
        assert "approval test" in steps_joined, (
            "gate must document the approval test that enables implicit approval"
        )
        # The invariant must no longer forbid implicit approval.
        assert "approval test" in gate["invariant"].lower(), (
            "invariant must tie the version bump to the approval test, "
            "not to explicit approval only"
        )
        # Turn 2 must reference the gate so the invariant is hard to miss.
        turn_2 = " ".join(ss["turn_2_review_and_write"])
        assert "pre_update_confirmation" in turn_2

    def test_turn_markers_shape(self, starter_doc: dict) -> None:
        tm = starter_doc["agent_guidelines"]["framework"]["turn_markers"]
        for key in ("rule", "tag_schema", "detection_regex", "states"):
            assert key in tm, f"turn_markers missing key: {key}"
        # The detection_regex must actually match the four declared states.
        regex = re.compile(tm["detection_regex"])
        for state_name in (
            "turn_1_end",
            "turn_2_awaiting_confirmation",
            "turn_2_complete",
            "session_zero_end",
        ):
            assert state_name in tm["states"], f"turn_markers missing state: {state_name}"
            state = tm["states"][state_name]
            for field in ("when", "banner", "tag"):
                assert field in state, f"{state_name} missing field: {field}"
            assert regex.search(state["tag"]), (
                f"{state_name}.tag does not match detection_regex: {state['tag']}"
            )

    def test_turns_wire_end_of_turn_markers(self, starter_doc: dict) -> None:
        """Each defined turn's instruction list must reference turn_markers so the
        agent emits an end-of-turn signal that automation can grep for."""
        sp = starter_doc["agent_guidelines"]["session_protocol"]
        turn_1 = " ".join(sp["standard_session"]["turn_1_research"])
        turn_2 = " ".join(sp["standard_session"]["turn_2_review_and_write"])
        session_zero = " ".join(sp["session_zero"]["after_answers"])
        assert "turn_markers" in turn_1, "turn_1_research must reference turn_markers"
        assert "turn_markers" in turn_2, "turn_2_review_and_write must reference turn_markers"
        assert "turn_markers" in session_zero, (
            "session_zero.after_answers must reference turn_markers"
        )

    def test_html_generation_handles_no_shell_access(self, starter_doc: dict) -> None:
        """html_generation.agent_action must cover the web-chat-no-shell case —
        printing the build command verbatim — not only the 'run via bash' path."""
        action = starter_doc["agent_guidelines"]["framework"]["html_generation"]["agent_action"]
        lower = action.lower()
        assert "shell access" in lower or "no shell" in lower, (
            "agent_action must distinguish the shell-access / no-shell-access branches"
        )
        assert "verbatim" in lower, (
            "agent_action must instruct printing the command verbatim for the no-shell case"
        )

    def test_session_protocol_states(self, starter_doc: dict) -> None:
        sp = starter_doc["agent_guidelines"]["session_protocol"]
        assert "detect_state" in sp
        assert "session_zero" in sp
        assert "standard_session" in sp
        assert "queue_empty" in sp

    def test_second_opinion_what_it_is(self, starter_doc: dict) -> None:
        so = starter_doc["agent_guidelines"]["framework"]["second_opinion_review"]
        assert "what_it_is" in so
        # Must explicitly state agent does not generate opinions itself
        assert "never" in so["what_it_is"].lower() or "CRITICAL" in so["what_it_is"]

    def test_overview_tab_present(self, starter_doc: dict) -> None:
        tab_ids = [t["id"] for t in starter_doc["tabs"]]
        assert "overview" in tab_ids

    def test_research_tab_sections(self, starter_doc: dict) -> None:
        research_tab = next(t for t in starter_doc["tabs"] if t["id"] == "research")
        secs = research_tab["sections"]
        for key in (
            "Open Research Queue",
            "Research Tracker",
            "Reasoning Journey",
            "Discarded Alternatives",
            "References",
        ):
            assert key in secs, f"research tab missing section: {key}"

    def test_queue_has_objective_column(self, starter_doc: dict) -> None:
        research_tab = next(t for t in starter_doc["tabs"] if t["id"] == "research")
        queue_blocks = research_tab["sections"]["Open Research Queue"]["blocks"]
        table_block = next(b for b in queue_blocks if b["type"] == "table")
        assert "Objective / Key Question" in table_block["headers"]

    def test_changelog_tab_present(self, starter_doc: dict) -> None:
        tab_ids = [t["id"] for t in starter_doc["tabs"]]
        assert "changelog" in tab_ids

    def test_ui_strings_present(self, starter_doc: dict) -> None:
        ui = starter_doc["meta"].get("ui_strings", {})
        for key in ("status_open", "status_done", "next_topic_label"):
            assert key in ui, f"ui_strings missing: {key}"

    def test_failure_modes_include_invented_opinions(self, starter_doc: dict) -> None:
        modes = starter_doc["agent_guidelines"]["framework"]["failure_modes"]
        text = " ".join(modes).lower()
        assert "invent" in text or "fictional" in text or "role-play" in text

    def test_citation_format_consistent(self, starter_doc: dict) -> None:
        """The citation format must be identical wherever it's specified.
        Drift here is exactly the kind of bug that motivated splitting the
        brief template into a single source of truth — guard against
        regressions."""
        fw = starter_doc["agent_guidelines"]["framework"]
        ss = starter_doc["agent_guidelines"]["session_protocol"]["standard_session"]

        canonical = "Title, Author, Year, Venue, DOI/URL"
        # The Turn 1 findings instruction must request the canonical citation format.
        turn_1 = " ".join(ss["turn_1_research"])
        assert canonical in turn_1, (
            f"turn_1_research must reference the canonical citation format "
            f"({canonical!r}); got: {turn_1!r}"
        )

        # The brief template (single source of truth) must also use the canonical format.
        brief = fw["second_opinion_review"]["brief_template"]
        assert isinstance(brief, dict), "brief_template must be a dict (instruction + template)"
        assert canonical in brief["template"], (
            f"brief_template.template must reference the canonical citation format ({canonical!r})"
        )

    def test_brief_template_is_single_source_of_truth(self, starter_doc: dict) -> None:
        """The verbatim copy-paste template lives ONLY in
        framework.second_opinion_review.brief_template.template — Turn 1
        references it by name rather than inlining a copy."""
        fw = starter_doc["agent_guidelines"]["framework"]
        ss = starter_doc["agent_guidelines"]["session_protocol"]["standard_session"]

        brief = fw["second_opinion_review"]["brief_template"]
        assert isinstance(brief, dict)
        assert "instruction" in brief and "template" in brief
        # Placeholder markers identify the verbatim template.
        marker = "[PROJECT_AND_BASIC_CHARACTERISTICS]"
        assert marker in brief["template"], (
            f"brief_template.template must contain placeholder markers like {marker!r}"
        )

        # Turn 1 must NOT inline the verbatim template — that's how it
        # drifted from the brief_template description before. It MUST
        # reference brief_template by name.
        turn_1 = " ".join(ss["turn_1_research"])
        assert marker not in turn_1, (
            "turn_1_research must NOT inline the verbatim template — "
            "reference framework.second_opinion_review.brief_template instead"
        )
        assert "brief_template" in turn_1, (
            "turn_1_research must reference framework.second_opinion_review.brief_template "
            "by name so there's a single source of truth"
        )
