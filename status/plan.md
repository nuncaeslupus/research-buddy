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

- [ ] **11. `research-buddy bump <source.md> <queue-id>`.** Single
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
      New module `src/research_buddy/bump.py` + CLI handler in
      `main.py`. Tests in `tests/test_bump.py`.
- [ ] **12. Starter marker hygiene.** `starter.md` currently has
      prose like *"paste this immediately before its `<!-- @end:
      rules -->` marker"* outside fenced code blocks. The validator
      is fence-aware so this doesn't false-positive *validation*,
      but it does false-positive the agent's `grep` for insertion
      points (which is what the v1.12 session transcript showed —
      the agent hit "found multiple times" on `@end: journey` and
      had to retry str_replace with bigger context). Fix: wrap each
      scaffolding example in `starter.md` inside a fenced block.
      Ship an `upgrade` pass so existing v2 projects pick it up.
      One-line starter change + small `upgrade_md.py` extension.
- [ ] **13. `research-buddy locate <source.md> <anchor>`.** Returns
      the line number + ~5 lines of surrounding context for the
      *live* `@end: <anchor>` marker, skipping fenced and HTML-
      comment-template instances (reusing `validator_md._line_in_fence`).
      Lets the agent jump straight to insertion points without
      grepping. Smaller than `bump` but useful for ad-hoc edits
      between sessions. New CLI subcommand only — no new module
      needed, calls into `validator_md` helpers.
- [ ] **14. `research-buddy diff-summary <old.md> <new.md>`.** Emits
      the `<!-- @summary-start --> ... <!-- @summary-end -->` block
      by diffing the two versions: rules added/revised, DAs added,
      queue rows moved, version bump, append-only-invariant check.
      Pure-mechanical portions only — the narrative paragraphs at
      the top of the summary stay agent-authored. Wraps existing
      diff logic in `validator_md._check_append_only` and
      `_collect_entry_ids`. New module
      `src/research_buddy/diff_summary.py` + CLI handler.

## Future improvements (queued, not in the current batch)

Surfaced 2026-06-01 in a project-review pass. These are higher-leverage
than further test-suite polish but are design-heavy / outward-facing, so
they need a decision before execution rather than being picked up blind.

- **Framework token overhead (highest leverage).** The framework block
  rides in *every* source file an agent uploads, *every* session
  (`starter.md` is ~674 lines). This is a per-session tax on the core
  2-turn workflow — the product's whole reason to exist. Flagged in
  session 16 as the unaddressed survivor, then dropped. The idea worth a
  real design pass: a short agent-edited source file + a separate
  `framework-cheatsheet.md` the agent reads once, so the per-session
  payload shrinks. Needs care: the framework is load-bearing for agent
  compliance (see sessions 16/17), so any split must not regress the
  no-tool-call gate or the session-state detection.

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
