"""Tests for schema validation."""

from __future__ import annotations

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
        ):
            assert key in fw, f"framework missing key: {key}"

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
