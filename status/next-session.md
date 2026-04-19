# Next session

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
