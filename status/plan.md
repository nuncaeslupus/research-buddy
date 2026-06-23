# Improvement roadmap

Professional-polish initiative agreed 2026-04-19. Executed one step at a
time; each step ships as its own PR against `main`.

Ordering rationale: cheap guard rails first, then raised coverage, then the
two big refactors last — so the expanded test suite and the stricter lint
both protect the refactors.

## Queue

- [x] **1. Stricter ruff ruleset.** Add `B` (bugbear), `SIM` (simplify),
      `PTH` (force pathlib) to `[tool.ruff.lint].select` in
      `pyproject.toml`. Fix whatever the expanded lint surfaces.
      *Shipped: 21 violations fixed (20 PTH123, 1 SIM108). All tests
      green.*
- [x] **2. Pre-commit hooks.** `.pre-commit-config.yaml` running
      `ruff check`, `ruff format`, `mypy`, and `make check-version-sync`
      on every commit. Document `pre-commit install` in `CLAUDE.md`.
      *Shipped in PR [#24].*
- [x] **3. Dependabot.** `.github/dependabot.yml` covering `pip`
      (weekly) and `github-actions` (weekly). Groups minor+patch so
      we don't drown in noise.
      *Shipped in PR [#26].*
- [x] **4. Python 3.13 in CI.** Add `3.13` to the `test` job's matrix
      in `.github/workflows/ci.yml`. Lint job stays on 3.12.
      *Shipped in PR [#36].*
- [x] **5. Schema self-test.** One pytest in `tests/test_schema.py`
      that loads `schema.json` and validates it against the Draft
      2020-12 meta-schema. Catches typos in the schema itself.
      *Shipped in PR [#40].*
- [x] **6. Raise coverage.** `main.py` (61% → 88%) and `validator.py`
      (63% → 100%). Targeted the untested branches: `--watch`,
      `--pdf`, `--all`, batch mode, validator error paths,
      version-compat tiers, MD pipeline (validate / migrate / clean
      / upgrade), and the argparse `main()` entry point.
      *Shipped: validator.py dead-code (`build_changelog_nav`,
      `_collect_all_ids` + helpers — never referenced anywhere)
      removed; new `tests/test_main_coverage.py` with 41 tests
      covering the previously-untested branches. Total project
      coverage 82% → 89%.*
- [x] **7. Mutation-testing baseline.** Install `mutmut`, configure
      it against `src/research_buddy/`, and capture a baseline
      survivor count.
      *Shipped: `mutmut>=3.0.0` in `[project.optional-dependencies].dev`,
      `[tool.mutmut]` config in `pyproject.toml`, `mutants/`
      gitignored, `tests/test_version_sync.py` skips when README is
      absent (mutmut runs tests from a `mutants/` sandbox that
      omits README). Baseline: 8964 total mutants — 4643 killed
      (51.8%), 3792 survived (42.3%), 511 no-tests, 18 timeout.
      Per-module survivor distribution captured in next-session.md.*
- [~] **7a–7j. Mutation-survivor cleanup, one module per step.**
      **Discontinued 2026-06-01.** The baseline (#7) earned its keep
      as a diagnostic — it proved line coverage ≠ behaviour coverage
      — and `validator` (#7a) + `table_layout` (#7b) shipped as
      PRs #89/#90. But the remaining ~3,700 survivors across eight
      modules (tail: `build` 630, `main` 849, `migrate_v1_to_v2`
      1198) is a low-ROI treadmill: the tests it yields pin exact
      warning strings and off-by-one boundaries, which are brittle
      and rarely catch real future bugs. Decision: stop grinding to
      zero. If a specific module gets a real bug later, fix the gap
      then. mutmut config stays in `pyproject.toml` for ad-hoc use.
      - [x] **7a.** `validator` — shipped (PR #89). 19 tests, 40
            REAL_GAP killed, 6 accepted equivalents.
      - [x] **7b.** `table_layout` — shipped (PR #90). 20 tests, 39
            REAL_GAP killed, 10 accepted equivalents.
      - [~] **7c–7j.** Discontinued (see note above).
- [x] **8. Coverage threshold in CI.** `make test-cov` runs pytest
      with `--cov --cov-report=term-missing --cov-fail-under=85`;
      CI's test job now calls it instead of bare `pytest`. Coverage
      source configured in `[tool.coverage.run]`. Current total 89%,
      so the 85% floor has headroom. *Shipped this session.*
      Optional follow-up: codecov upload + badge in README.
- [x] **8a. `starter-example/` sync guard.** New
      `scripts/check_examples_sync.py` + `make check-examples-sync`,
      wired into the CI lint job. Regenerates both examples to a temp
      dir and byte-compares against the committed copies — catches
      both content drift and version-footer drift (the examples had
      in fact gone stale at 1.8.0; regenerated to 1.10.0 in this
      change). *Shipped this session.*
- [x] **9. Split `main.py` (1007 → 66 lines).** Extracted `cli.py`
      (argparse parser + dispatch) and a `commands/` package
      (`_shared`, `build`, `validate`, `clean`, `migrate`, `init`,
      `upgrade`). `main.py` is now a thin re-export façade keeping
      `from research_buddy.main import …` and the console-script
      entry point stable. Behaviour-preserving (bodies copied
      verbatim); only the 3 `cmd_upgrade` monkeypatch targets in
      `test_upgrade.py` moved to `research_buddy.commands.upgrade.*`.
      Largest resulting module is `commands/build.py` (336 lines).
      Now #11–#14 add their handlers as new `commands/*` modules
      instead of growing `main.py`. *Shipped this session.*
- [x] **10. Split `build.py` (796 lines).** Folded into the Jinja2
      migration listed in "Future improvements" — the renderer
      split would have been torn out a step later. Each `r_*`
      block renderer is now a 1–4 line wrapper around a Jinja
      macro in `src/research_buddy/templates/`; the f-string
      scaffold at the bottom of `build_html()` is now
      `base.html.j2`.
      *Shipped via the Jinja migration.*

## Agent-efficiency helpers (queued after #6)

Surfaced 2026-05-16 from a real research-buddy session transcript
(`claude-md-best-practices_v1.11 → v1.12`). The session-time
breakdown showed the bulk of agent effort is genuinely non-mechanical
(rule drafting, hypothesis-table writing, vetting), but a meaningful
slice is pure plumbing: locating `<!-- @end: X -->` insertion points,
moving queue→tracker, bumping frontmatter + date + changelog
boilerplate, hand-writing the `@summary` block. These four steps
target that slice. Ordering rationale: `bump` is the biggest single
win (4–6 fewer str_replaces per session); the starter convention fix
is a one-line change but unblocks every future agent grep; `locate`
is a smaller-scope companion to `bump`; `diff-summary` is the
lowest-leverage convenience and can land last.

- [x] **11. `research-buddy bump <source.md> <queue-id>`.** Single
      command that performs all the mechanical Turn-2 edits: bump
      `version` + `date` in YAML frontmatter; move the Q-NNN queue
      row → Research Tracker (preserving the ID, appending version
      attribution); insert empty session-notes skeleton with
      hypothesis-resolution table + cross-section-impact line +
      compliance-validation line; add empty top changelog entry with
      version + date + queue-ID hook; add empty `### v1.X —
      YYYY-MM-DD` subsection at top of References. Agent fills the
      prose; everything mechanical is already correct. Dry-run by
      default; `--apply` writes atomically and runs `validate-md`.
      New module `src/research_buddy/bump.py` + handler
      `commands/bump.py` (the plan predated the #9 split, which moved
      handlers out of `main.py`). Tests in `tests/test_bump.py`.
      Shipped: writes a NEW `_v{next}-source.md` and validates it with
      the input as `--prior`.
- [x] **12. Starter marker hygiene.** `starter.md` had prose like
      *"paste this immediately before its `<!-- @end: rules -->`
      marker"* that embedded the literal marker, so an agent `grep`
      for an insertion point hit "found multiple times". Shipped:
      reworded the 7 colliding prose lines to "this section's closing
      `@end` marker" so each live `@end: X` is the unique occurrence of
      its ID; `tests/test_starter_hygiene.py` enforces the invariant.
      Note vs. plan: the fix is *rewording*, not fencing — inline
      mentions can't be fenced without mangling the sentence, and
      fencing wouldn't help a plain grep anyway. No `upgrade_md` code
      change needed: the 4 framework-block lines propagate to existing
      projects via the existing wholesale framework re-sync; the 3
      user-section intros reach new projects only (acceptable — `locate`
      mitigates regardless).
- [x] **13. `research-buddy locate <source.md> <anchor>`.** Shipped:
      prints the line of the *live* `<!-- @end: <anchor> -->` marker +
      context, matching full-line markers outside fenced blocks
      (reusing `validator_md._line_in_fence`), so inline prose mentions
      and fenced examples never collide. `commands/locate.py` only — no
      new top-level module. Accepts `rules`, `@end: rules`, or the full
      comment form.
- [x] **14. `research-buddy diff-summary <old.md> <new.md>`.** Shipped:
      emits the mechanical part of the `@summary` block (version bump,
      queue→tracker moves, rules added/revised, DAs/sessions added,
      append-only PASS/FAIL); narrative left as a `{{placeholder}}`.
      Exit 1 signals an append-only violation. New
      `src/research_buddy/diff_summary.py` + `commands/diff_summary.py`.
      Reuses `_check_append_only` / `_extract_section` /
      `_extract_table_first_column` (used `_entry_blocks` for rule-revision
      detection rather than `_collect_entry_ids`, which only returns IDs).

## Brief-gate hardening + localization (from a real session, 2026-06-08)

- [x] **15. Brief-gate hardening + `turn1` + Spanish localization (1.13.0).**
      Driven by a real research session where the agent skipped the second-
      opinion brief. Root cause (verified): the agent had been given a *clean
      view*, whose surviving operating-manual preamble still said "read
      [Framework (Core)] … emit the brief" while `clean` had stripped that
      framework — dangling references that turn "fill a template" into "generate
      from scratch", which agents under tool-pressure skip. Shipped together:
      - **`clean` strips the agent preamble** (`clean_md.strip_agent_preamble`)
        and replaces it with a one-line self-identifying note pointing back at
        the `*-source.md`. The clean view is a reader artifact, not an agent
        file. (HTML never carried it — it sits before the first H2, which the
        tab split drops.)
      - **Hardened starter preamble:** brief gate stated first AND last
        (primacy + recency), concrete tool families named ("web search,
        extended/advanced/deep research, browsing, code execution that fetches
        sources"), and an inline fill-in brief skeleton so it survives a short
        read window. Propagates to existing docs via `upgrade --apply`
        (`_replace_preamble`).
      - **`research-buddy turn1 <file>`** prints the Turn-1 brief skeleton
        pre-filled from frontmatter + the top queue row, judgement slots left as
        `{{placeholders}}` (`turn1.py` + `commands/turn1.py`). "Fill, don't
        remember."
      - **HTML section-heading localization** (`localize.py`): headings display
        in `language.code` (ships `es`) while slugs/ids stay English so
        cross-links never break; `section_labels` frontmatter overrides/extends.
        Clean MD keeps English headings (link integrity).
      Tests: `test_turn1.py`, `test_localize.py`, + clean/build/upgrade
      additions (543 passed, 91% cov). Finding recorded: `ui_strings` is dead v1
      carryover with no v2 render path — not wired; the agent writes status text
      directly.

## Opus review fix initiative (2026-06-22)

Comprehensive codebase audit by Claude Opus. Full findings in
`tmp/review-fix-list.md`. 13 PR batches, ordered by impact. Each batch
ships as its own PR against `main`.

- [ ] **PR-1: Release safety + changelog.** P0-2 (release.yml: move tag after
      publish), P3-1 (backfill CHANGELOG.md gaps since v1.2.0), P3-5 (release.yml:
      extract current-version section for release notes).
- [x] **PR-2: Append-only enforcement.** Shipped this session. P0-1(b):
      `_check_append_only` now preserves Research Tracker rows (`Q-`/`T-` ids,
      `T-000` seed exempt) and individual reference bullets (the H3 check only
      caught whole subsections). *Session-id preservation was already enforced* —
      `_collect_anchors` collects `@session`, so a removed session fires
      `anchor-removed`; a dedicated check would just double-report, so it was
      intentionally not added. P2-1 (`_check_unclosed_fence` — error at the
      opener when a fence is never closed). P2-2 (broken-cross-link promoted
      warning→error; starter illustrative targets stay `info`). P2-3
      (`_collect_entry_ids` made fence-aware; `_collect_anchors` already was).
      7 new tests; 577 passed, 91.64%. Starter still validates error-clean.
- [x] **PR-3: Framework ↔ tooling truth-up.** P0-1(a) (starter.md: teach `bump`,
      `locate`, `diff-summary` as the blessed Turn-2 path), P1-1 (same — surface
      the three helpers), P1-4 (fix version-compat pause contradiction), P1-6
      (fix "validate mechanically flags plain-text refs" claim), P3-8 (add
      `research_buddy_version` to required-fields list in starter.md).
      *Shipped: 1.14.0. Preamble "Tools at hand" now lists bump/locate/diff-summary
      with one-line descriptions. Turn-2 steps 4+6 surface the shell-access shortcuts.
      "Both flows are exactly 2 turns" rewritten to name the MINOR version-compat
      exchange as a pre-session gate. Required-fields list updated to match the
      validator (adds research_buddy_version). Plain-text-refs bullet removed from
      mechanical checks (validate doesn't check this); failure-mode tag corrected
      mechanical→semantic.*
- [x] **PR-4: Brief-skeleton unification.** P1-2 (single canonical template;
      unify preamble skeleton + turn1.py wording; sync test).
      *Shipped: 1.15.0. Preamble's 4 short placeholder names aligned to canonical
      template names (PROJECT_AND_BASIC_CHARACTERISTICS, LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED,
      RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED, TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN).
      Added missing article "a". Sync guard: TestBriefSkeletonSyncWithCanonicalTemplate (2 tests)
      catches future name drift. 596 passed, lint clean, examples in sync. PR #120.*
- [x] **PR-5: Methodology completeness.** P1-3 (Turn-2 hypothesis resolution
      step + session-note template matches bump.py), P1-5 (excellence bar
      guidance, queue prioritization rubric, rule supersession mechanics,
      queue/tracker dual-membership rule).
      *Shipped: 1.16.0. New Turn 2 step 3 (hypothesis resolution); session-note
      template in §Templates synced to `_session_skeleton` output; 2 sync-guard
      tests. Excellence bar guidance, 4-point priority rubric, supersession
      mechanics, dual-membership rule added. 598 passed, PR #121.*
- [x] **PR-6: clean_md correctness.** P2-8 (make `collect_framework_targets`
      fence-aware), P2-9 (fix `strip_framework_block` EOF content loss).
      *Shipped this session. Both verified as REAL bugs first: (P2-8) the
      starter's `### Templates` fenced examples carry `<a id="q-001">` + heading
      placeholders that were being collected as framework targets, so a promoted
      `[Q-001](#q-001)` body link got unwrapped to plain text in the clean view —
      fixed by skipping fenced lines via `validator_md._line_in_fence`. (P2-9)
      the malformed-opener `break` dropped everything from the opener to EOF
      (contradicting its own "leave untouched" comment) — now preserves the
      opener + remaining lines verbatim. The existing
      `test_malformed_no_closer_leaves_text_intact` had encoded the buggy
      drop-the-body behavior; corrected to assert the body survives. 561 passed,
      91.42%.*
- [x] **PR-7: migrate hardening (bulk).** Shipped this session: P0-4 all three
      collision bugs — changelog sort is now patch-aware (`build_changelog._key`
      returns a 3-tuple; the version-normalization collision surfaced there, not
      in a literal `_normalize_version`); queue-ID synthesis is collision-free
      (two-pass: collect existing + tracker IDs, then assign the lowest free
      `Q-NNN` — the old `Q-{i+1}` row-index scheme could dup a tracker ID or an
      inline ID); verdict `<a id>` is slugified via new `_slug` (was `rid.lower()`,
      which left spaces/punctuation in the id for labels without a clean R-/DA-
      prefix). P2-11 (`build_domain_tab` mangles a label that slugs to a
      canonical anchor → `-tab` suffix; `CANONICAL_ANCHORS` set). P2-12 / P2-13a
      (changelog renders `### vX.Y — DATE`; synthetic entry carries `meta.date`).
      P2-13b (`build_frontmatter` writes `project.source_tiers` {tier_1/tier_2/
      discovery} + `project.domain_rules`, matching the starter shape). 8 new
      tests; 569 passed, 91.53%.
  - [ ] **PR-7b: migrate dedup + drop marker (deferred).** P2-10 (deduplicate
        verdict labels) needs a `seen_ids` set threaded through the whole
        `render_block`/`render_blocks`/`render_subsections` pipeline — too
        invasive to bundle with the collision fixes. P2-13c (HTML marker when
        content is intentionally dropped, e.g. `Research Methodology`) is a
        design choice (what to mark, where) needing a clearer spec. Both split
        out to keep PR-7 reviewable and low-risk.
- [x] **PR-8: build safety + render bugs.** Shipped this session. P0-3
      (`perform_build_md` aborts with exit 1 and writes no HTML when the
      validator finds error-severity issues; warnings don't block). P2-14
      (tab labels `html.escape`d into `data-tab-label`). P2-15
      (`_md_render_inline` flattens multi-paragraph input to `<br><br>` — fixed a
      latent bug where the single-paragraph `fullmatch` *also* matched
      multi-paragraph output and returned interior `</p><p>`). P2-17
      (`_neutralize_style_close` backslash-escapes `</style>` in theme CSS, v1 +
      v2). P3-V2-TRUST (`_check_dangerous_html` warns on `<script>`/`on*=`/
      `javascript:` in the body, fence- and inline-code-aware). **P2-16 was
      already done in PR-10** (the non-UTF-8 MD-source guard via
      `read_text_or_error`). 8 new tests; 586 passed, 91.68%. Partially closes
      the "v2 escaping / trust model" backlog item (warns + neutralizes the
      `</style>` break-out; full `r_svg`/raw-HTML sanitization still open).
- [x] **PR-9: Script/test hygiene.** P3-9 (delete broken `test-all` + unused
      markers), P3-10 (fix hard-coded `1.13.0` in test_turn1.py → `1.0.0`),
      P3-11 (add `starter.md` to pre-commit version-sync files trigger),
      P2-18 (sync_version.py: count-check all four updaters, align README regex),
      P2-7 (delete dead `STARTER_NULLABLE`), P3-12 (soften "TDD ceremony enforced"
      in CLAUDE.md).
      *Shipped this session.*
- [x] **PR-10: File-I/O helpers.** P2-19 (shared `read_text_or_error` + `atomic_write`
      helpers), P2-16 (fold non-UTF-8 MD guard in), P2-20 (fold temp-file cleanup in).
      *Shipped this session: new `src/research_buddy/fileio.py` with
      `read_text_or_error` (UTF-8 guard → `FileReadError`) + `atomic_write`
      (temp-sibling rename, `try/finally` cleanup). Encoding guard wired into the
      build path user-file reads (v2 MD source + v1/v2 theme loads); `atomic_write`
      adopted by `bump`, `upgrade` (md + json), `migrate` (+ module main), `init`
      (md + json). `tests/test_fileio.py` (10) + 2 build-path integration tests;
      558 passed, 91.40%. Bundled-starter `Traversable` loads left unguarded
      (our own ASCII, not user input).*
- [x] **PR-11: upgrade edge cases.** P2-21 (v1 upgrade: add forward-only version
      guard matching v2), P2-22 (skip only version bump when doc is ahead of tool,
      still refresh framework), P2-23 (sniff YAML indent; make preamble/blockquote
      replacement fence-aware). *Shipped: PR #118. +15 tests; 593 passed.*
- [ ] **PR-12: README rewrite.** P3-2 (lead with v2 MD flow), P3-3 (For AI Agents:
      lead with starter.md), P3-4 (scope version-compat claim to v1 only).
- [x] **PR-13: Deliverable Synthesis capstone.** New optional `## Deliverable
      Synthesis` section in starter.md with `@anchor: synthesis` / `@end: synthesis`,
      triggered by 5th Empty-queue option; cite-or-cut guardrails; living section
      excluded from append-only invariant.
      *Shipped: 1.17.0. Edit A: option (5) added to empty-queue rule. Edit B:
      section scaffold after Changelog with instructional HTML comment (cite-or-cut,
      living-section semantics, validator exemption). Edit C: documented in File
      editing convention 3 and Self-validation mechanical checks. validator_md.py:
      `_LIVING_ANCHORS = frozenset({"synthesis"})` + `_check_anchor_preservation`
      skips living anchors. 5 new tests (`TestSynthesisLivingSection`). 602 passed,
      91.69% coverage. PR #123.*
- [x] **PR-14: Design spikes.** Three decisions shipped as v1.18.0:
      **P1-8 framework token overhead** — closed/no-change: the framework is
      load-bearing for agent compliance (empirically proven in sessions 16/17);
      splitting it would risk regressing the no-tool-call gate. Removed from
      "Future improvements". **v1 sunset** — deprecation warnings added to all
      v1 entry points (`build`, `validate`, `upgrade`, `init --v1`) steering
      users to migrate or use the v2 path. **P1-7 empty-queue UX** — new
      `agent_state: complete` value: validator warns on unknown states, `turn1`
      refuses complete-marked files with a remedy hint, and `starter.md`
      instructs the agent to greet + offer three options (new topics/synthesis/
      leave as-is) instead of running a session automatically.
      *Shipped: 614 passed, 91.71% coverage. PR to follow.*

Notes:
- P3-6 (framework headings use em-dashes its own rule forbids) and P3-7
  (`ui_strings` dead frontmatter) fold into PR-3 or PR-5 respectively.
- P3-13, P3-14 nits fold into whichever PR touches the relevant file.
- PRs follow the one-concern-per-PR rule [[feedback_pr_separation]].

## Future improvements (queued, not in the current batch)

Surfaced 2026-06-01 in a project-review pass. These are higher-leverage
than further test-suite polish but are design-heavy / outward-facing, so
they need a decision before execution rather than being picked up blind.

- ~~**Framework token overhead.**~~ **Closed (PR-14, 2026-06-23).** The
  framework is load-bearing for agent compliance — sessions 16/17 proved
  that agents without the full framework text skip the no-tool-call gate.
  Any split risks that regression with no reliable fix path. Decision:
  keep the full framework in the source file; do not pursue a cheatsheet
  split.

- **v2 escaping / trust model.** `build.py` runs Jinja with
  `autoescape=False`; the PR #53 review pushback ("agents are instructed
  not to embed JS") was reasonable for v1, where a human curates the
  JSON. But v2's whole premise is *LLM-authored Markdown* rendered to
  single-file HTML a human opens in a browser — a prompt-injected or
  sloppy agent emitting `<script>`/`onerror=` is now in the threat model.
  At minimum: document the trust boundary in the v2 docs. Ideally:
  sanitize the raw-HTML / `r_svg` passthrough on the v2 path.

- **v1 sunset with a dated target.** v1 is "deprecated" in prose but every
  feature still ships a dual path (`build`/`build_md`,
  `validator`/`validator_md`, `upgrade`/`upgrade_md`, plus `migrate`),
  roughly doubling surface area. A dated removal plan (e.g. v1 read-only
  in 2.0, removed in 2.1) would let us stop investing in the legacy half
  and shrink the codebase. Behavioural change for v1 users → needs a
  decision.

- **User-facing CHANGELOG.** `status/next-session.md` is an excellent
  internal log but there's no `CHANGELOG.md` for `pip` upgraders — a
  published PyPI package should have a "what changed" surface.

- **Consistent encoding-error handling across all file reads.** PR #93
  hardened the JSON-read paths (`build`/`validate`/`upgrade`/`migrate`)
  to catch `UnicodeDecodeError` alongside `json.JSONDecodeError`, so a
  `.json` with invalid UTF-8 bytes reports cleanly instead of crashing.
  The remaining `read_text` sites are still unguarded and will traceback
  on bad bytes: v2 Markdown build (`perform_build_md`), the `--theme`
  / frontmatter `theme_css` / conventional `theme.css` loads, and the
  bundled-starter loads in `_shared.py` / `upgrade_md`. Do it in one
  pass for parity — ideally a small shared `read_text_or_error` helper
  rather than scattering try/except, so the message/exit-code behaviour
  stays uniform.

- **Consistent temp-file cleanup across all atomic writers.** Surfaced in
  the #95 review: `bump`, `upgrade`, `migrate`, and `init` all do
  `tmp.write_text(...)` → `tmp.replace(target)` with no cleanup, so a
  failed write leaves a `.tmp` behind. Low-severity (atomic-write cruft),
  but worth one consistent pass — a shared `atomic_write(path, text)`
  helper wrapping the write/replace in `try/finally` — rather than a
  one-off in any single command. Pairs naturally with the encoding helper
  above (both are "centralize a file-I/O concern" cleanups).

- **Mobile-friendly tab bar.** Symptom: when a document has many
  tabs, the top menu overflows off-screen on mobile with no way to
  scroll. Likely fix in `src/research_buddy/css/`: horizontal
  `overflow-x: auto`, momentum scrolling, fade-edge scroll
  indicators, and/or a hamburger fallback below a breakpoint. Needs
  a real mobile device (or devtools emulation) to verify.

- **Real PDF generator.** Current `--pdf` runs WeasyPrint over the
  dark-themed HTML, which looks wrong on paper. Options:
  (a) print-specific CSS — `@media print` with light theme, page
  breaks, real headers/footers; (b) a separate JSON → PDF path
  (ReportLab or similar) that treats PDF as a first-class output,
  not a side effect of HTML. (a) is cheaper and probably good
  enough; (b) is a bigger investment.

[#24]: https://github.com/nuncaeslupus/research-buddy/pull/24
[#26]: https://github.com/nuncaeslupus/research-buddy/pull/26
[#36]: https://github.com/nuncaeslupus/research-buddy/pull/36
[#40]: https://github.com/nuncaeslupus/research-buddy/pull/40
