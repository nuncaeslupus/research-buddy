"""Shared HTML chrome for the v2 Markdown builder.

These helpers render the parts of the page that are *not* document content — the
Jinja environment, bundled asset loading, the Research Buddy footer, language
resolution, and the unique-ID state machine. They were extracted from the (now
removed) v1 JSON builder so the v2 renderer (`build_md`) and the v1→v2 migrator
(`migrate_v1_to_v2`) can share them without depending on any v1 rendering code.
"""

from __future__ import annotations

import base64
import functools
import re
from importlib import resources
from typing import Any

import jinja2

Doc = dict[str, Any]

# ── Constants ───────────────────────────────────────────────────────────────

# Mapping of human-readable language names to BCP-47 codes, for documents that use
# `language` as a plain string (e.g. "English") instead of the preferred
# {"code": "en", "label": "English"} form. Falls back to a best-effort slug.
_LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "spanish": "es",
    "español": "es",
    "castellano": "es",
    "french": "fr",
    "français": "fr",
    "german": "de",
    "deutsch": "de",
    "italian": "it",
    "italiano": "it",
    "portuguese": "pt",
    "português": "pt",
    "chinese": "zh",
    "中文": "zh",
    "japanese": "ja",
    "日本語": "ja",
    "korean": "ko",
    "한국어": "ko",
    "arabic": "ar",
    "العربية": "ar",
    "russian": "ru",
    "русский": "ru",
    "dutch": "nl",
    "nederlands": "nl",
    "polish": "pl",
    "polski": "pl",
}

_RB_FOOTER_CSS = """
/* ── Research Buddy footer ── */
.rb-powered-by{display:flex;align-items:center;justify-content:center;gap:16px;padding:20px;font-size:12px;color:var(--text3);clear:both}
.rb-logo{width:100px;height:auto}
.rb-powered-by a{color:var(--text3);text-decoration:none}
.rb-powered-by a:hover{color:var(--text2)}
@media print{.rb-powered-by{display:none}}
"""


# ── State Management ────────────────────────────────────────────────────────


class BuildState:
    """Tracks state during a single build pass, primarily for unique ID generation."""

    def __init__(self) -> None:
        self.used_ids: set[str] = set()

    def unique_id(self, base: str) -> str:
        """Generate a unique ID by appending a counter if the base is already taken."""
        if not base:
            base = "id"
        candidate = base
        counter = 2
        while candidate in self.used_ids:
            candidate = f"{base}-{counter}"
            counter += 1
        self.used_ids.add(candidate)
        return candidate


# ── Assets ──────────────────────────────────────────────────────────────────


def _neutralize_style_close(css: str) -> str:
    """Defang any ``</style>`` inside user theme CSS before it's inlined.

    The theme block is interpolated raw into the page's ``<style>`` element
    (Jinja ``autoescape=False``), so a literal ``</style>`` — accidental or
    malicious — would close the element early and let following text render as
    HTML. Backslash-escaping the slash is a no-op for the CSS parser (``<\\/style>``
    is the same token in a string) but no longer matches the HTML end-tag.
    """
    return re.sub(r"</(\s*style)", r"<\\/\1", css, flags=re.IGNORECASE)


def _load_asset(name: str, subdir: str = "") -> str:
    """Load a bundled asset file from the package."""
    if subdir:
        ref = resources.files("research_buddy") / subdir / name
    else:
        ref = resources.files("research_buddy") / name
    return ref.read_text(encoding="utf-8")


def _load_binary_asset(name: str, subdir: str = "") -> bytes:
    """Load a bundled binary asset from the package."""
    if subdir:
        ref = resources.files("research_buddy") / subdir / name
    else:
        ref = resources.files("research_buddy") / name
    return ref.read_bytes()


def _asset_to_base64(data: bytes, mime: str) -> str:
    """Convert binary data to base64 data URL."""
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ── Jinja environment ───────────────────────────────────────────────────────

# autoescape=False matches the historical behaviour: the trusted page chrome
# (base.html.j2) carries the app's own <script>/<style>, and the frontmatter
# scalars interpolated into it are html.escape'd by `build_md`. Agent-authored
# document HTML is sanitized separately (see sanitize_html.py).


@functools.lru_cache(maxsize=1)
def _get_env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.PackageLoader("research_buddy", "templates"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


# ── Language resolution ───────────────────────────────────────────────────────


def _resolve_lang_code(meta: Doc) -> str:
    """Return an HTML lang attribute value (BCP-47-ish) from meta.language.

    Accepts three shapes:
      - {"code": "es", "label": "Español"} — preferred, returns "es".
      - "en", "es-419" — already a BCP-47 short tag, returned as-is (lower-cased).
      - "English", "Spanish" — human-readable, mapped via `_LANGUAGE_NAME_TO_CODE`;
        unknown names fall back to the first whitespace-delimited token, truncated.
    """
    lang_meta = meta.get("language", "en")
    if isinstance(lang_meta, dict):
        return str(lang_meta.get("code") or "en")
    if not lang_meta:
        return "en"
    raw = str(lang_meta).strip()
    if re.fullmatch(r"[a-zA-Z]{2,3}(-[a-zA-Z0-9]+)*", raw):
        return raw.lower()[:10]
    # Whitespace-only strings produce empty split(); fall back to "en" to stay BCP-47-ish.
    tokens = raw.split() or ["en"]
    return _LANGUAGE_NAME_TO_CODE.get(raw.lower(), tokens[0][:10])


# ── Research Buddy footer ─────────────────────────────────────────────────────


def _build_rb_footer_html(meta: Doc) -> str:
    """Render the inline "Powered by Research Buddy" footer div."""
    rb_version = meta.get("research_buddy_version", "")
    logo_data = _rb_logo_data_url()
    ver_suffix = f" v{rb_version}" if rb_version else ""
    return (
        f'<div class="rb-powered-by">'
        f'<img src="{logo_data}" alt="Research Buddy" class="rb-logo">'
        f"<span>Powered by "
        f'<a href="https://github.com/nuncaeslupus/research-buddy">Research Buddy</a>'
        f"{ver_suffix}"
        f"</span></div>\n"
    )


@functools.lru_cache(maxsize=1)
def _rb_logo_data_url() -> str:
    """Load and base64-encode the Research Buddy logo exactly once per process."""
    return _asset_to_base64(_load_binary_asset("research-buddy.png", "images"), "image/png")
