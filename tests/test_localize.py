"""Tests for `research_buddy.localize` — display labels for framework headings."""

from __future__ import annotations

from research_buddy.localize import SECTION_LABELS, localized_label


class TestLocalizedLabel:
    def test_translates_known_heading(self) -> None:
        assert localized_label("Open Research Queue", "es") == "Cola de investigación"

    def test_strips_region_subtag(self) -> None:
        # es-419 should resolve like es.
        assert localized_label("References", "es-419") == "Referencias"

    def test_english_is_noop(self) -> None:
        assert localized_label("References", "en") == "References"

    def test_empty_lang_is_noop(self) -> None:
        assert localized_label("References", "") == "References"

    def test_unknown_language_falls_back_to_english(self) -> None:
        assert localized_label("References", "de") == "References"

    def test_unknown_heading_falls_back_unchanged(self) -> None:
        assert localized_label("Some Project Heading", "es") == "Some Project Heading"

    def test_override_wins_over_builtin(self) -> None:
        overrides = {"Open Research Queue": "Cola de tareas"}
        assert localized_label("Open Research Queue", "es", overrides) == "Cola de tareas"

    def test_override_enables_unshipped_language(self) -> None:
        overrides = {"References": "Références"}
        assert localized_label("References", "fr", overrides) == "Références"

    def test_blank_override_is_ignored(self) -> None:
        overrides = {"References": "   "}
        assert localized_label("References", "es", overrides) == "Referencias"

    def test_non_string_override_is_ignored(self) -> None:
        overrides = {"References": ["not", "a", "string"]}  # type: ignore[dict-item]
        assert localized_label("References", "es", overrides) == "Referencias"

    def test_non_dict_overrides_is_ignored(self) -> None:
        # A malformed `section_labels` (e.g. a list) must not crash .get().
        assert localized_label("References", "es", ["nope"]) == "Referencias"  # type: ignore[arg-type]

    def test_non_string_lang_code_is_noop(self) -> None:
        assert localized_label("References", None) == "References"  # type: ignore[arg-type]


class TestSectionLabelsTable:
    def test_every_label_has_spanish(self) -> None:
        # The shipped language is Spanish; every canonical heading must cover it
        # so a Spanish doc localizes with zero config.
        for english, langs in SECTION_LABELS.items():
            assert "es" in langs, f"{english!r} missing an 'es' translation"
            assert langs["es"] and langs["es"] != english
