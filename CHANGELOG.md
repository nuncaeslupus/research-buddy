# Changelog

All notable changes to Research Buddy. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.10.0] — 2026-05-14

Operating-manual hardening for the v2 starter, with an upgrade pathway so
existing projects pick up the same improvements via `research-buddy
upgrade <file>.md --apply`.

### Changed

- **Starter operating manual** (top HTML comment between frontmatter and the
  first `@anchor`): compacted into a tight ≤12-line block that fits inside
  any reasonable first-read window. Carries an explicit no-tool-call gate
  ("DO NOT CALL ANY TOOL until you have read framework, detected state,
  and emitted the brief"), the install rule ("if shell access exists and
  `research-buddy --version` fails, `pip install research-buddy`"), and a
  precedence statement over chat-environment tool-priority mandates ("MUST
  use tool X first", "use only tool Y"). Driven by a postmortem of an agent
  that skipped the second-opinion brief because surrounding tool mandates
  outweighed the framework's instructions.
- **Framework Core version-compatibility check** (`research_buddy_version`
  vs the framework loaded for the session): same-MAJOR/MINOR-older now
  *pauses at the top of Turn 1* and asks the user "(a) pause so you can
  run `research-buddy upgrade <file>.md --apply` locally and re-upload, or
  (b) proceed with the older framework this session?" before composing the
  brief or calling any research tool. Previous behavior was a silent note
  in the Turn 2 change summary, which surfaced after the work was done.
- **Visible agent-reminder blockquote** inside the title block now names
  tool calls explicitly ("before any other action — including any tool
  call (web search, extended research, code execution, etc.)").

### Added

- **`research-buddy upgrade <file>.md --apply` now refreshes three
  template-owned regions** instead of one. Previously only the framework
  block (between `<!-- @anchor: framework.core -->` and `<!-- @end:
  framework.reference -->`) was swapped. Now also:
    - the **preamble** — the operating-manual HTML comment between the
      frontmatter close and the first `<!-- @anchor:` line;
    - the **agent-reminder blockquote** — the single visible
      `> **Agent: ...` line inside the title block.
  Project-owned content (frontmatter values, title heading, project spec,
  queue, tracker, rules, DAs, sessions, references, changelog) is still
  preserved exactly. Existing v1.9.1 projects will pick up the operating-
  manual hardening on `upgrade --apply`.

## [1.1.1] — 2026-04-19

Docs and release-infrastructure patch. No code changes.

### Fixed

- **README**: the "Version compatibility (tool ↔ document)" section described
  in the 1.1.0 CHANGELOG was actually missing from the published README (the
  commit adding it landed 4 minutes after its PR merged and never made it to
  main). 1.1.1 ships the real section with the full MAJOR/MINOR/PATCH
  severity table and the "What if my document is on an older version?"
  subsection.

### Added

- **Automated release pipeline** (`.github/workflows/release.yml`). Pushing
  a `v*` tag now runs: `check-version-sync` + tag/pyproject match →
  `make build` + `twine check` → PyPI upload via trusted publishing (OIDC,
  no stored token) → GitHub release with CHANGELOG body and attached wheel +
  sdist.
- **`RELEASE.md`** runbook: one-time PyPI trusted-publisher setup, the
  bump/tag/push flow, failure recovery, and the PATCH/MINOR/MAJOR rubric.

### Upgrading from 1.1.0

No action required. `pip install --upgrade research-buddy` fetches the new
wheel; the PyPI project page now renders the corrected README.

## [1.1.0] — 2026-04-19

### Added

- **Doc ↔ tool version compatibility check.** Every `research-buddy build` and
  `research-buddy validate` now compares `meta.research_buddy_version` against
  the installed CLI and emits a tiered message:
  - MAJOR differs → error-level warning with a migration recipe.
  - Tool MINOR older than doc MINOR (same MAJOR) → upgrade recommendation.
  - Tool MINOR newer than doc MINOR (same MAJOR) → **silent**. No action required;
    the agent will bump `meta.research_buddy_version` on the next write.
  - PATCH-only difference → silent.

  See the "Version compatibility" section in the README.

- **`--all` on `research-buddy build`** now matches any `*_v*.json` filename,
  not just `document_v*.json`. Consistent with `find_latest_json`. Sort key
  uses only the version suffix so project names that contain digits still
  order correctly.

- **CI version-sync gate.** `make check-version-sync` fails if
  `pyproject.toml`, `src/research_buddy/__init__.py`,
  `src/research_buddy/starter.json`, and the README heading fall out of sync.
  Wired into the lint job.

- **`CLAUDE.md`** at the repo root — short orientation file for AI-assisted
  sessions (layout, Make targets, version-sync flow, test fixtures, 2-turn
  workflow, optional extras).

### Changed (backwards-compatible)

- **HTML assembly refactor.** `build.build_html` no longer contains ~28 lines
  of duplicated footer + language code. Extracted `_resolve_lang_code` and
  `_build_rb_footer_html` helpers; the Research Buddy logo is now loaded and
  base64-encoded exactly once per process via `functools.lru_cache`.

- **BCP-47 language mapping.** A `meta.language` string like `"English"` now
  produces `<html lang="en">` via a lookup table (`_LANGUAGE_NAME_TO_CODE`),
  instead of the literal `lang="English"`. BCP-47 tags (`"en"`, `"pt-BR"`,
  `"es-419"`) pass through. Unknown names fall back to the first whitespace-
  delimited token truncated to 10 chars. Dict form
  (`{"code": "en", ...}`) is unchanged.

- **Error messages.** Four CLI errors that referenced the obsolete
  `document_v*.json` naming now say `*_v*.json`.

- **`validate()` consolidated.** `from research_buddy.validator import validate`
  now lives as a single top-level import in `main.py` (was duplicated in three
  places as lazy imports).

- **`validator.py` internals.** Two ad-hoc `_walk` closures flattened to
  module-scope helpers (`_walk_section_ids`, `_walk_references`). No behaviour
  change.

- **README** restructured: new "Version compatibility" section, the "Document
  format" section now points at the bundled `src/research_buddy/schema.json`,
  and the "Examples" section references `make regen-example`.

### Changed (BREAKING)

- **`weasyprint` is now an optional dependency.** Install the `pdf` extra to
  enable PDF export:

  ```bash
  pip install "research-buddy[pdf]"
  ```

  Rationale: weasyprint has heavy system-level dependencies
  (cairo, pango, gobject-introspection) that blocked installs in restricted
  environments, and the README already described it as optional. If you rely
  on `--pdf`, switch to the extra. The CLI prints a clear install hint if
  weasyprint is missing.

### Fixed

- **`--all` silently ignored most files.** Sorting + globbing were scoped to
  `document_v*.json` only. Now matches any `*_v<MAJOR>.<MINOR>.json` and sorts
  by the version suffix rather than every digit in the filename.

- **Whitespace-only `meta.language` used to raise `IndexError`** inside
  `_resolve_lang_code`. Now falls back to `"en"`.

- **`scripts/sync_version.py`** uses `sys.exit(1)` instead of the REPL builtin
  `exit(1)`.

### Upgrading from 1.0.x

**No action required for existing documents.**

- A document with `meta.research_buddy_version: "1.0"` (or `"1.0.3"`) built
  with this 1.1.0 release is fully backwards-compatible. `research-buddy build`
  and `validate` stay silent, exit 0, and the agent bumps
  `meta.research_buddy_version` automatically the next time it writes.
- If you were relying on `pip install research-buddy` to make `--pdf` work,
  run `pip install --upgrade "research-buddy[pdf]"`.
- If you were scripting against `research-buddy build <dir> --all` and
  suspected it was silently doing nothing, that was this bug — it now picks up
  any `*_v*.json`. Re-run against your directory; the output is the union of
  what was previously selected plus anything that was wrongly skipped.

### Migration guidance for the future

If a future release bumps the MAJOR version (2.0.0, …) you will see an
error-level warning from `research-buddy validate` and `research-buddy build`
the first time you run the new CLI against an old document. The warning will
offer you two concrete options:

1. **Pin the old major** (keep your document as-is):

   ```bash
   pip install 'research-buddy==1.*'
   ```

2. **Migrate the document.** Open the document in an AI session and say
   *"Migrate to research-buddy vX.Y"*. The agent will update the JSON
   structure to match the new schema. The build is not blocked meanwhile;
   output may be wrong until migration is complete.

## [1.0.3] — earlier releases

Not tracked in this file. See `git log` for history prior to 1.1.0.
