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
- [ ] **7a–7j. Mutation-survivor cleanup, one module per step.**
      Ordered ascending by survivor count so the smallest, most
      tractable modules ship first. For each: run `mutmut-report`
      with `--module <name>`, classify survivors into real-gap /
      equivalent / untestable, add tests for the real gaps, accept
      the rest. Goal per module: zero remaining REAL_GAP survivors.
      - [x] **7a.** `validator` (46 survivors → 6 accepted
            equivalents). Smallest module; also the one we just
            brought to 100% line coverage in #6 — a load-bearing
            demonstration that line coverage ≠ mutation kill rate.
            *Shipped: 19 new tests in `tests/test_validator_mutations.py`
            kill all 40 REAL_GAP survivors; 6 remain as accepted
            equivalents (4× `_load_schema` encoding variants on an
            ASCII file, 2× `>1` vs `>=1` boundary that produces
            identical output on a single-element list).*
      - [x] **7b.** `table_layout` (49 survivors → 10 accepted
            equivalents). Survivors classified into 39 REAL_GAP +
            10 EQUIVALENT. New `tests/test_table_layout_mutations.py`
            (20 tests across 9 classes) kills all 39 real gaps; the
            10 equivalents (`_layout_from_profiles#52/75/79` plus all
            seven `compute_layouts` mutations on the `is not None`
            fallback) are documented in `next-session.md`.
      - [ ] **7c.** `clean_md` (52).
      - [ ] **7d.** `upgrade` (88).
      - [ ] **7e.** `upgrade_md` (188).
      - [ ] **7f.** `validator_md` (308).
      - [ ] **7g.** `build_md` (384).
      - [ ] **7h.** `build` (630).
      - [ ] **7i.** `main` (849).
      - [ ] **7j.** `migrate_v1_to_v2` (1198). Largest; tackle
            last so the muscle is built up on the smaller modules
            first.
- [ ] **8. Coverage threshold in CI.** Add `--cov-fail-under=85` to
      pytest and wire `pytest-cov` into the CI test job. Optional:
      codecov upload + badge in README.
- [ ] **9. Split `main.py` (421 lines).** Extract `cli.py`
      (argparse wiring) + `commands/{build,init,validate}.py`. Keep
      `main.py` as a thin shim re-exporting `main` for the console
      script.
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
