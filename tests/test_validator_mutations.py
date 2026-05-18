"""Targeted tests that kill mutmut survivors in `research_buddy.validator`.

Step #7a of the mutation-survivor cleanup roadmap. Each test is written to
pin behavior that a high-coverage line-based test suite was leaving open
for mutmut to mutate undetected. See `status/next-session.md` (session 19+)
for the full survivor list and classification.

Buckets:
    - `_parse_date` / `_parse_semver`: direct unit assertions on return tuples.
    - `_check_version_compatibility`: exact error-message text.
    - `validate` schema-error path formatting + sort order.
    - `validate` rb-version / language exact-message text.
    - Empty-default branches (`.get(key, {})` / `.get(key, [])`) and
      subsections recursion.
"""

from __future__ import annotations

from research_buddy.validator import (
    _check_version_compatibility,
    _parse_date,
    _parse_semver,
    validate,
)

# Module-level constants — shared across several test classes that build
# minimum-valid v1 docs. Each test that mutates a copy uses {**_BASE_META, …}.
_BASE_META = {
    "version": "1.0",
    "date": "April 2026",
    "title": "T",
    "research_buddy_version": "1.10.0",
}
_BASE_TABS: list[dict] = [{"id": "overview", "label": "Overview", "sections": {}}]


class TestParseDateInternals:
    """Pin `_parse_date` return values so regex/format mutations get caught."""

    def test_yyyy_mm_dd(self) -> None:
        assert _parse_date("2026-04-01") == (2026, 4, 1)

    def test_yyyy_mm_dd_with_trailing_text_uses_match_not_findall(self) -> None:
        # `re.match` anchors the (Y, M, D) capture at the start of the
        # string. The numeric-fallback branch (re.findall) would pick up the
        # trailing "5" as a fourth element. Asserting the 3-tuple result
        # kills mutants that bypass the regex (`m = None`) or rewrap it.
        assert _parse_date("2026-04-01-rev5") == (2026, 4, 1)

    def test_month_year_form(self) -> None:
        # Trailing 0 (day) distinguishes the Month-YYYY branch from a
        # mutant that swaps it to 1.
        assert _parse_date("April 2026") == (2026, 4, 0)


class TestParseSemverInternals:
    """Pin `_parse_semver` zero-fill semantics for missing minor/patch."""

    def test_major_only_zero_fills_minor_and_patch(self) -> None:
        # Catches `int(m.group(2) or 0)` → `or 1` mutant.
        assert _parse_semver("1") == (1, 0, 0)

    def test_major_minor_zero_fills_patch(self) -> None:
        # Catches `int(m.group(3) or 0)` → `or 1` mutant.
        assert _parse_semver("1.0") == (1, 0, 0)

    def test_major_minor_patch_roundtrip(self) -> None:
        assert _parse_semver("2.5.7") == (2, 5, 7)


class TestVersionCompatibilityExactMessage:
    """The unparseable-doc-version message is part of the contract."""

    def test_unparseable_doc_version_exact_text(self) -> None:
        # Single-call return — no schema noise — so we can assert the
        # whole message verbatim. Kills XX-wrap and casing mutants on the
        # hint substring "Expected something like '1.0' or '1.0.3'.".
        result = _check_version_compatibility("banana", "1.10.0")
        assert result == [
            "[meta.research_buddy_version] Unrecognized version format: "
            "'banana'. Expected something like '1.0' or '1.0.3'."
        ]


class TestSchemaErrorPathFormatting:
    """`validate` joins JSON-pointer path components with '.' and falls back
    to '(root)' when the path is empty. Both the literal and the joiner are
    user-visible and have to survive mutation."""

    def test_root_path_uses_literal_root_marker(self) -> None:
        issues = validate({})
        # Missing 'meta' / 'tabs' at the document root → "(root)" path.
        # Asserting the exact bracketed prefix kills:
        #   - path = None mutant       → "[None] …"
        #   - path = "(ROOT)" mutant   → "[(ROOT)] …"
        #   - "(root)" → "XX(root)XX"  → "[XX(root)XX] …"
        #   - `and "(root)"` mutant    → "[] …" (empty join evaluates falsy)
        assert any(i.startswith("[(root)] ") for i in issues), issues
        assert not any("[None]" in i for i in issues)
        assert not any("[(ROOT)]" in i for i in issues)
        assert not any("[XX(root)XX]" in i for i in issues)

    def test_deep_path_uses_dot_joiner_with_string_components(self) -> None:
        # tab at index 0 missing required 'id' → JSON path ['tabs', 0]
        # → "[tabs.0]". Kills:
        #   - "." → "XX.XX" mutant         → "[tabsXX.XX0]"
        #   - str(p) → str(None) mutant    → "[None.None]"
        #   - empty-or-(root) mutants don't fire here (path non-empty)
        issues = validate(
            {
                "meta": {
                    "version": "1.0",
                    "date": "April 2026",
                    "title": "T",
                    "research_buddy_version": "1.10.0",
                },
                "tabs": [{"label": "L", "sections": {}}],
            }
        )
        assert any(i.startswith("[tabs.0] ") for i in issues), issues
        assert not any("[tabsXX.XX0]" in i for i in issues)
        assert not any("[None.None]" in i for i in issues)


class TestSchemaErrorSortOrder:
    """`validate` sorts schema errors by string-formatted path so output is
    deterministic regardless of jsonschema's internal iteration order."""

    def test_errors_sorted_by_path_not_natural_order(self) -> None:
        # Schema declares properties in the order
        # `agent_guidelines, meta, tabs, changelog`, so jsonschema's
        # iter_errors emits a 'meta' error BEFORE a 'changelog' error.
        # Sorted by str(list(path)), "[changelog]" precedes "[meta]"
        # alphabetically. Verifying the sorted order kills the mutant
        # that replaces the sort key with the constant `str(None)`
        # (which collapses to a stable no-op preserving natural order).
        issues = validate(
            {
                "meta": {
                    "version": "1.0",
                    "title": "T",
                    "research_buddy_version": "1.10.0",
                    # missing 'date' → forces a [meta] error
                },
                "tabs": [{"id": "a", "label": "L", "sections": {}}],
                "changelog": "not-an-array",  # type mismatch → [changelog]
            }
        )
        changelog_idx = next((i for i, w in enumerate(issues) if w.startswith("[changelog]")), -1)
        meta_idx = next((i for i, w in enumerate(issues) if w.startswith("[meta]")), -1)
        assert changelog_idx != -1 and meta_idx != -1, issues
        assert changelog_idx < meta_idx, (
            f"[changelog] must precede [meta] under path-sort, got order: {issues}"
        )


class TestRbVersionMissingExactMessage:
    """Exact-text assertion on the missing-rb-version warning. Substring
    matches on 'research_buddy_version' alone leave XX-wrap and casing
    mutations alive."""

    def test_missing_rb_version_full_text(self) -> None:
        doc = {
            "meta": {"version": "1.0", "date": "April 2026", "title": "T"},
            "tabs": [{"id": "overview", "label": "Overview", "sections": {}}],
        }
        issues = validate(doc)
        # TOOL_VERSION is interpolated into the middle of the message, so
        # we assert both the leading and trailing fixed substrings
        # verbatim (case-sensitive). Together they pin every static piece
        # of the message except the version itself.
        missing_msg = next(
            (i for i in issues if "research_buddy_version" in i and "Missing" in i),
            None,
        )
        assert missing_msg is not None, issues
        assert missing_msg.startswith(
            "[meta.research_buddy_version] Missing — add 'research_buddy_version': '"
        )
        assert missing_msg.endswith(
            "' to meta. This field is required for schema and build script version traceability."
        )


class TestLanguageExactMessages:
    """The two `[meta.language]` warnings are case- and punctuation-sensitive.
    Loose `"language" in i.lower()` assertions leave casing and XX-wrap
    mutants alive."""

    def test_invalid_type_full_text(self) -> None:
        doc = {
            "meta": {**_BASE_META, "language": 42},
            "tabs": _BASE_TABS,
        }
        issues = validate(doc)
        expected = (
            "[meta.language] Must be a string (e.g. 'English') or an object "
            "with at least a 'code' key (e.g. {'code': 'en', 'label': 'English'})."
        )
        assert expected in issues, issues

    def test_object_missing_code_full_text(self) -> None:
        doc = {
            "meta": {**_BASE_META, "language": {"label": "English"}},
            "tabs": _BASE_TABS,
        }
        issues = validate(doc)
        assert "[meta.language] Object form must include a 'code' key." in issues

    def test_language_absent_does_not_emit_language_warning(self) -> None:
        # The `lang is not None` guard is critical — flipping it to
        # `lang is None` would fire the invalid-type warning when the
        # field is omitted entirely. Pin the absence-of-warning.
        doc = {"meta": _BASE_META, "tabs": _BASE_TABS}
        issues = validate(doc)
        assert not any("[meta.language]" in i for i in issues), issues


class TestEmptyKeyDefaults:
    """`_validate_references` and `_walk_references` rely on `.get(key, {})`
    / `.get(key, [])` defaults so missing keys don't crash the walk. Mutants
    that change those defaults to None would `for x in None` / `None.items()`
    and raise. Each test exercises a doc shape with the relevant key absent."""

    def test_tab_without_sections_key_does_not_crash(self) -> None:
        # Schema requires `sections` so this still emits a structural
        # warning — but `_validate_references` must run cleanly afterwards.
        # Kills `_validate_references#13, #15`
        # (`tab.get("sections", {})` → None / missing default).
        doc = {
            "meta": _BASE_META,
            "tabs": [{"id": "a", "label": "L"}],  # sections absent
        }
        # Just calling validate without an exception is the assertion.
        validate(doc)

    def test_section_without_blocks_key_does_not_crash(self) -> None:
        # `blocks` is optional in the section schema; a section without
        # it must still be walked without raising.
        # Kills `_walk_references#2, #4` (`sec.get("blocks", [])` → None).
        doc = {
            "meta": _BASE_META,
            "tabs": [
                {
                    "id": "a",
                    "label": "L",
                    "sections": {"Empty": {"subtitle": "no blocks here"}},
                }
            ],
        }
        validate(doc)

    def test_references_block_without_items_key_does_not_crash(self) -> None:
        # A references block with no `items` key must walk cleanly.
        # Kills `_walk_references#15, #17` (`b.get("items", [])` → None).
        doc = {
            "meta": _BASE_META,
            "tabs": [
                {
                    "id": "a",
                    "label": "L",
                    "sections": {
                        "Refs": {"blocks": [{"type": "references"}]},
                    },
                }
            ],
        }
        validate(doc)


class TestSubsectionsRecursion:
    """The recursive descent into `sec.get("subsections", {})` must actually
    be triggered. Mutants that swap the key name or the warnings list keep
    the surface API working but skip the subsection check."""

    def _doc_with_subsection_misordered_refs(self) -> dict:
        # A subsection whose references are version-ascending — the
        # validator must descend into subsections and report the issue.
        return {
            "meta": _BASE_META,
            "tabs": [
                {
                    "id": "a",
                    "label": "L",
                    "sections": {
                        "Top": {
                            "subsections": {
                                "Inner": {
                                    "blocks": [
                                        {
                                            "type": "references",
                                            "items": [
                                                {"version": "v1.0", "text": "Old"},
                                                {"version": "v1.1", "text": "New"},
                                            ],
                                        }
                                    ]
                                }
                            }
                        }
                    },
                }
            ],
        }

    def test_subsection_misordered_refs_are_detected(self) -> None:
        # Kills:
        #   _walk_references#60 — sec.get(None, {}) skips recursion entirely
        #   _walk_references#64 — sec.get("XXsubsectionsXX", {}) → no match
        #   _walk_references#65 — sec.get("SUBSECTIONS", {}) → no match
        # If the descent is skipped the misordered refs go unreported,
        # so asserting the warning's presence catches all three.
        issues = validate(self._doc_with_subsection_misordered_refs())
        assert any("REFERENCE ORDER" in i and "Inner" in i for i in issues), issues

    def test_subsection_recursion_passes_real_warnings_list(self) -> None:
        # _walk_references#57 replaces the recursive call's `warnings`
        # argument with None. Once the recursion tries to append the
        # misordered-refs warning to None, AttributeError fires — the
        # test would crash with an exception instead of completing. The
        # previous test would already catch that, but pinning the
        # *count* of REFERENCE ORDER warnings also documents intent
        # (one per misordered block, not silently lost in a None call).
        issues = validate(self._doc_with_subsection_misordered_refs())
        ref_warnings = [i for i in issues if "REFERENCE ORDER" in i]
        assert len(ref_warnings) == 1, ref_warnings
