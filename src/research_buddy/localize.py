"""Localized display labels for the framework-fixed section headings.

The v2 framework names its user-facing sections in English ("Open Research
Queue", "References", …). Those names are load-bearing: the HTML renderer
derives tab ids and heading slugs from them, and cross-links like
`[Queue](#open-research-queue)` point at those slugs. Translating the headings
in the source would break every such link.

So localization happens at HTML-render time only: the renderer keeps the English
text for slug/id derivation but swaps the DISPLAYED text to the document's
language. The clean-view Markdown keeps English headings — there, a heading's
slug *is* its text, so display and link target cannot diverge.

`SECTION_LABELS` maps the canonical English heading → {language subtag:
localized label}. Add a language by adding entries; the renderer falls back to
English for any heading or language not covered. A document overrides or extends
the table via the optional `section_labels:` frontmatter mapping (English
heading → label), which wins over the built-in table — the escape hatch for
languages not shipped here or for project-specific wording.
"""

from __future__ import annotations

# Canonical English heading -> {primary language subtag -> localized label}.
# Keyed by the exact heading text the framework writes: the user-facing H2
# section names plus the three Project Specification H3s. Primary subtags only
# (`es`, not `es-419`) — the resolver strips the region before lookup.
SECTION_LABELS: dict[str, dict[str, str]] = {
    "Project Specification": {"es": "Especificación del proyecto"},
    "Open Research Queue": {"es": "Cola de investigación"},
    "Research Tracker": {"es": "Seguimiento de la investigación"},
    "Adopted Rules": {"es": "Reglas adoptadas"},
    "Discarded Alternatives": {"es": "Alternativas descartadas"},
    "Session Notes": {"es": "Notas de sesión"},
    "Reasoning Journey": {"es": "Recorrido del razonamiento"},
    "References": {"es": "Referencias"},
    "Changelog": {"es": "Registro de cambios"},
    "Domain": {"es": "Dominio"},
    "Source tiers": {"es": "Niveles de fuentes"},
    "Domain rules": {"es": "Reglas del dominio"},
}


def _primary_subtag(lang_code: str) -> str:
    """`es-419` → `es`; `EN` → `en`; `""` → `""`."""
    return (lang_code or "").split("-")[0].strip().lower()


def localized_label(
    english: str,
    lang_code: str,
    overrides: dict[str, str] | None = None,
) -> str:
    """Return the display label for an English framework heading.

    Resolution order: frontmatter `section_labels` override (exact English key)
    → built-in `SECTION_LABELS` for the document's primary language subtag → the
    English original unchanged. Headings that are not framework sections, and
    languages with no translation, fall through to English.
    """
    if overrides:
        ov = overrides.get(english)
        if isinstance(ov, str) and ov.strip():
            return ov
    lang = _primary_subtag(lang_code)
    if lang in ("", "en"):
        return english
    return SECTION_LABELS.get(english, {}).get(lang, english)
