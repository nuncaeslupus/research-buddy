# CLAUDE.md

Short project map for future sessions. If something below is wrong, trust the code, fix this file.

## Read first: `status/`

At the start of every session, read both files in `status/` for context:

- `status/plan.md` — improvement roadmap (numbered steps, in order, with
  shipped items checked off) plus a "Future improvements" backlog. Slow-
  changing, strategic. Check here to see what the next step is and why the
  ordering was chosen.
- `status/next-session.md` — append-only session log. Each entry: what was
  done, next steps, blockers. Tactical, updated at the end of each session.
  Check here for the most recent context (PR numbers, decisions, stale
  items flagged in earlier sessions).

Update `next-session.md` at the end of a session when meaningful work shipped
or the next steps changed. Update `plan.md` only when the roadmap itself
changes (step completed, new step inserted, ordering revised).

## What this repo is

`research-buddy` — a CLI that turns a versioned **v2 Markdown** research
document into a single-file HTML page. Installed as a package; the CLI entry
point is `research_buddy.main:main`. Agents (humans or LLMs) edit the source
file; this tool renders it. The source file is the source of truth.

**v2 Markdown** — YAML frontmatter + Markdown body with HTML-comment anchors.
Source is `*_v*-source.md` (full framework, agent-edited); the clean view
`*_v*.md` (framework stripped) and HTML are derived.

**v1 JSON was removed in v2.0.** The only remaining v1 surface is
`research-buddy migrate-v1-to-v2`, which converts a legacy v1 JSON document to a
v2 `*-source.md`. (History: v1 was the original format; v2 became default in 1.5;
all other v1 paths — build/validate/upgrade/`init --v1` — were removed in 2.0.)

## Layout

```
src/research_buddy/
  main.py              # thin façade: re-exports `main` + command handlers for back-compat
  cli.py               # argparse parser (build_parser) + dispatch (main)
  commands/            # one module per subcommand
    _shared.py         #   _load_starter_md_text (v2 starter loader)
    build.py           #   build  (perform_build_md, cmd_build)
    validate.py        #   validate
    clean.py           #   clean
    bump.py            #   bump   (v2 Turn-2 mechanical edits; cmd_bump)
    locate.py          #   locate (live @end insertion point; cmd_locate)
    diff_summary.py    #   diff-summary (mechanical Turn-2 summary; cmd_diff_summary)
    turn1.py           #   turn1 (pre-filled brief skeleton; cmd_turn1)
    migrate.py         #   migrate-v1-to-v2 (legacy escape hatch)
    init.py            #   init (+ _set_frontmatter_scalar, _init_v2)
    upgrade.py         #   upgrade (+ _upgrade_md_file)
  chrome.py            # shared HTML chrome (Jinja env, asset loading, BuildState,
                       #   footer, lang resolution) used by build_md + migrate
  build_md.py          # v2 MD  → HTML (chrome from chrome.py; localizes headings; sanitizes)
  sanitize_html.py     # render-time HTML sanitizer (nh3) for agent-authored fragments
  upgrade_md.py        # v2 framework refresh: re-sync framework block + frontmatter from starter.md
  validator_md.py      # v2 mechanical validator (frontmatter, anchors, links, IDs, prior diff)
  clean_md.py          # v2 source MD → clean MD (strip framework + agent preamble, regen title)
  bump.py              # v2 Turn-2 mechanical edits (queue→tracker, stubs, version/date)
  turn1.py             # v2 Turn-1 brief skeleton, pre-filled from frontmatter + top queue row
  localize.py          # HTML-render section-heading labels per language (display-only; slugs stay English)
  diff_summary.py      # v2 old→new diff → mechanical @summary block
  migrate_v1_to_v2.py  # v1 JSON  → v2 MD source (the only v1-reading code)
  fileio.py            # shared file-I/O: read_text_or_error (UTF-8 guard) + atomic_write
  starter.md           # v2 session-zero template, bundled in the wheel
  css/ js/ lib/ images/  # assets inlined into the generated HTML
scripts/
  sync_version.py         # Source of truth = pyproject.toml; rewrites the other files
  check_version_sync.py   # Read-only: fails if any version string drifted. Used by CI.
  check_examples_sync.py  # Read-only: fails if committed starter-example/*.html drifted. Used by CI.
tests/            # pytest; class-grouped, TDD by convention
  fixtures/v1_starter.json  # representative v1 doc — test data for migrate (not shipped)
starter-example/  # starter-md.html (v2)
Makefile          # make sync | lint | format | test | test-cov | regen-examples | check-examples-sync | build | publish | version-sync | check-version-sync
```

## Commands (prefer Make)

| Command                  | What it does                                                                |
| ------------------------ | --------------------------------------------------------------------------- |
| `make sync`              | `uv sync --extra dev` — install dev deps                                    |
| `make test`              | `pytest tests/ -v` — full suite, fast and ungated (local iteration)        |
| `make test-cov`          | Full suite + coverage gate (`--cov-fail-under=85`). CI's test job uses this |
| `make lint`              | `ruff check` + `ruff format --check` + `mypy` (mirrors CI)                  |
| `make format`            | `ruff check --fix --unsafe-fixes` + `ruff format`                           |
| `make regen-md-example`  | Rebuild `starter-example/starter-md.html` from `starter.md`                 |
| `make regen-examples`    | Alias for `regen-md-example`                                                |
| `make check-examples-sync`| CI gate: fails if either committed `starter-example/*.html` has drifted    |
| `make version-sync`      | Propagate `pyproject.toml` version into the three downstream files         |
| `make check-version-sync`| CI gate: fails if any of the four version strings have drifted              |
| `make build`             | Produce wheel + sdist in `dist/`                                            |
| `make publish`           | `build` then `twine upload` (requires PyPI creds)                           |
| `make update-skills`     | `git subtree pull` latest shared skills from the `shared-skills` remote     |

Don't call `ruff` / `mypy` / `pytest` directly unless debugging — Make targets
keep things consistent with CI.

## Pre-commit hooks

After a fresh clone, install the git hooks once:

```
uv run pre-commit install
```

From then on every `git commit` runs `ruff check`, `ruff format --check`,
`mypy`, and `make check-version-sync` — the same four steps as the CI lint
job. Config lives in `.pre-commit-config.yaml`; all hooks invoke tools via
`uv run` so their versions come from `uv.lock` (no drift vs. CI).

To run the full battery on-demand: `uv run pre-commit run --all-files`.

## Versions

Four places hold the version, one source of truth:

- `pyproject.toml` — canonical (`version = "…"`)
- `src/research_buddy/__init__.py` — `__version__ = "…"` (rewritten by `sync_version.py`)
- `src/research_buddy/starter.md` — `research_buddy_version` in YAML frontmatter (same)
- `README.md` — `# Research Buddy v…` heading (same)

Workflow on a bump: edit `pyproject.toml`, run `make version-sync`, commit. CI's
`make check-version-sync` catches drift; `tests/test_version_sync.py` is the
local belt-and-suspenders.

Releasing is automatic. `.github/workflows/release.yml` runs on every push to
`main`: if `pyproject.toml`'s version has no `vX.Y.Z` tag yet, CI tags the
commit, builds, publishes to PyPI (trusted publishing / OIDC), and cuts a
GitHub release. So **merging a version bump to `main` is the release** — no
manual `git tag` / push. Pushes that don't introduce a new version are a cheap
no-op. `make publish` remains only as an emergency fallback: it uploads to
PyPI **without** creating the `vX.Y.Z` tag, so a later merge of that version to
`main` would see no tag, attempt to release, and fail at the upload step with a
"file already exists" error. Don't use it in the normal flow — let the merge
release.

v2 documents record `research_buddy_version` but there is **no active
version-compatibility gate** — the field is checked only for presence, and the
agent updates it on each Turn 2 write. (The v1 MAJOR/MINOR comparison in
`validator._check_version_compatibility` went away with v1 in 2.0.)

## Tests

Plain pytest, class-based for grouping but no inheritance magic. One shared
fixture lives in `tests/conftest.py`:

- `starter_doc` → fresh `dict` from `tests/fixtures/v1_starter.json` (a
  representative v1 document; used by the `migrate-v1-to-v2` tests, the only
  place a v1 doc is still exercised).

Tests that compare versions read `from research_buddy import __version__` — do
not hard-code a literal, it will silently rot. `_parse_semver` now lives in
`upgrade_md.py` (its only remaining caller).

## 2-turn agent workflow (what the tool supports)

1. User runs `research-buddy init my-project/` → produces
   `source/research-document.md` (the bundled v2 starter).
2. User uploads that source file to an LLM chatbot.
3. Agent runs session_zero (reads the in-file framework), returns the
   versioned source — `{file_name}_v1.0-source.md`.
4. User saves that file, runs `research-buddy build <source>.md` →
   produces `versions/[file_name]_v1.0.html` + stable `[file_name].html`.
5. Subsequent sessions: upload latest source, say "Continue research".
   Agent does one research topic per session in exactly two turns, then
   writes a new versioned source + HTML.

## Optional extras

- `pip install -e ".[dev]"` — dev tooling (pytest, ruff, mypy, build, twine,
  pre-commit, mutmut).

## Non-obvious things

- **`main.py` is a re-export façade.** Command logic lives in
  `cli.py` + `commands/*`; `main.py` just re-exports `main` (the
  console-script entry point) and the handlers/helpers so
  `from research_buddy.main import cmd_build` etc. still resolve.
  Consequence for tests: monkeypatch a command's dependency on
  **its own module**, e.g. `research_buddy.commands.build.validate_md`,
  not `research_buddy.main.validate_md` — the patched name must match
  where the function does its global lookup.
- **`build` is v2-only.** It accepts `.md` source files; a non-`.md` path is a
  clean error (v1 JSON support was removed in 2.0). `build_md_html` strips the
  framework block by default (the framework is for the agent reading the source,
  not for HTML readers); pass `keep_framework=True` programmatically to keep it.
- **v2 build safety (PR-8).** `perform_build_md` **gates the render on
  validator errors** — error-severity issues abort the build (exit 1, no HTML
  written); warnings don't block. Render hardening: tab labels are
  `html.escape`d into `data-tab-label`; `_md_render_inline` flattens
  multi-paragraph input to `<br><br>` (no `<p>` children inside an inline
  `<li>`); `chrome._neutralize_style_close` backslash-escapes any `</style>` in
  user theme CSS before it's inlined into the `<style>` block (Jinja runs
  `autoescape=False`). The validator also warns
  (`unsafe-html-{script,event-handler,js-uri}`) on `<script>` / inline `on*=` /
  `javascript:` in the body outside fenced/inline code — the LLM-authored-HTML
  trust surface; warnings, not errors, so an illustrative example still builds.
- **v2 HTML sanitization (trust model).** The validator only *warns* about
  active HTML; `sanitize_html.py` is the render-time backstop that actually
  removes it. `build_md` runs every **agent-derived** fragment — each tab's
  rendered body, the frontmatter `banners`, and the tab labels — through
  `sanitize_html` (`nh3`/ammonia) with an allowlist matched to the renderer's
  output + starter.md's Element catalog (block/inline tags, `<svg>` + its static
  children, `span`/`div` with any class, `<a id>`, `<col style="width:…">` via a
  `filter_style_properties` allowlist). It strips `<script>` (+ contents),
  `on*=` handlers, `javascript:`/`data:` URIs (default ammonia `url_schemes`),
  `<iframe>`/`<object>`/`<foreignObject>`/`<animate>`, and anything unlisted —
  so **inline SVG is rendered but sanitized as untrusted**. `strip_comments=False`
  (keeps `<!-- @anchor -->`), `link_rel=None` (no `rel` spam on internal links).
  The **trusted chrome is NOT sanitized** (it carries the app's own
  `<script>`/`data-tab`); instead the frontmatter scalars injected into it
  (`title`/`version`/`date` → `<title>`, footer, sidebar) and `lang_code` (→
  `<html lang>`) are `html.escape`d in `build_md`, closing the
  `title: </title><script>…` breakout. Sanitizing the *rendered* HTML (not the
  source) is deliberate: markdown-it has already escaped fenced/inline code, so
  a `<script>` shown as a code example survives while a live one is stripped.
  `nh3>=0.3.0` is a core dependency (`filter_style_properties` landed in 0.3.0).
- **`bump` writes a NEW versioned file, never in place.** `research-buddy
  bump <file>_vX.Y-source.md Q-NNN --apply` emits
  `<file>_vX.(Y+1)-source.md` (MINOR bump) and validates it with the input
  as `--prior`, so anchor-preservation + append-only invariants are checked
  on the way out. It does the mechanical Turn-2 edits only (queue→tracker
  move, session/changelog/references stubs, frontmatter version+date) and
  leaves `{{placeholders}}` for the agent to fill. Pure text transforms live
  in `bump.py`; the file I/O + guards live in `commands/bump.py`. Refuses
  starter files and unknown queue IDs.
- **`locate` / `diff-summary` are read-only agent helpers.** `locate
  <file>.md <anchor>` prints the line of the *live* `<!-- @end: <anchor> -->`
  marker plus context — it matches **full-line** markers outside fenced blocks
  (reusing `validator_md._line_in_fence`), so inline prose mentions and fenced
  template examples never collide. `diff-summary <old>.md <new>.md` emits the
  mechanical part of the Turn-2 `@summary` block (version bump, queue→tracker
  moves, rules added/revised, DAs/sessions added, append-only PASS/FAIL),
  leaving the narrative as a `{{placeholder}}`; exit 1 signals an append-only
  violation. Logic in `diff_summary.py`; both handlers in `commands/`.
- **`turn1` is a read-only brief-gate helper.** `research-buddy turn1
  <file>.md` prints the Turn-1 second-opinion brief wrapped in real
  `<!-- @brief-start -->` / `<!-- @brief-end -->` markers, pre-filled from the
  frontmatter (project description, source tiers, fixed Never-tier) plus the
  first live Open Research Queue row (topic + objective, reusing `bump`'s
  comment-aware row parser). Judgment slots (relevant DAs / tracker rows /
  rules, hypotheses, excellence bar) stay `{{placeholders}}`; guidance prints to
  stderr so the stdout block is clean to paste. The body mirrors the canonical
  brief template in `starter.md` — keep them in sync. Refuses starter files.
  Pure logic in `turn1.py`; handler in `commands/turn1.py`. Surfaced in the
  starter preamble + brief-template section as the "fill, don't remember" path.
- **`clean` strips the agent preamble, not just the framework.** The operating-
  manual HTML comment between the frontmatter and `<!-- @anchor: title -->`
  references the framework (`read [Framework (Core)](#framework-core)`, "emit the
  brief") — which `clean` removes. Leaving it would point an agent at sections
  that no longer exist (and `unwrap_framework_links` would rewrite those links to
  dangling plain text). So `clean_md.strip_agent_preamble` replaces the preamble
  with a one-line self-identifying note pointing back at the `*-source.md`. The
  HTML build never carried the preamble (it sits before the first H2, which
  `split_into_tabs` drops). This is the fix for "agent skipped the brief because
  the uploaded file had no framework" — usually a clean view uploaded by mistake.
- **`clean` is fence-aware and EOF-safe.** `collect_framework_targets` skips
  lines inside fenced blocks (reusing `validator_md._line_in_fence`): the
  framework's `### Templates` examples carry placeholder headings + `<a
  id="q-001">`-style anchors that are NOT real targets — collecting them would
  make `unwrap_framework_links` strip a legitimate body link like
  `[Q-001](#q-001)` (a promoted tracker row) down to plain text. Separately,
  `strip_framework_block`'s malformed-opener path (a `framework.core` anchor with
  no matching `@end`) preserves the opener + every remaining line verbatim
  instead of `break`ing, which used to silently drop everything from the opener
  to EOF.
- **HTML localizes section headings; slugs stay English.** `build_md` displays
  framework headings ("Open Research Queue", "References", the Project-Spec H3s)
  in the doc's `language.code` while keeping the English slug/id (tab `data-tab`,
  `tab-{id}`, heading `<a id>`) so `[Queue](#open-research-queue)` cross-links
  never break. Table in `localize.py` (ships `es`); frontmatter `section_labels`
  (English heading → label) overrides/extends it and enables unshipped languages.
  Display-only: the clean-view **Markdown keeps English headings** (there a
  heading's slug *is* its text). The legacy `ui_strings` frontmatter is a v1
  carryover — **not rendered in v2** (no fixed status column); the agent writes
  status text / `rb-ok`/`rb-flag` chips directly in the doc language.
- **Starter marker hygiene is invariant-tested.** Every live `<!-- @end: X
  -->` marker is the unique occurrence of `@end: X` in `starter.md` (so an
  agent grep for an insertion point gets one hit). Prose that used to embed
  the literal marker now says "this section's closing `@end` marker".
  `tests/test_starter_hygiene.py` enforces this; reintroducing a literal
  marker mention in starter prose will fail it.
- **v2 anchors are load-bearing.** `<!-- @anchor: X -->` ↔
  `<!-- @end: X -->` and `<!-- @rule: R-XXX-N -->` ↔
  `<a id="r-xxx-n"></a>` are the anchor system the validator
  protects. `validate --prior` enforces append-only invariants
  (anchors / DAs / changelog / references never disappear). Renaming
  an anchor is a breaking change.
- **Append-only coverage + structural checks (PR-2).** `_check_append_only`
  also preserves **Research Tracker rows** (`Q-`/`T-` first-column ids; the seed
  `T-000` is exempt) and **individual reference bullets** (the H3 check only
  caught whole per-version subsections). Session ids need no separate check —
  `_collect_anchors` already collects `@session` markers, so a removed session
  fires `anchor-removed`. `_collect_entry_ids` is now fence-aware (a `@da`/`@rule`
  in a fenced template example isn't a live entry). `validate_md` runs
  `_check_unclosed_fence` (an open ``` with no closer is an error pointing at the
  opener — otherwise it silently swallows the rest of the doc). A
  `broken-cross-link` is now an **error** (was a warning), except for the
  starter's illustrative example targets, which stay `info`.
- **`doc_format_version` vs `research_buddy_version`.** The frontmatter
  field `doc_format_version: 2` is the *format generation* — it bumps
  when v2 itself changes shape (rare). `research_buddy_version` is the
  *tool version* and tracks `pyproject.toml`. The legacy `format_version`
  key is still accepted by `validator_md.py` and `clean_md.py` but emits
  a `deprecated-format-version-key` warning; `research-buddy upgrade
  <file>.md --apply` renames it (and refreshes the framework block
  + adds missing `project.source_tiers` / `project.domain_rules`
  frontmatter fields) on existing v2 docs.
- **`*.md` ships in the wheel.** `[tool.setuptools.package-data]`
  globs include `*.md` so `starter.md` is available via
  `importlib.resources` after `pip install`. Without this glob,
  `migrate-v1-to-v2` would fail at runtime (it loads the v2 framework
  block from the bundled starter).
- **`migrate_v1_to_v2` guards a few collision classes.** Queue-ID synthesis is
  two-pass (collect existing inline + tracker `Q-NNN`, then assign the lowest
  free one) so an auto-ID never dups a tracker or inline ID. Changelog sort is
  patch-aware (`_key` → 3-tuple) and entries render `### vX.Y — DATE`. Verdict
  `<a id>`s go through `_slug` (idempotent for well-formed `R-`/`DA-` ids).
  `build_domain_tab` suffixes a label that slugs to a `CANONICAL_ANCHORS` member
  with `-tab` so it can't clobber the framework's own anchor. `build_frontmatter`
  carries `project.source_tiers` + `project.domain_rules`. Still open (PR-7b):
  verdict-label dedup needs renderer-wide `seen_ids` threading; no marker is yet
  emitted when content (e.g. `Research Methodology`) is intentionally dropped.
- `language` accepts both a string ("English") and an object
  (`{"code": "en", "label": "English"}`). The string form is mapped to a BCP-47
  code via `_LANGUAGE_NAME_TO_CODE` in `chrome.py` (`_resolve_lang_code`);
  unknown names fall back to the first token truncated to 10 chars. Inline SVG is
  sanitized as untrusted at render time (see the trust-model note above), not
  passed through verbatim.
- **`fileio.py` centralizes two file-I/O concerns.** `read_text_or_error(path)`
  reads UTF-8 and raises `FileReadError` on invalid bytes (so a `.md` source or
  `theme.css` with bad bytes reports cleanly instead of tracebacking — parity
  with the JSON reads PR #93 hardened); callers catch it, print to stderr, return
  a non-zero code. `atomic_write(path, text)` does temp-sibling-write→rename with
  `try/finally` cleanup, so a failed write leaves no `.tmp` behind. Used by
  `build` (the v2 source + theme reads) and the atomic writers (`bump`, `upgrade`,
  `migrate`, `init`). The bundled-starter loads (our own ASCII via
  `importlib.resources`) stay unguarded — they're not user input and use a
  `Traversable`, not a `Path`.
- CI (`.github/workflows/ci.yml`) runs lint on 3.12 only, tests on 3.11 + 3.12.
  `make check-version-sync` is part of the lint job.
- `tmp/`, `.vscode/`, `dist/` are gitignored. `starter-example/` is committed
  so users can view the example without installing the package.
- `.claude/skills/` is imported from a shared repo via `git subtree` from
  `https://github.com/nuncaeslupus/my-skills.git`. `make update-skills` pulls
  the latest. Project-specific skills can be dropped alongside the shared ones
  — subtree won't touch them.
