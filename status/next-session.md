# Next session

## Session 2026-04-19 (session 2)

### What was done

- **Resolved the queued upstream-proposals item.** Read the three
  reference files in `ai-trading-system` (draft issue body,
  `scripts/upgrade_research_buddy.py` reference impl, `docs/dev/
  research-buddy-upgrade.md` runbook) to size the work.
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
