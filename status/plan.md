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
- [x] **10. Split `build.py` (796 lines).** Folded into the Jinja2
      migration listed in "Future improvements" — the renderer
      split would have been torn out a step later. Each `r_*`
      block renderer is now a 1–4 line wrapper around a Jinja
      macro in `src/research_buddy/templates/`; the f-string
      scaffold at the bottom of `build_html()` is now
      `base.html.j2`.
      *Shipped via the Jinja migration.*

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
