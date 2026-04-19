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
- [ ] **2. Pre-commit hooks.** `.pre-commit-config.yaml` running
      `ruff check`, `ruff format`, `mypy`, and `make check-version-sync`
      on every commit. Document `pre-commit install` in `CLAUDE.md`.
- [ ] **3. Dependabot.** `.github/dependabot.yml` covering `pip`
      (weekly) and `github-actions` (weekly). Groups minor+patch so
      we don't drown in noise.
- [ ] **4. Python 3.13 in CI.** Add `3.13` to the `test` job's matrix
      in `.github/workflows/ci.yml`. Lint job stays on 3.12.
- [ ] **5. Schema self-test.** One pytest in `tests/test_schema.py`
      that loads `schema.json` and validates it against the Draft
      2020-12 meta-schema. Catches typos in the schema itself.
- [ ] **6. Raise coverage.** `main.py` (64% → ≥85%) and `validator.py`
      (63% → ≥85%). Target the untested branches: `--watch`, `--pdf`,
      `--all`, batch mode, validator error paths, version-compat
      tiers.
- [ ] **7. Mutation-testing baseline.** Install `mutmut`, configure
      it against `src/research_buddy/`, and capture a baseline
      survivor count. Acts as a quality check on the coverage raised
      in #6: high line-coverage with weak assertions still lets
      mutants survive. The `mutmut-report` skill at
      `.claude/skills/mutmut-report/` analyzes the run and groups
      survivors into real-gap / equivalent / untestable. Fix the real
      gaps, accept the rest.
- [ ] **8. Coverage threshold in CI.** Add `--cov-fail-under=85` to
      pytest and wire `pytest-cov` into the CI test job. Optional:
      codecov upload + badge in README.
- [ ] **9. Split `main.py` (421 lines).** Extract `cli.py`
      (argparse wiring) + `commands/{build,init,validate}.py`. Keep
      `main.py` as a thin shim re-exporting `main` for the console
      script.
- [ ] **10. Split `build.py` (796 lines).** Create a `renderers/`
      package with one module per block type and a dispatch registry
      (`RENDERERS: dict[str, Callable[[Block, BuildState], str]]`).
      `build.py` keeps only `build_html`, helpers, and constants.

## Future improvements (queued, not in the current batch)

- **Jinja2 templates.** Replace the hand-rolled HTML string assembly
  in `build.py` (and the `r_*` renderers) with Jinja2 templates
  living in `templates/`. Benefits: fewer HTML-escaping bugs,
  designer-friendly, easier to diff. Cost: new runtime dep, template
  discovery via `importlib.resources`, and a meaningful rewrite of
  every renderer. Schedule after #9 — the renderer split is a
  prerequisite.

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
