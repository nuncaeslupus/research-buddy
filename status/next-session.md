# Next session

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
