# Next session

## Session 2026-05-12 (session 16)

### What was done

- **Starter hardening — 1.8.0 → 1.9.0 (single PR).** Eight
  changes to `src/research_buddy/starter.md` driven by a postmortem
  from a downstream agent that mis-ran session zero. All targeted
  at making the first-touch experience harder for an LLM to
  misread.
  1. **Unmissable AGENT preamble** as the first content after the
     YAML closing `---` — multi-line HTML comment (invisible to
     human Markdown viewers, visible to any agent reading raw)
     stating STOP, read the file, deliverable is a versioned `.md`
     file, NOT a chat response. Survives clean view.
  2. **New `agent_state` frontmatter field** with values
     `needs_session_zero` | `ready`. Replaces "`project.domain`
     null means session zero" with a literal state token the agent
     must overwrite in session zero Turn 2. Backwards-compatible:
     framework's "Detect session state" rule has a fallback for
     pre-1.9 docs without the field. `upgrade_md.py` backfills
     `agent_state: ready` for existing v2 docs (a doc reaching
     upgrade is by definition post-session-zero).
  3. **Chat-output anti-pattern** as the first bullet of
     [Common failure modes] — `[mechanical]` catches the meta-
     failure of producing the session output as a chat response,
     artifact, or anything other than the versioned source file.
  4. **Session-zero Turn 1 mode-switch (3 cases).** First message
     is (a) generic kickoff → print welcome + 5 questions; (b)
     already supplies the 5 answers explicitly or by inference →
     skip the questions, both turns ship in one message; (c) a
     research request rather than a project spec → run session
     zero with the request as the implicit spec and seed it as
     Q-001. (b) and (c) suppress the Turn 1 marker.
  5. **Forward-reference convention** explicit: pending queue
     items (rows still in the queue, not yet promoted to Tracker /
     Session Notes) have NO `<a id>` target — reference them as
     plain text `Q-NNN`, not as a Markdown link. The "always
     link" rule excludes them. Mechanical detection via
     `validate`.
  6. **Templates extracted to a dedicated `### Templates`
     subsection inside framework.reference.** The three quadruple-
     backtick example blocks (rule, DA, session) used to live
     inside `## Adopted Rules` / `## Discarded Alternatives` / `##
     Session Notes`. They were a footgun for naive
     `str_replace` — easy to wreck the template when "appending
     before @end". Now the user sections are content-only
     between anchor and @end; templates live in one canonical
     place, fenced.
  7. **Self-install instruction** in [Self-validation]: when the
     agent has shell access but `research-buddy` is missing, run
     `pip install research-buddy` first. Real validation beats
     mental simulation; one-time install removes the "simulated
     PASS, actual FAIL" failure class. Includes PyPI URL and
     fallback notes.
  8. **Version bump 1.8.0 → 1.9.0** (MINOR — additive, fully
     backwards-compatible). `make version-sync` propagated; lint
     clean; **320 tests pass** (319 + 1 new
     `test_inserts_missing_agent_state` for the upgrade backfill).
- **`upgrade_md.py` change.** New `_ensure_agent_state` helper
  follows the existing `_ensure_project_*` pattern: inserts
  `agent_state: ready` immediately after `research_buddy_version:`
  when the field is absent (pre-1.9 docs). One test added; 18
  upgrade tests green.
- **Single-PR slicing was the user's call** at the start of the
  session — bundled all eight changes (originally seven from the
  postmortem + the self-install instruction added mid-session) so
  the regen + version-sync + tagged release happen once, not
  eight times.

### Next steps

1. **Open the PR** for `feat/starter-hardening-1.9.0` against
   main. Branch is local-only at session end; commit is queued
   but unpushed (user did not explicitly ask to push).
2. **Tag + publish 1.9.0** after merge: `git tag v1.9.0 && git
   push --tags`, then `make publish` (PyPI token in `~/.pypirc`
   from session 14 still works headlessly).
3. **Backport forward-only version policy to v1 `upgrade.py`** —
   still carried from session 13/14. Cheap fix (~10 lines + one
   test); the v1 path still blindly overwrites
   `meta.research_buddy_version`.
4. **Postmortem item #8** (the ~10k-token framework overhead) is
   the unaddressed survivor from this batch — needs a real
   design pass. Idea was "framework-cheatsheet.md alongside a
   much shorter source file" so the per-session overhead drops.
   Not in scope for 1.9.0; opens a separate work stream.
5. **Carry-overs**: roadmap step #6 (coverage on `main.py` /
   `validator.py`); roadmap #7/#8/#9 (mutmut, coverage gate,
   split `main.py`) still deferred.

### Blockers

- None.

---

## Session 2026-05-10 (session 15)

### What was done

- **Three-PR series shipping the v2 element catalog.** Single
  MINOR (1.7.0 → 1.8.0) at the end of γ, as agreed up-front so
  vocabulary teaching, algorithmic chrome, and renderers all
  arrive in one tagged release.
  - **PR [#79] α — element-catalog teaching.** Single compact
    table in `framework.reference` listing 18 elements + 7 callout
    kinds + 2 algorithmic items. Closed list — `Anything not
    listed here should be expressed as ordinary prose, lists, or
    tables`. The catalog is the renderer contract.
  - **PR [#80] β — algorithmic items.** New shared
    `table_layout.py` (content-based, language-independent column
    widths via per-column `p50/p90/has_spaces/is_token` profile,
    with structural signature grouping so similar tables align).
    Numbered H3/H4 in v2 matching v1's `<span class="num">`
    chrome. Both pipelines reuse the same module. 18 new
    `test_table_layout.py` tests + 5 nav-numbering tests; 282
    total. Replaced the English-keyword heuristic
    (`build/test condition/rejected` header matching) — works in
    any language, never matches words.
  - **PR [#81] γ — renderers.** GFM admonitions (`> [!KIND]`)
    for the 7 catalog kinds (NOTE/TIP/IMPORTANT/WARNING/CAUTION
    + research-specific LIMITATION/HYPOTHESIS); `rb-verdict`,
    `rb-cards`, `rb-banner` fenced-block renderers (YAML body
    where structured); references-anchor styling (compact `<ul
    class="references">` after `<!-- @anchor: references -->`,
    with anchor-before-H2 detection so the framework convention
    of placing the anchor *outside* the H2 still works);
    `.rb-ok` / `.rb-bad` / `.rb-flag` inline chip CSS (raw
    `<span class>` passes through markdown-it's `html=True`,
    needs no renderer); frontmatter `banners` (rendered above
    the first tab) and `theme_css` (cascade: CLI flag > FM
    field > conventional `theme.css`). 37 new tests; 319 total.
- **Single MINOR bump** 1.7.0 → 1.8.0 covers all three. The
  starter / API stays backwards-compatible: a 1.7.x doc still
  renders cleanly under 1.8.x because the renderers fail-closed
  on unknown fence kinds (unknown `rb-verdict <kind>` falls
  through to a plain code block, never crashes).
- **Gemini review on [#81] — three MEDIUMs, all accepted.** All
  three flagged the same root cause: wrapping rendered Markdown
  body in `<p>` produced invalid `<p><p>…</p><p>…</p></p>` when
  the input had multiple paragraphs (`_md_render_inline` only
  strips the outer `<p>` for single-paragraph results). Fix
  splits the helper into two: `_md_render_inline` (inline-context
  slots like `<li>`) and `_md_render_body` (block-context slots
  like card / banner / verdict bodies, keeping the `<p>` wrapping
  intact). Cards / agnostic / cc banners switched from `<p>{body}</p>`
  to `<div class="card-body|banner-body">{body}</div>`. Three
  regression tests pin `<p><p>` and `</p></p>` are absent across
  cards / agnostic / cc banner outputs.
- **Why text-level admonition expansion vs. token-level.**
  markdown-it-py's inline `children` aren't trivially re-parseable
  after stripping the `[!KIND]` prefix; a regex-driven text
  rewrite (respecting fence state via `_line_in_fence`) is
  simpler and equally correct. Token-level is used for `rb-*`
  fences because their YAML bodies need structured parsing.
- **Why a `_references_tab_index` pre-scan.** The framework
  convention places `<!-- @anchor: NAME -->` *before* the
  `## NAME` heading. After tab splitting, the comment is
  filtered out of the next tab's body. Detecting the
  comment→H2 mapping up front and arming the right tab is
  cheaper than moving the comment in the source (which would
  break the file-editing rule "anchors are sacred").

- **Release.** `v1.8.0` tagged and pushed; **wheel + sdist
  published to PyPI** via `make publish` (the headless setup
  from session 14's `~/.pypirc` API token still works — no
  re-auth needed).

[#79]: https://github.com/nuncaeslupus/research-buddy/pull/79
[#80]: https://github.com/nuncaeslupus/research-buddy/pull/80
[#81]: https://github.com/nuncaeslupus/research-buddy/pull/81

### Next steps

1. **Roadmap forward.** Step #1 of the v2 polish run was the
   element catalog (now done). The pre-existing roadmap items
   in `status/plan.md` are the next pickup — pre-commit hooks
   were shipped in session 12, so the next outstanding item is
   whatever sits below that in `plan.md`.
2. **Dogfood**: agents using v1.8.0 should pick up the catalog
   from `framework.reference`. Worth surfacing a one-line
   "what's new" pointer in the next standard-session change
   summary so the discovery isn't silent.
3. **Existing-doc upgrade smoke test passed.** Mid-session
   verified `research-buddy upgrade` on a real downstream
   `claude-skill-system_v1.17-source.md` (1.6.0 → 1.8.0
   framework swap), and `research-buddy build` produced a
   1202 KB HTML cleanly. One pre-existing broken cross-link
   warning surfaced — content issue in the user's tracker, not
   a build regression.

### Blockers

- None.

---

## Session 2026-05-07 (session 14)

### What was done

- **PR [#76] merged** — *upgrade-md dispatch* (the v2 path
  authored in session 13). One Gemini MEDIUM landed before merge:
  `_find_framework_bounds` was matching marker lines by stripped
  equality only, so a fenced code example showing
  `<!-- @anchor: framework.core -->` or
  `<!-- @end: framework.reference -->` would shadow the real
  boundaries (end-detection's last-match rule means a bogus end
  inside a later fence wins). Fixed by reusing
  `validator_md._line_in_fence`; new test
  `test_ignores_marker_lines_inside_fenced_code_blocks` locks it
  in. Docstring on `_replace_framework_block` corrected — it had
  *claimed* to ignore in-fence markers but didn't.
- **PR [#77] merged** — *init defaults to v2 Markdown + bump
  1.7.0*. Two changes bundled because both ship in the same MINOR:
  - `research-buddy init <dir>` now scaffolds
    `source/research-document.md` (the bundled v2 starter) by
    default; `--v1` falls back to the legacy JSON scaffold. The
    starter's frontmatter is patched in place — `title` / `subtitle`
    set when `--title` / `--subtitle` are passed, every other
    value stays null for session zero. `cmd_init` is now a thin
    dispatcher; legacy logic lives in `_init_v1`, v2 in `_init_v2`.
    Frontmatter editing uses a small line-based helper
    (`_set_frontmatter_scalar`) that preserves YAML comments — same
    convention `upgrade_md` already uses for the same file shape.
  - **Version bump 1.6.0 → 1.7.0** (MINOR — additive: new `.md`
    dispatch on `upgrade` with the forward-only semver guard, and
    v2-default scaffolding on `init`).
- **Gemini review on [#77]** — two MEDIUMs, both accepted:
  1. **Quote escaping in `_set_frontmatter_scalar`.** A title with
     embedded `"` (e.g. `My "Awesome" Project`) would have produced
     invalid YAML. Fix backslash-escapes `\` and `"` before wrapping
     in YAML's double-quoted form. New
     `test_init_escapes_double_quotes_in_title` round-trips through
     `yaml.safe_load`. The `# inside an existing quoted value`
     sub-concern was documented as a precondition rather than coded
     against — `init`'s only call sites operate on the fresh
     starter's `null` lines (no embedded `#`), so the helper's naive
     ` #` comment-split is safe in practice.
  2. **Placeholder style alignment.** v1 init's success message uses
     `[meta.file_name]`; v2 was using `{file_name}`. Aligned v2 to
     `[file_name]_v1.0-source.md` so the square-bracket "substitute
     this" idiom is consistent across both paths.
- **Tests / lint.** 254 → 261 pass (+1 for fence-skip on PR 76,
  +6 for v2 init / -2 from v1 reframing on PR 77, +1 for
  quote-escape regression on the Gemini fix). Lint clean.
  `make regen-examples` ran clean (only version-footer diff in the
  rendered HTML).
- **Docs.** README quick-start now leads with the v2 flow and
  points at `--v1` for legacy projects; the `init` section
  documents both paths. CLAUDE.md's 2-turn workflow narrative
  updated to match (v2 default; `--v1` legacy fallback).
  `main.py` module docstring changed from "init still scaffolds
  v1" to "init defaults to v2 Markdown".
- **Release.** `v1.7.0` tagged on the `[#77]` merge commit and
  pushed to GitHub; **wheel + sdist published to PyPI**
  (https://pypi.org/project/research-buddy/1.7.0/).
- **Headless publish setup.** `~/.pypirc` now holds a
  PyPI API token (`username = __token__`, `chmod 600`), so
  `make publish` works without a TTY going forward. First attempt
  in this session failed with 403 because the pasted token was
  truncated (length 41 — real PyPI tokens are ~200 chars; the
  wrap on PyPI's display tripped the copy). After regenerating
  and pasting the full token (length 215), upload succeeded.

### Next steps

1. **Backport forward-only version policy to v1 `upgrade.py`** —
   carried from session 13. The v1 path still blindly overwrites
   `meta.research_buddy_version` (silent downgrade hazard same as
   v2 had). Cheap fix (~10 lines + one test). Lands as 1.8.0 or
   gets deferred until someone hits it.
2. **Carry-overs**: v2 build fidelity vs v1 `starter.html`
   (callouts, fixed-width tables, numbered subheadings); roadmap
   step #6 — coverage on `main.py` / `validator.py`. Roadmap
   #7/#8/#9 (mutmut, coverage gate, split `main.py`) deferred
   again.

### Blockers

- None.

[#76]: https://github.com/nuncaeslupus/research-buddy/pull/76
[#77]: https://github.com/nuncaeslupus/research-buddy/pull/77

---

## Session 2026-05-07 (session 13)

### What was done

- **PR [#75] merged** — *framework hardening: write second-opinion
  brief before any research tool call.* Convert the brief guarantee
  from temporal ("compose before research, emit after") to spatial
  ("write into the outgoing response buffer before any tool call").
  Turn 1 step 5 now says "write the brief into the response, with
  `@brief-start`/`@brief-end` markers, BEFORE invoking any research
  tool" plus a pre-tool-call self-check; step 7 appends findings
  beneath the already-emitted brief and adds an explicit "do not
  re-emit / re-edit / move" guard. Brief-template Composition rule
  reframed; failure-modes list got a sharper entry naming the actual
  failure mode (drafted in reasoning, never written into the
  response). No version bump — iterating before release.
- **`research-buddy upgrade` v2 dispatch shipped on branch
  `feat/upgrade-md`.** Closes the long-standing "upgrade-md" gap
  from session 12. `cmd_upgrade` now dispatches on file extension
  (`.json` → v1 path; `.md` → new `upgrade_md.py`). The v2 path
  replaces the framework block (between `<!-- @anchor: framework.core
  -->` and `<!-- @end: framework.reference -->`) with the installed
  starter's block, bumps `research_buddy_version` *forward only*,
  renames legacy `format_version` → `doc_format_version`, and inserts
  missing `project.source_tiers` / `project.domain_rules` frontmatter
  blocks with null values. Edits are line-based on the frontmatter
  so YAML comments survive. Atomic-write semantics + dry-run/
  `--apply`/`--no-validate` mirror the v1 contract.
- **Forward-only version policy is the one v1↔v2 semantic
  divergence.** v1 `upgrade.py` blindly overwrites
  `meta.research_buddy_version` with the installed value (downgrades
  silently). The v2 path raises `UpgradeError` when the doc is
  AHEAD of the installed tool, with a message telling the user to
  either upgrade the tool or manually edit the field. Surfaced
  during smoke-test on a real downstream doc that had been
  deliberately stamped at `2.0.0` to mark "framework version this
  doc was authored against" — silent downgrade would have lost user
  intent. Tested via `test_doc_ahead_of_tool_raises`.
- **New module `src/research_buddy/upgrade_md.py`** (~280 lines,
  pure logic); CLI helper `_upgrade_md_file` in `main.py`. 17 new
  tests in `tests/test_upgrade_md.py` (framework swap + frontmatter
  migrations + ahead-of-tool guard + CLI dry-run/apply/idempotent-
  apply). Full suite: 254 pass, lint clean.
- **Smoke-tested end-to-end on `claude-skill-system_v1.16-source.md`**
  (4793 lines). After resolving the version skew (2.0.0 → 1.6.0
  manually per the new error-path UX), `--apply` swapped the
  framework block cleanly: new step-5 spatial-guarantee wording
  landed, all 23+ project-specific terms preserved, post-write
  `validate` reported 6 broken-cross-link warnings — all
  pre-existing in the user's content, not caused by the upgrade.
  All 6 were also fixed in this session (cross-links repointed at
  the correct anchors; three flat-table rule rows gained inline
  `<a id>` tags so `[R-XXX-N](#r-xxx-n)` links resolve without
  promoting the rules to canonical `<!-- @rule: -->` blocks). Doc
  now validates clean.
- **Documentation refreshed:**
  - `README.md` — "How does it work" paragraph now says `build`,
    `validate`, **and `upgrade`** dispatch on extension; the
    `upgrade` command section documents both v1 and v2 modes with
    examples for each.
  - `CLAUDE.md` — layout adds `upgrade_md.py`; the stale
    "doc_format_version vs research_buddy_version" note now points
    at `research-buddy upgrade <file>.md --apply` as the official
    path for renaming legacy `format_version` and refreshing the
    framework block (the old wording said "planned upgrade-md
    command, see session 12").
  - `main.py` module docstring — the "remain JSON-only until the
    parallel MD scripts ship" note is gone; argparse help for
    `upgrade` documents both dispatch modes.

### Next steps

1. **Merge the upgrade-md PR**, then bump 1.6.0 → 1.7.0 (MINOR — new
   `.md` dispatch path on `upgrade`, additive on the v1 side, plus
   the new forward-only semver guard). Run `make version-sync`,
   `make regen-md-example` (no-op expected since framework is
   stripped from the rendered example), tag, `make publish`.
2. **Decide whether to backport the forward-only version policy to
   v1 `upgrade.py`.** The v1 path still blindly overwrites
   `meta.research_buddy_version` — same hazard. Cheap fix
   (~10 lines + one test) but a behavioural change for v1 users;
   could land as 1.8.0 or be deferred until someone hits it.
3. **Carry-overs** from session 12 still live: `init` should default
   to v2 MD scaffolding (currently v1 JSON only); v2 build fidelity
   vs v1 starter.html (callouts, fixed-width tables, numbered
   subheadings); roadmap step #6 — raise coverage on `main.py` /
   `validator.py`. Roadmap items #7/#8/#9 (mutmut, coverage gate,
   split `main.py`) deferred again.

### Blockers

- None.

[#75]: https://github.com/nuncaeslupus/research-buddy/pull/75

---

## Session 2026-05-07 (session 12)

### What was done

- **Closed PR [#71] and replaced with PR [#72]** (`refresh-starter-framework`).
  PR 71 was a GitHub-UI direct edit that:
  (a) accidentally truncated 18 long lines in `starter.md` to `[...]`
  (paste-from-Read-tool artifact in commit `2441fce`), and
  (b) used `tier1_contradiction` / `FALSIFIED` (Gemini caught both).
  PR 72 starts from `67ef215` (last clean commit) and folds in 22
  surgical instruction updates from the user's draft.
- **Substantive framework changes** in `starter.md` (PR 72):
  - Turn 1 reorders to **brief + research**: brief is composed in step 5
    *after* hypotheses are pre-registered in step 4 (Gemini caught the
    initial 4↔5 ordering — both pre-reg and brief reference each other).
    The brief is emitted verbatim and can never be re-edited after
    research.
  - Turn 2 becomes **vet + validate + atomic write**. Validation moved
    from `SHOULD` → `MUST`: the agent MUST invoke
    `research-buddy validate` (or paste a mental-simulation checklist
    when shell access is missing) and the validator output MUST appear
    in the message *before* the file artifact.
  - New **session-start version-compatibility check**: agent compares
    the doc's `research_buddy_version` against the loaded framework
    version, surfaces MAJOR mismatch as a one-line warning before any
    work, advisory only.
  - **`format_version` renamed to `doc_format_version`** to disambiguate
    from `research_buddy_version`. Deprecation fallback in
    `validator_md.py` and `clean_md.py` so v2 files predating the
    rename still validate (with a `deprecated-format-version-key`
    warning).
  - Frontmatter now declares `project.source_tiers`
    (tier_1 / tier_2 / discovery) and `project.domain_rules` — fixes
    the previously-dangling `{{project.source_tiers.tier1}}`
    references.
  - Adopted Rules gain `Status lifecycle` + `Force keywords (RFC 2119/8174)`.
  - Queue rules gain `Stable IDs` + `Re-queuing`. Open Research Queue
    has two ghosted example rows so session zero has Objective shape
    to pattern-match.
  - New **mechanical check** in `validator_md.py`:
    `brief-slot-empty-but-section-non-empty` — fires when the Turn 1
    brief context slot says "None." but the corresponding section
    (Discarded Alternatives / Tracker / Adopted Rules) has live
    entries. Tested in `TestBriefContextSlots`.
  - Synthesis matrix keeps `UNVERIFIABLE` alongside SUPPORTS /
    CONTRADICTS / SILENT (Gemini caught its removal from PR 72 commit 1).
- **Recovered the `[...]`-truncated lines** from `2441fce`. Identified
  the bad commit by diffing against `67ef215`. Process note: GitHub UI
  paste from a Read tool's truncated display is the likely cause —
  worth a guardrail.
- **Updated `claude-skill-system_v1.14.md`** (the user's research doc):
  re-injected the new framework block (334 lines, ~34 KB), added the
  agent-read directive to the title, renamed `format_version` →
  `doc_format_version`, populated `project.source_tiers` in
  frontmatter from the body content. All anchors balanced.

### Next steps

1. **Wait for CI on PR [#72]** and merge once green. After merge, bump
   to 1.6.0 (MINOR — new mechanical check, frontmatter additions,
   doc_format_version rename with deprecation fallback). Tag, publish.
2. **`upgrade-md` command — promoted from "lower priority" to active
   work.** With the framework just gaining substantive new directives
   (validation MUST, version-drift check, Stable IDs, Status
   lifecycle, brief composition timing), every existing v2 source
   document in the wild is now framework-stale. Need a dedicated
   command that mirrors `upgrade.py`'s contract for v1: re-sync the
   framework block (everything between
   `<!-- @anchor: framework.core -->` and
   `<!-- @end: framework.reference -->`) from the installed
   `starter.md` into an existing `*_v*-source.md`, leaving the project
   sections (and the title-section *body* below the framework
   directive) untouched. Should also rename `format_version` →
   `doc_format_version` if the legacy key is present, and add
   `project.source_tiers` / `project.domain_rules` placeholders to
   frontmatter if missing. Same atomic-write semantics as `upgrade`
   for JSON: one message, all changes, or report what would change
   with `--dry-run`.
3. **Carry-over** items from session 11 below remain valid (init
   scaffolding v1, build fidelity, coverage). The session-11 item #4
   about `upgrade-md` is superseded by the session-12 entry above.

### Blockers

- None. PR [#72] open with two commits + Gemini fixes folded in.

[#71]: https://github.com/nuncaeslupus/research-buddy/pull/71
[#72]: https://github.com/nuncaeslupus/research-buddy/pull/72

---

## Session 2026-05-07 (session 11)

### What was done

- **Shipped a six-stage v2-Markdown maturation plan** in five PRs
  off `main`. Plan committed as
  `.claude/plans/greedy-imagining-raven.md`. PRs #56–#61 had landed
  the v2 surface (starter.md, validator_md, clean_md,
  migrate_v1_to_v2) without tests, packaging, version-sync coverage,
  or MD→HTML build. This session closed those gaps and bumped to
  **1.5.0**.
- **PR [#64] — wheel ships `*.md`**. One-line addition to
  `[tool.setuptools.package-data]` so `starter.md` is bundled.
  Without it, `migrate-v1-to-v2` would fail at runtime via
  `importlib.resources` after `pip install`.
- **PR [#65] — version-sync covers starter.md.** Five sources now
  tracked instead of four. `scripts/sync_version.py` and
  `scripts/check_version_sync.py` extended; `migrate_v1_to_v2.py`
  sources `research_buddy_version` from the package `__version__`
  rather than hardcoding (no more drift). New
  `tests/test_version_sync.py` (5 tests). Decision after dialogue
  with user: MD tracks the wheel version (single source of truth) —
  `format_version: 2` is the orthogonal format-generation marker.
- **PR [#66] — full test coverage for v2 surface** (132 → 205
  tests). 73 new tests across `test_validator_md.py` (27),
  `test_clean_md.py` (20), `test_migrate_v1_to_v2.py` (26).
  Pattern matches `test_upgrade.py`. CI initially failed on
  `ruff format --check` (Makefile's `make lint` didn't include it);
  fix landed in the same PR — `make lint` now mirrors CI exactly.
  Gemini caught a brittle `"*" not in out.split(...)[1]...` assertion
  in `test_clean_md.py`; replaced with a structural check.
- **PR [#67] — `build_md.py` + main dispatch + v2 example**
  (Stages 4 + 6 combined). Adds `build_md_html(text, *,
  theme_css=None, keep_framework=False)` reusing the v1 chrome via
  `base.html.j2`. Each top-level `## H2` becomes a tab; `### H3` /
  `#### H4` feed the sidebar nav. Renders GFM tables, preserves
  raw HTML and `<!-- @anchor: ... -->` comments. New runtime deps:
  `markdown-it-py>=3.0`, `mdit-py-plugins>=0.4`. New
  `tests/test_build_md.py` (27 tests). `cmd_build` now dispatches
  on `.md`. `starter-example/starter-md.html` (195 KB) lands
  alongside the unchanged `starter.html` (190 KB after the 1.5.0
  bump). `make regen-md-example` and `make regen-examples` added.
  After user feedback, default behavior strips the framework block
  (matches `starter.html` semantics — agent-facing source ≠
  reader-facing artifact); `keep_framework=True` for the
  agent-source view. Starter-mode FILL placeholders carry over from
  v1 so the unconfigured starter renders comparably.
- **Version bump 1.4.0 → 1.5.0.** Decision made jointly: 1.5 is a
  MINOR (new build_md feature, new runtime deps, no breaking
  change to v1). MD set as the recommended format for new
  projects. JSON remains supported but marked deprecated in README
  + CLAUDE.md.
- **Docs (Stage 5).** README gains a "v2 Markdown (recommended)
  vs v1 JSON (legacy)" section; commands table extended with
  `clean`, `migrate-v1-to-v2`, and the v2 dispatch on `build` /
  `validate --prior`; examples section covers both starters.
  CLAUDE.md updated: layout includes the four new modules; commands
  table mentions `regen-md-example` / `regen-examples`; new
  "Non-obvious things" entries call out the build dispatch, the v2
  anchor system, the `format_version` vs `research_buddy_version`
  distinction, and the wheel package-data gotcha.

### Next steps

1. **Merge PR [#67]** (build_md + Stage 6 example) and the docs +
   1.5.0 bump PR (this session's last commit). After both land,
   `make publish` to PyPI as 1.5.0. Tag `v1.5.0`, push.
2. **`init` still scaffolds v1 JSON.** With v2 now the recommended
   format, `research-buddy init` should produce a v2 MD source by
   default (and probably gain a `--v1` flag for legacy JSON
   projects). Out of scope for this session; one focused PR.
3. **v2 build fidelity vs v1 starter.html.** `starter-md.html`
   (195 KB) is close to `starter.html` (190 KB) but the bodies
   look different: v1 renders rich blocks (callouts, fixed-width
   tables, numbered subheadings via `<span class="num">`); v2
   renders plain markdown — no callout primitive in the source
   format. Closing that gap means either (a) extending the v2
   source format with callout-equivalent fenced syntax (e.g.
   GFM-style `> [!NOTE]`) and teaching `build_md` to render it, or
   (b) accepting that v2 is intentionally simpler. Decision and
   roadmap entry pending.
4. **`upgrade` for v2.** Currently v1-only. v2 framework refresh
   ships by re-running `migrate-v1-to-v2` or by manually replacing
   the framework block; a dedicated `upgrade-md` would automate
   re-injecting the latest framework block from `starter.md` into
   an existing v2 source. Lower priority — manual replace works
   for now.
5. **Carried from earlier sessions:**
   - **[#48] follow-up PR** — drop "verbatim" from two
     `starter.json` instructions; switch
     `upgrade.py:_reorder_dict` callers to derive canonical order
     from `list(starter.keys())`.
   - **Roadmap step #6 — raise coverage.** `main.py` was 64 % at
     session 10; this session added meaningful coverage to the v2
     side but didn't measure overall. Re-run `pytest --cov` and
     plan the targeted-branches PR.
   - **Roadmap steps #7 / #8 / #9 / #10** — mutation testing,
     coverage gate, splitting `main.py`. Deferred again.

### Blockers

- None. Both PRs open and CI green at session end.

[#64]: https://github.com/nuncaeslupus/research-buddy/pull/64
[#65]: https://github.com/nuncaeslupus/research-buddy/pull/65
[#66]: https://github.com/nuncaeslupus/research-buddy/pull/66
[#67]: https://github.com/nuncaeslupus/research-buddy/pull/67

---

## Session 2026-04-26 (session 10)

### What was done

- **Executed the bot-review triage on PR [#53]** per session 9's
  provisional call. One follow-up commit `c45061a` (folded into
  squash-merge `b644725` on `main`) plus 5 inline replies on the
  PR threads. Merged + 1.4.0 published to PyPI in parallel; the
  `v1.4.0` tag was created on `b644725` at the end of the
  session.
- **`c45061a` — table macro refactor.** Pushed the remaining
  hand-rolled table assembly into the Jinja macro. `r_table` is
  now 8 lines: the two heuristics (`_nowrap_cols`,
  `_table_col_widths`) feeding one macro call. The macro takes
  `headers`, `rows`, `nowrap`, `col_widths`, `ncols`, `use_fixed`
  and does the `<colgroup>` / `<col>` loop, the `t-fixed` class
  conditional, the `<th>` loop, and the `<td>` cell loop with
  the `nw` conditional class (via `loop.index0` against
  `nowrap|length`). `md()` is invoked through the registered
  Jinja filter on cell/header values. `make regen-example` was
  byte-identical against the pre-refactor baseline (194,789
  bytes, zero diff). 127 tests still pass.
- **Bot replies on [#53]** — posted as inline replies via
  `gh api … pulls/53/comments -F in_reply_to=…`:
  - #1 (autoescape, HIGH) and #2 (manual `r_code` escape,
    MEDIUM): pushed back. Pre-migration code never escaped
    title/badge fields either, so this PR doesn't change the
    security posture. Flipping autoescape on would (a) break
    byte-identity against the 1.3.x output for any document
    with `<`, `&`, or `'` in title/badge fields and (b) require
    `| safe` at every `md()` interpolation site plus `r_svg`.
    The trust model lives in `starter.json.agent_guidelines`
    (agents instructed not to embed JS in svg blocks).
    Tightening that — moving from agent-trust to in-template-
    trust — is its own PR, not part of a no-behaviour-change
    migration.
  - #3 (colgroup), #4 (use_fixed boolean), #5 (cell loop): all
    addressed in `c45061a`; replies point at the commit.
- **Stale-branch cleanup.** After the squash-merge, GitHub
  auto-deleted `refactor/jinja-templates` on the remote. A late
  status push from this session accidentally resurrected it;
  fixed via `git push origin :refactor/jinja-templates`. No
  data lost — the merged content is on `main` as `b644725`, and
  this session's status entry rides in via a separate docs PR.
- **Lint slip from session 9 not repeated.** Ran
  `uv run ruff format --check` manually before pushing the
  table-macro commit. `pre-commit install` still not invoked
  on this clone.

### Next steps

1. **[#48] follow-up PR** (still queued from session 8): drop
   "verbatim" from the two `starter.json` instructions where it
   conflicts with the "Adapt to each project" requirement;
   switch `upgrade.py:_reorder_dict` callers to derive the
   canonical key order from `list(new_ag.keys())` and
   `list(starter.keys())` so the upgrade logic auto-tracks
   future starter changes.
2. **Roadmap step #6 — raise coverage.** `main.py` 64 % → ≥85 %,
   `validator.py` 63 % → ≥85 %. Target the untested branches:
   `--watch`, `--pdf`, `--all`, batch mode, validator error
   paths, version-compat tiers.
3. **Roadmap steps #7 / #8 / #9** — mutation-testing baseline,
   coverage threshold in CI, splitting `main.py`. Step #10 was
   folded into the Jinja migration in session 9.
4. **Optional housekeeping.** Run `uv run pre-commit install`
   on this clone so `ruff format --check` runs locally on every
   commit — was the cause of the format slip on the first push
   in session 9, documented in `CLAUDE.md` but never invoked on
   this branch.

### Blockers

- None. v1.4.0 shipped (PyPI + git tag); `main` is clean.

[#53]: https://github.com/nuncaeslupus/research-buddy/pull/53

---

## Session 2026-04-26 (session 9)

### What was done

- **Shipped Jinja2 migration of `build.py` to PR review** (PR
  [#53] open, CI green, bot review pending; bumps 1.3.4 →
  1.4.0). Folded roadmap step #10 ("split build.py via a
  renderers package") into the Jinja move — there was no value
  in shipping a renderer split that would be torn out a step
  later. New `templates/` package (`base.html.j2`,
  `blocks.html.j2`, `section.html.j2`) holds all markup;
  `build.py` is now 1–4 line wrappers + the heuristics
  (`_table_col_widths`, `_nowrap_cols`, Python language
  auto-detect, `_resolve_lang_code`).
- **Migration order — 8 commits, byte-identity gate at every
  step.** Each commit ended with `make regen-example` producing
  a `starter-example/starter.html` that `diff`-ed clean against
  a baseline captured on `main` before the branch was cut.
  127 tests + lint stayed green at every step. Order:
  scaffolding (jinja dep, _get_env) → 8 simplest renderers →
  banners + callout + verdict → containers → code+table →
  section.html.j2 → base.html.j2 → version bump.
- **Lint slip.** `make lint` runs `ruff check + mypy` only;
  CI also runs `ruff format --check`. Three wrappers needed
  reformatting (lines that fit on one line after the migration
  shrunk them). Fixed in commit `08832c2`. Could add `ruff
  format --check` to `make lint` to catch this locally next
  time, or `pre-commit install` (already documented in
  CLAUDE.md but not run on this branch).
- **Key whitespace pattern:** every block macro is wrapped in
  `{%- macro ... -%}` (strips whitespace at start of body) and
  `{% endmacro -%}` (preserves trailing newline of body, strips
  whitespace AFTER the endmacro). The combination emits exactly
  the bytes of the original f-string return value.
  `keep_trailing_newline=False` (default) on the env so
  `base.html.j2` ends at `</html>` without a trailing newline,
  matching the original f-string.
- **Gemini bot posted 5 inline comments** on PR [#53]:
  1. **HIGH (security):** `autoescape=False` permits HTML
     injection via titles/badges. Suggests: enable autoescape,
     mark trusted output (`md()`, svg) with `| safe`.
  2. **MEDIUM:** Manual `&/</>` escape in `r_code` becomes
     redundant if autoescape is on.
  3. **MEDIUM:** `<colgroup>`/`<col>` assembly still in Python
     — should move into the `table` macro.
  4. **MEDIUM:** `table_cls = ' class="t-fixed"' if use_fixed
     else ""` — pass `use_fixed` boolean instead.
  5. **MEDIUM:** `<td>` cell loop with `nw` conditional class
     still in Python — should move into the macro.

### Next steps

1. **Triage bot review on [#53] and decide.** My provisional
   call (user wanted to think on it):
   - **#1/#2 (autoescape):** push back. The original code never
     escaped title/label/badge fields either, so this PR
     doesn't change the security posture. The trust model
     lives in `starter.json.agent_guidelines` — agents are
     instructed not to embed JS in svg blocks. Flipping
     autoescape on would (a) break byte-identity for any input
     containing `<`, `&`, `'` and (b) require `| safe` on every
     `md()` interpolation site and `r_svg`. Better as a
     follow-up "tighten input trust" PR if we want to move
     from agent-trust to in-template-trust.
   - **#3/#4/#5 (table macro):** accept. The table macro is
     half-done — `<colgroup>` loop, `t-fixed` class string, and
     `<td>` cell loop with the `nw` conditional are pure markup
     and belong in the template. Refactor passes `headers`,
     `rows`, `nowrap`, `col_widths`, `ncols`, `use_fixed`
     directly; macro does the loops. Byte-identity gate
     protects against whitespace regressions.
2. **After triage, push final fixes; merge [#53].**
3. **After merge: `make publish` to PyPI.** This is a MINOR
   bump (new runtime dep `jinja2>=3.1` + transitive
   `markupsafe`). Existing downstream docs at v1.3.x will emit
   an info note on build (tool newer than doc). Optional: tag
   `v1.4.0`, push.
4. **[#48] follow-up PR** (still queued from session 8): drop
   "verbatim" from the two `starter.json` instructions where it
   conflicts with the "Adapt to each project" requirement;
   switch `upgrade.py:_reorder_dict` callers to derive the
   canonical key order from `list(new_ag.keys())` and
   `list(starter.keys())` so the upgrade logic auto-tracks
   future starter changes.
5. **Roadmap step #6 — raise coverage** (carried since session
   5). `main.py` 64 % → ≥85 %, `validator.py` 63 % → ≥85 %.
6. **Roadmap steps #7, #8, #9** — mutation-testing baseline,
   coverage threshold in CI, splitting `main.py`. Step #10 is
   now done (folded into the Jinja migration).
7. **Theme-aware conditionals are now cheap.** Adding `<style>`
   blocks gated on user prefs, print-specific output, or new
   block types only needs a macro edit, not f-string surgery.
   Worth keeping in mind for the queued "real PDF generator"
   future improvement.

### Blockers

- None. PR [#53] is awaiting human triage of the bot review.

[#53]: https://github.com/nuncaeslupus/research-buddy/pull/53

---

## Session 2026-04-25 (session 8)

### What was done

- **Shipped HTML rendering improvements split across four PRs**
  ([#49] merged; [#50], [#51], [#52] open at session end). User
  triaged the four concerns up front and authorized the
  one-PR-per-concern split:
  1. **[#49] — logo PNG resize** (1.3.0 → 1.3.1, PATCH). The
     bundled `images/research-buddy.png` was 1536×1536 / 725 KB
     but only ever displayed at ~100 px. Resized to 200×200 via
     PIL Lanczos (27 KB, -96 %). Generated HTML dropped from
     ~944 KB to ~190 KB — the user's "embedded libraries" guess
     turned out to be wrong; the logo was the real culprit.
     `highlight.min.js` is 127 KB and legitimate, kept as-is.
  2. **[#50] — tab bar mobile overflow** (1.3.1 → 1.3.2, PATCH).
     The 5-tab bar clipped on phones because nothing could
     scroll. Added `overflow-x: auto`, hid the scrollbar
     (`scrollbar-width: none` + `::-webkit-scrollbar`),
     `flex-shrink: 0` + `white-space: nowrap` on tab buttons,
     and made the burger menu `position: sticky; left: 0` so it
     stays pinned while tabs scroll under it. After bot review,
     pushed a follow-up giving the sticky button `height: 100%`
     and stripping its top/bottom/left borders so tabs aren't
     visible in gaps as they scroll past.
  3. **[#51] — sidebar overlay in landscape phones**
     (1.3.1 → 1.3.3, PATCH). Mobile sidebar overlay was gated on
     `max-width: 768px` only, so phones in landscape (height
     ~390-430 px, width 844-915 px) fell through to the desktop
     rule and the sidebar ate half the screen. Expanded the
     media query to `(max-width: 768px), (max-height: 500px)` —
     500 px catches landscape phones without affecting tablets
     (≥744 px tall) or laptops (≥600 px tall). After bot review,
     swapped the JS-side `window.innerWidth/innerHeight`
     comparison for `window.matchMedia('(max-width: 768px),
     (max-height: 500px)')` so CSS and JS share the same media
     query and can't drift.
  4. **[#52] — light theme by default with dark-mode toggle**
     (1.3.1 → 1.3.4, PATCH). User wanted light as the default
     with the option to switch. CSS `:root` now holds a light
     palette (#ffffff / #1a2030 / saturated brand colours);
     dark colours moved under `:root[data-theme="dark"]` and
     `color-scheme` follows. The bundled hljs CSS got an Atom
     One Light default with the existing One Dark scoped under
     `[data-theme="dark"]`. New `--code-bg` and `--skip-*`
     variables replace previously-hardcoded `#0d1117` /
     `#2a2020` / `#886666`. Tab bar gained a ☀/☾ toggle aligned
     to the right; click flips the attribute and persists the
     choice in `localStorage('rb-theme')`. Inline `<head>`
     script reads localStorage **before paint** to avoid FOUC.
     Hardcoded footer colours (`#8090b8`, `#6070a0`,
     `#a0b0d0`) were replaced with `var(--text3)` so both
     themes look right.
- **Version leapfrog deliberate.** Each PR bumped one PATCH so
  the four PRs could land independently without version-string
  conflicts: 1.3.1 (logo), 1.3.2 (tab bar), 1.3.3 (landscape),
  1.3.4 (theme). PRs [#51] and [#52] both needed a `git merge
  origin/main` mid-session once earlier PRs landed (style.css
  in [#51], style.css + version files in [#52]) — auto-merge
  handled the CSS, version files were trivial "ours".
- **Bot reviews triaged, not blindly applied.**
  `gemini-code-assist[bot]` posted on [#50], [#51], and [#52].
  Accepted: sticky button full-height ([#50]), `matchMedia`
  ([#51]). Skipped with reasoning: scrollbar discoverability on
  [#50] (matches mobile platform conventions); `THEME_KEY`
  constant on [#52] (the magic string actually crosses the
  build.py↔script.js boundary, so factoring inside script.js
  alone doesn't reduce duplication); FOUC-script "duplication"
  on [#52] (bot misread — `starter-example/starter.html` is
  the *output* of `build.py`, not separate source).
- **Bot review on already-merged [#48] still open.** Four
  comments on `starter.json` ("verbatim" wording vs. "Adapt to
  each project" placeholders) and `upgrade.py` (hardcoded
  ordering keys vs. deriving from `list(starter.keys())` /
  `list(new_ag.keys())`). Worth folding into the next small
  cleanup PR — none are urgent.

### Next steps

1. **After [#50], [#51], [#52] all merge**, cut a 1.3.4 PyPI
   release. `make publish`, push tag, confirm install.
2. **Jinja2 migration of `build.py`** (user agreed to plan it
   as a follow-up). Goal: replace the assembly f-string at the
   bottom of `build_html()` and the per-block renderers with
   Jinja templates / macros, keeping `make regen-example` byte-
   identical against the pre-migration baseline. New runtime
   dependency, but the `<head>` / `<body>` / per-tab scaffolding
   becomes substantially more readable, and adding theme-aware
   conditionals (or future block types) gets cheaper.
3. **[#48] follow-up PR**: drop "verbatim" from the two
   `starter.json` instructions where it conflicts with the
   "Adapt to each project" requirement; switch
   `upgrade.py:_reorder_dict` callers to derive the canonical
   key order from `list(new_ag.keys())` and
   `list(starter.keys())` so the upgrade logic auto-tracks
   future starter changes.
4. **Roadmap step #6 — raise coverage** (carried from session
   7). `main.py` 64 % → ≥85 %, `validator.py` 63 % → ≥85 %.
   Target the untested branches: `--watch`, `--pdf`, `--all`,
   batch mode, validator error paths, version-compat tiers.
5. **Roadmap steps #7 / #8 / #9 / #10** — mutation-testing
   baseline, coverage threshold in CI, splitting `main.py`,
   splitting `build.py` via a `renderers/` package (the last
   item likely interacts with the Jinja migration; sequence
   them carefully).
6. **Downstream cleanup** — same standing item: any project
   with `agent_guidelines` mid-file or in legacy key order can
   run `research-buddy upgrade <path>/*.json --apply` to pick
   up the 1.3.0 reorganization.

### Blockers

- None. [#50] / [#51] / [#52] all green and ready to merge in
  any order; conflicts pre-resolved.

[#49]: https://github.com/nuncaeslupus/research-buddy/pull/49
[#50]: https://github.com/nuncaeslupus/research-buddy/pull/50
[#51]: https://github.com/nuncaeslupus/research-buddy/pull/51
[#52]: https://github.com/nuncaeslupus/research-buddy/pull/52

---

## Session 2026-04-25 (session 7)

### What was done

- **Shipped starter reorganization + structural upgrade** (PR [#48]).
  Single PR bundled because all changes were "same file, same
  theme" — the user explicitly authorized the one-concern-per-PR
  override for this case (consistent with the same override on PR
  [#44]).
  1. **`agent_guidelines.framework` reordered** for top-down
     readability: orientation (`about`) → boundaries
     (`failure_modes`) → research methodology (`source_discovery`,
     `second_opinion_review`, `synthesis_matrix`) → document
     mechanics (`document_navigation`, `content_format`,
     `cross_links`, `widget_library`, `versioning`,
     `update_targets`) → output signals (`turn_markers`,
     `html_generation`). `standard_session` children reordered so
     `pre_update_confirmation` sits adjacent to Turn 2 (the turn
     that calls it). **Steps within `turn_1_research` and
     `turn_2_review_and_write` arrays are unchanged** — those are
     the procedure, not subject to reorder.
  2. **Single source of truth for the verbatim brief template.**
     The ~1 KB template that was inlined in
     `turn_1_research[3]` now lives only in
     `framework.second_opinion_review.brief_template` as a
     `{instruction, template}` dict. Turn 1 references it by name.
     Citation format aligned to `Title, Author, Year, Venue,
     DOI/URL` everywhere (the prior drift between Turn 1 and
     `brief_template` was the bug commit `8f1d335` half-fixed).
  3. **Three long passages tightened** without losing essence:
     `versioning.tool_version_compatibility`,
     `html_generation.agent_action`,
     `brief_template.instruction`. `failure_modes` "no go-ahead"
     wording now references `pre_update_confirmation` so it
     doesn't contradict the implicit-approval test added in
     [#44].
  4. **`research-buddy upgrade` reorders existing files at four
     levels** — doc top-level (`agent_guidelines, meta, tabs,
     changelog`), `agent_guidelines` children, `meta` keys,
     `project_specific` keys. Custom/extra keys land at the end
     of their level. Required because `dict ==` ignores key order
     — added `docs_equivalent()` helper and switched
     `cmd_upgrade`'s idempotency check to it, so reorder-only
     changes trigger a write instead of being silently skipped.
- **11 new tests** (127 pass total): 9 in `TestUpgradeReorder`
  for the new reorder behavior, 2 in `TestStarterDocIntegrity`
  asserting the citation format is consistent across both Turn 1
  and `brief_template`, and that Turn 1 references
  `brief_template` instead of inlining a placeholder marker (so
  the same drift can't happen again).
- **Smoke-tested upgrade dry-run** against two real downstream
  docs: `ai_trading_system_v4.2.json` (would reorder
  `meta` + `agent_guidelines.project_specific`) and
  `~/Descargas/alzheimer_companion_v1_10.json` (had
  `agent_guidelines` at position 4 — reorder would fix
  top-level + meta). Neither file was modified — dry-run only.
- **Version 1.2.2 → 1.3.0** (MINOR per
  `framework.versioning.rule`; content change in starter).
  `make version-sync` + `make regen-example` ran clean — the
  rebuilt `starter-example/starter.html` only changed in the
  version-footer string (agent_guidelines isn't user-visible in
  the rendered HTML).
- **Published 1.3.0 to PyPI** via `make publish`. Live at
  https://pypi.org/project/research-buddy/1.3.0/. Tag `v1.3.0`
  pushed.
- **Zero open PRs** at session end. `main` CI green.

### Next steps

1. **Roadmap step #6 — raise coverage**. `main.py` 64% → ≥85%,
   `validator.py` 63% → ≥85%. Target the untested branches:
   `--watch`, `--pdf`, `--all`, batch mode, validator error paths,
   version-compat tiers.
2. **Roadmap step #7 — mutation-testing baseline**. Install
   `mutmut`, configure against `src/research_buddy/`, capture
   baseline survivor count via the `mutmut-report` skill.
3. **Roadmap step #8 — coverage threshold in CI**. Add
   `--cov-fail-under=85` to pytest and wire `pytest-cov` into the
   CI test job. Optional: codecov upload + README badge.
4. After the coverage trio, steps #9 (split `main.py`) and #10
   (split `build.py` via a `renderers/` package).
5. **Downstream cleanup**: any project that has
   `agent_guidelines` mid-file or in legacy key order can now run
   `research-buddy upgrade <path>/*.json --apply` to pick up the
   1.3.0 reorganization. The 1.2.2 → 1.3.0 bump is MINOR, so
   existing docs WILL emit an info note on build (tool newer than
   doc) until they re-run upgrade.
6. Ongoing: keep an eye on new Dependabot PRs (majors
   individually, python-minor-patch group as one, CI must stay
   green on each).

### Blockers

- None.

[#48]: https://github.com/nuncaeslupus/research-buddy/pull/48

---

## Session 2026-04-19 (session 6)

### What was done

- **Shipped protocol refinements to `starter.json`** (PR [#44]),
  motivated by a real user incident: Claude-on-the-web stopped
  Turn 2 for a redundant third confirmation, then the user's
  quota ran out before the build step could run, so no HTML was
  produced. Three interlocking fixes in one PR (user explicitly
  overrode the one-concern-per-PR rule — same file, same theme):
  1. `standard_session.pre_update_confirmation` gained an
     **approval test**: submission of second-opinion sources + a
     continue signal in the same message, with clean vetting and
     no blocking contradictions, counts as implicit approval and
     Turn 2 proceeds directly to the atomic write. Invariant
     amended to tie the version bump to the approval test OR
     explicit approval.
  2. `framework.html_generation.agent_action` now distinguishes
     shell-access (run the command) from no-shell (web chat UI:
     print the build command verbatim on its own line, ready to
     copy — "you can now run X" is not enough).
  3. New `framework.turn_markers` section: every defined turn
     ends with a human-readable banner + machine-readable
     HTML-comment tag on the final two lines. Four states —
     `turn_1_end`, `turn_2_awaiting_confirmation`,
     `turn_2_complete`, `session_zero_end`. A stable
     `detection_regex` is exposed so external automation can
     detect turn boundaries. Placeholder syntax is `{name}` (not
     `<name>`) so the tag template is a valid HTML comment AND
     matches the regex.
- Version bumped **1.2.0 → 1.2.1**; `make version-sync` +
  `make regen-example` applied. Four new/tightened assertions in
  `TestStarterDocIntegrity` (approval-test wording, invariant
  rewording, `turn_markers` shape + regex round-trip, no-shell
  branch in `html_generation.agent_action`); **116 tests pass**.
- **Gemini review on #44 — both points accepted** (commit b381811):
  use the full `framework.turn_markers.states` path to match the
  turn_1 and session_zero bullets; qualify the
  `{version}`/`{file_name}` substitution with "where applicable"
  since `turn_2_awaiting_confirmation` has no placeholders.
- **Published 1.2.1 to PyPI** via `make publish`. Live at
  https://pypi.org/project/research-buddy/1.2.1/ .
- **Zero open PRs** at session end. `main` CI green.

### Next steps

1. **Roadmap step #6 — raise coverage**. `main.py` 64% → ≥85%,
   `validator.py` 63% → ≥85%. Target the untested branches:
   `--watch`, `--pdf`, `--all`, batch mode, validator error paths,
   version-compat tiers.
2. **Roadmap step #7 — mutation-testing baseline**. Install
   `mutmut`, configure against `src/research_buddy/`, capture
   baseline survivor count. Use the `mutmut-report` skill at
   `.claude/skills/mutmut-report/` to triage survivors.
3. **Roadmap step #8 — coverage threshold in CI**. Add
   `--cov-fail-under=85` to pytest and wire `pytest-cov` into the
   CI test job. Optional: codecov upload + README badge.
4. After the coverage trio, steps #9 (split `main.py`) and #10
   (split `build.py` via a `renderers/` package).
5. Downstream projects need to run `research-buddy upgrade
   <path>/*.json --apply` to pick up `turn_markers` and the
   rewritten gate in their existing JSONs. The 1.2.0 → 1.2.1
   bump is patch-level, so existing docs will NOT emit a
   compat warning on build — the agent picks up the new
   guidelines only after the user runs `upgrade`.
6. Ongoing: keep an eye on new Dependabot PRs (majors
   individually, python-minor-patch group as one, CI must stay
   green on each).

### Blockers

- None.

[#44]: https://github.com/nuncaeslupus/research-buddy/pull/44

---

## Session 2026-04-19 (session 5)

### What was done

- **Shipped roadmap step #5 — schema self-test** (PR [#40]). Added
  `TestSchemaIntegrity::test_schema_is_valid_draft_2020_12` to
  `tests/test_schema.py` — loads the bundled `schema.json` and runs
  `jsonschema.Draft202012Validator.check_schema()`. Catches typos /
  invalid keywords in the schema itself. Gemini review on the PR
  suggested reusing `validator._load_schema()` instead of duplicating
  the 3-line file-load snippet — accepted (commit b5a53a9), dropped
  unused `json` and `importlib.resources` imports.
- **Shipped the second half of [#22] — three methodology sections
  into `starter.json`** (PR [#41]; closes #22). Added
  `framework.source_discovery` (multi-database principle, author
  verification, preprint caution, paywalled-access recipes),
  `framework.synthesis_matrix` (Claim × Source evidence table +
  pre-registration rule), and `standard_session.pre_update_confirmation`
  (explicit 4-step gate before atomic writes; `turn_2_review_and_write`
  now references it by name). Version bumped **1.1.1 → 1.2.0**;
  `make version-sync` + `make regen-example` applied. Three new tests
  in `TestStarterDocIntegrity`; 113 pass total. Gemini suggested
  tightening the synthesis_matrix adoption rule to reject Tier-2
  contradictions too; **partial accept** (commit b1b8ff6) — clarified
  the SUPPORTS tier (≥2 from Tier-1, explicit) but kept the
  CONTRADICTS Tier-1-only asymmetry intentional, since the original
  text is battle-tested downstream and prevents a single Tier-2
  textbook from vetoing strong Tier-1 evidence.
- **Zero open PRs** at session end. `main` CI green after every merge.

### Next steps

1. **Roadmap step #6 — raise coverage**. `main.py` 64% → ≥85%,
   `validator.py` 63% → ≥85%. Target the untested branches:
   `--watch`, `--pdf`, `--all`, batch mode, validator error paths,
   version-compat tiers. This is a coverage-adding PR; actual gains
   in meaningful-mutation survival will be measured by step #7
   (`mutmut`).
2. **Roadmap step #7 — mutation-testing baseline**. Install `mutmut`,
   configure against `src/research_buddy/`, capture baseline survivor
   count. Use the `mutmut-report` skill at `.claude/skills/mutmut-report/`
   to triage survivors into real-gap / equivalent / untestable.
3. **Roadmap step #8 — coverage threshold in CI**. Add
   `--cov-fail-under=85` to pytest and wire `pytest-cov` into the CI
   test job. Optional: codecov upload + README badge.
4. After the coverage trio, steps #9 (split `main.py`) and #10
   (split `build.py` via a `renderers/` package).
5. Ongoing: keep an eye on new Dependabot PRs (majors individually,
   python-minor-patch group as one, CI must stay green on each).

### Blockers

- None.

[#40]: https://github.com/nuncaeslupus/research-buddy/pull/40
[#41]: https://github.com/nuncaeslupus/research-buddy/pull/41

---

## Session 2026-04-19 (session 4)

### What was done

- **Shipped roadmap step #4 — Python 3.13 in CI** (PR [#36]). Added
  `"3.13"` to the `test` job matrix and mirrored the support with a
  `Programming Language :: Python :: 3.13` classifier in
  `pyproject.toml`. Lint job stays on 3.12.
- **Shipped `status/` read-first convention** (PR [#37]): new section
  at the top of project `CLAUDE.md` telling every future session to
  read `plan.md` + `next-session.md` before doing anything else, plus
  the promised mark-as-done on steps #2 and #3 in the roadmap.
- **Shipped `research-buddy upgrade` CLI** (PR [#38], closes half of
  [#22]). Pure logic lives in new `src/research_buddy/upgrade.py`; CLI
  handler in `main.py`; 21 tests in `tests/test_upgrade.py`. Dry-run
  default (exit 1 on changes), `--apply` writes atomically and runs
  `validate()`; **idempotent no-op** skips the write and the
  `meta.format_note` stamp when the doc is structurally unchanged.
  Preserves `agent_guidelines.project_specific` and
  `session_zero.note`. Smoke-tested end-to-end on a scaffolded +
  drifted project.
- **Triaged review feedback on three docs/feature PRs**:
  - [#38] — accepted all 3 Gemini comments: comma-joined `key_diffs` in
    CLI output, newline-separated `format_note` entries, and an
    `isinstance` guard in `_compute_key_diffs` so a malformed
    non-dict framework doesn't crash the diff.
  - [#37] — accepted: moved the step #3 shipped-note to its own
    indented line, matching the style of steps #1 and #2.
  - [#35] — accepted link refs for [#29]–[#31]; pushed back on two with
    evidence. The "plan.md still stale" concern was moot because [#37]
    ships it in parallel. The "ruff format supports TOML since 0.4.0"
    claim is the same one Gemini raised on [#24] and was rejected with
    evidence then; verified again against the pinned `ruff 0.15.9` —
    `format --extension` still only maps `python`, `ipynb`, `pyi`.
- **Drained the Dependabot queue**: merged all 7 open bumps in one
  pass — [#27] `actions/checkout` 4→6, [#28] `actions/download-artifact`
  4→8, [#29] `astral-sh/setup-uv` 5→7, [#30] `actions/setup-python`
  5→6, [#31] `actions/upload-artifact` 4→7, [#32] python-minor-patch
  group, [#33] `types-jsonschema` patch. Dependabot auto-rebased [#28]
  and [#29] when the first wave hit conflicts; the retry succeeded.
- **Zero open PRs** at session end. `main` CI green after every merge.

### Next steps

1. **Second half of [#22]** — three methodology sections into
   `starter.json`: `synthesis_matrix`, the generic subset of
   `source_discovery` (multi-database principle, author verification,
   preprint caution, paywalled access), and an explicit
   pre-update confirmation gate in `standard_session.preflight_sequence`.
   Reference text lives in `ai-trading-system/tmp/research-buddy-upstream-issue-draft.md`.
   This is a template-content change — bumps `meta.research_buddy_version`,
   so it needs a `make version-sync` + `make regen-example` pass, and
   the `research-buddy upgrade` CLI shipped in #38 is what downstream
   projects will use to adopt it.
2. **Roadmap step #5 — schema self-test**. One pytest in
   `tests/test_schema.py` that loads `schema.json` and validates it
   against the Draft 2020-12 meta-schema. Catches typos in the schema
   itself.
3. Ongoing: keep an eye on new Dependabot PRs (majors individually,
   python-minor-patch group as one, CI must stay green on each).

### Blockers

- None.

[#27]: https://github.com/nuncaeslupus/research-buddy/pull/27
[#33]: https://github.com/nuncaeslupus/research-buddy/pull/33
[#35]: https://github.com/nuncaeslupus/research-buddy/pull/35
[#36]: https://github.com/nuncaeslupus/research-buddy/pull/36
[#37]: https://github.com/nuncaeslupus/research-buddy/pull/37
[#38]: https://github.com/nuncaeslupus/research-buddy/pull/38

---

## Session 2026-04-19 (session 3)

### What was done

- **Shipped roadmap step #2 — pre-commit hooks.** PR [#24] merged.
  `.pre-commit-config.yaml` with four local (`uv run`) hooks mirroring
  the CI lint job: `ruff check`, `ruff format --check`, `mypy`,
  `check-version-sync`. Added `pre-commit>=3.5.0` to the `dev` extra and
  documented `pre-commit install` in `CLAUDE.md`. Rejected a Gemini
  review (toml in ruff-format's `types_or`) with verification evidence —
  `ruff format` is Python-only.
- **Shipped a small skills-cleanup PR** on the same day. PR [#25]
  merged. Tightened `analyze_mutmut.py` (`run_cmd` exits on non-zero
  return instead of silently emptying survivors; `find_mutmut` uses
  `shutil.which` and exits with a clear error if not found). Applied all
  three Gemini review comments after verifying they were correct. Also
  reverted an incorrect SKILL.md rewording I made — `git rev-parse
  --show-toplevel` resolves to the caller's repo, so the cd-elsewhere
  recipe I wrote did not work.
- **Shipped roadmap step #3 — Dependabot.** PR [#26] merged.
  `.github/dependabot.yml` with two weekly ecosystems: `uv` (Dependabot's
  native uv ecosystem, GA 2026-03-10) and `github-actions`. Minor + patch
  bumps grouped per ecosystem; majors get individual PRs. Config fired
  immediately — five bump PRs opened on merge ([#28]–[#32]). Rejected a
  second Gemini review (add `pre-commit` ecosystem) because our config
  is all `repo: local`, which Dependabot explicitly skips.

### Next steps

1. **Triage the Dependabot PR queue** that opened on #26 merge:
   [#28]–[#32]. Quick pass: approve the github-actions majors
   individually, let the python-minor-patch group ride as one PR. CI on
   each must stay green.
2. **Roadmap step #4 — Python 3.13 in CI.** Branch
   `ci/python-3.13`. Add `"3.13"` to the `test` job matrix in
   `.github/workflows/ci.yml`; lint job stays on 3.12. Small config-only
   PR.
3. After #4, continue with step #5 (schema self-test) then step #6
   (coverage raise) per `status/plan.md`.
4. **In-flight user work**: branch `chore/skills-subtree` has a commit
   removing `.claude/skills/` in preparation for a git-subtree import.
   That's independent of the roadmap — resume at the user's direction.
5. Upstream-proposals implementation ([#22]) still queued as a separate
   work stream; no change from session 2.

### Blockers

- None.

[#24]: https://github.com/nuncaeslupus/research-buddy/pull/24
[#25]: https://github.com/nuncaeslupus/research-buddy/pull/25
[#26]: https://github.com/nuncaeslupus/research-buddy/pull/26
[#28]: https://github.com/nuncaeslupus/research-buddy/pull/28
[#29]: https://github.com/nuncaeslupus/research-buddy/pull/29
[#30]: https://github.com/nuncaeslupus/research-buddy/pull/30
[#31]: https://github.com/nuncaeslupus/research-buddy/pull/31
[#32]: https://github.com/nuncaeslupus/research-buddy/pull/32

---

## Session 2026-04-19 (session 2)

### What was done

- **Resolved the queued upstream-proposals item.** Read the three
  reference files in `ai-trading-system` (draft issue body,
  `scripts/upgrade_research_buddy.py` reference impl,
  `docs/dev/research-buddy-upgrade.md` runbook) to size the work.
- **Posted tracking issue [#22]** on research-buddy: combined proposal
  for a `research-buddy upgrade` CLI and three methodology sections in
  `starter.json` (`synthesis_matrix`, generic `source_discovery` subset,
  pre-update confirmation gate in `standard_session`).
- Stripped private-repo links from the issue body before posting —
  `ai-trading-system` is PRIVATE and the two reference files are
  **untracked** there (sit in the working tree, never committed).
- **Updated memory**: `project_upstream_proposals.md` frontmatter +
  trailing note now reflect "tracked as #22" instead of "not yet
  posted". MEMORY.md index hook updated to match.

### Next steps

The Session 1 list is mostly stale — refreshed:

1. Kick off **roadmap step #2 — pre-commit hooks**. Branch:
   `chore/pre-commit-hooks`. Contents: `.pre-commit-config.yaml`
   running `ruff check`, `ruff format`, `mypy`, and
   `make check-version-sync` on every commit. Document
   `pre-commit install` in the project `CLAUDE.md`.
2. After #2, move to step #3 (Dependabot) — small config-only PR.
3. Upstream-proposals implementation (tracked as [#22]) is now a
   separate work stream. Per `feedback_pr_separation.md` split into
   two PRs; per `feedback_refactor_ordering.md` ship the `upgrade` CLI
   (guardrail) **before** the `starter.json` methodology additions
   (feature). Slot after the current professional-polish roadmap or in
   parallel — user's call.

### Blockers

- None.

---

## Session 2026-04-19 (session 1)

### What was done

- **Established the improvement roadmap** at `status/plan.md` (ten
  steps, three queued future improvements: jinja2 templates,
  mobile-friendly tab bar, real PDF generator).
- **Seeded `~/.claude/CLAUDE.md`** with Karpathy-style behavioural
  guidelines plus a Python-projects default-tooling section (ruff
  `E,W,F,I,UP,RUF,B,SIM,PTH`; strict-by-default mypy;
  `requires-python >= 3.11`).
- **Shipped roadmap step #1** — stricter ruff ruleset. Added `B`,
  `SIM`, `PTH` to `[tool.ruff.lint].select`, fixed the 21 violations
  surfaced (20 PTH123 across `main.py`/`conftest.py`/`test_main.py`,
  1 SIM108 in `perform_build`). PR [#19] merged; 88 tests green.
- **Inserted mutation-testing step** as new #7 between #6
  (coverage raise) and #8 (coverage threshold in CI). Raised on PR
  [#20], merged.

[#19]: https://github.com/nuncaeslupus/research-buddy/pull/19
[#20]: https://github.com/nuncaeslupus/research-buddy/pull/20
[#22]: https://github.com/nuncaeslupus/research-buddy/issues/22
