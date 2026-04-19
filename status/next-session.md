# Next session

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
  [#20] (this branch), open.

### Next steps

1. Merge PR #20 (`docs/queue-mutation-testing`) to finalise the
   ten-step ordering. Look at reviews in the PR first!
2. Kick off roadmap step #2 — pre-commit hooks. Branch:
   `chore/pre-commit-hooks`. Contents: `.pre-commit-config.yaml`
   running `ruff check`, `ruff format`, `mypy`, and
   `make check-version-sync` on every commit. Document
   `pre-commit install` in project `CLAUDE.md`.
3. After #2, move to step #3 (Dependabot) — small config-only PR.

### Blockers

- None.

[#19]: https://github.com/nuncaeslupus/research-buddy/pull/19
[#20]: https://github.com/nuncaeslupus/research-buddy/pull/20