# Next session

## Session 2026-06-23 (session 43)

### What was done

Shipped **PR-1 remainder** (PR #127) and **PR-12: README rewrite** (PR #128).
The Opus review fix initiative is now fully complete — all 14 PR batches shipped.

**PR-1 remainder — CHANGELOG backfill (PR #127):**
- Added missing entries for 1.14.0, 1.15.0, 1.16.0, 1.17.0 (released during
  the Opus review initiative but never documented in CHANGELOG.md).
- 1.14.0 entry is the most substantial: covers the full Opus review batch
  (fileio.py, validator hardening, migrate collision fixes, clean_md, build
  safety, upgrade edge cases, framework truth-up, release workflow safety).
- 1.15.0–1.17.0 entries cover PR-4/5/13 (brief-skeleton, methodology,
  deliverable synthesis).
- plan.md: PR-1 checkbox marked [x] (the P0-2 and P3-5 code changes shipped in
  PR #117 session 35; P3-1 backfill now complete).

**PR-12: README rewrite (PR #128):**
- "Research protocol" rewritten to lead with v2: names the brief gate and
  `turn1`, uses `*_vX.Y-source.md` naming, presents v1 as a parenthetical.
- "File naming" split into v2 Markdown (recommended) and v1 JSON (legacy)
  sub-tables; v2 table includes the clean-view `*_vX.Y.md` artifact.
- "Batch Processing" heading → "(v1 JSON only)".
- "Document format", "Block types", "Schema compatibility" headed with "(v1 JSON)"
  and a note pointing at `starter.md` for v2.
- "Version compatibility" split into "v1 JSON: active version check" (existing
  table, now correctly scoped) and "v2 Markdown: agent-managed version" (new
  paragraph; removes the incorrect "comparison behavior is identical for both
  formats" claim).
- Two Gemini review fixes: `[file_name]_v1.0.md` → `[file_name]_vX.Y.md` (file
  naming table); "the v1 CLI" → "the CLI (for v1 documents)" (no separate binary).
- plan.md: PR-12 checkbox marked [x].

### Next steps

1. **The Opus review fix initiative is complete.** All open plan.md items
   are now [x] or [~]. The remaining "Future improvements" backlog:
   - v2 escaping / trust model (`autoescape=False` + LLM-authored source)
   - v1 sunset with a dated target (v2.0 removal of `init --v1`; v3.0 full removal)
   - User-facing CHANGELOG (already done — #127 completes the backfill)
   - Mobile-friendly tab bar
   - Real PDF generator
2. No immediate code work needed. Next session can pick up any "Future
   improvements" item or address a real user-reported issue.

### Blockers

- None.

## Session 2026-06-23 (session 42)

### What was done

Shipped **PR-7b: migrate dedup + drop marker** — the last deferred item in the
Opus review fix initiative. Two items in one PR (#125):

**P2-10 — verdict `<a id>` deduplication.**
- New `_unique_aid(base_aid, seen_ids)` helper after `_slug`. Returns `base_aid`
  unchanged when `seen_ids is None` (backward compat). On collision, appends
  `-2`, `-3`, … suffixes. Guards against empty `base_aid` (from a label
  containing only punctuation) by falling back to `"anchor"`.
- `seen_ids: set[str] = set()` created in `migrate()` and passed to every
  verdict-capable builder: `build_overview_tab`, `build_domain_tab`,
  `build_discarded_alternatives`, `build_session_notes`, `build_reasoning_journey`,
  `build_references`, `build_changelog`. The `<!-- @rule: R-FM-1 -->` marker
  keeps the original id (so validators can detect real data errors); only the
  HTML `<a id>` is deduplicated.

**P2-13c — dropped-content marker.**
- `INTENTIONALLY_DROPPED_RESEARCH_SECTIONS = frozenset({"Research Methodology"})`
  (the v2 in-file framework replaces it).
- `_dropped_research_sections(research_tab)` returns sorted names of dropped
  sections present in the source.
- `migrate()` inserts an HTML comment before `## Project Specification` when any
  sections are dropped.
- `main()` prints a stderr warning listing dropped sections after migration.

Tests: `TestVerdictLabelDedup` (9 tests) + `TestDroppedContentMarker` (8 tests).

Follow-up fixes after Gemini code review on the PR (also in #125):
- Empty `base_aid` guard in `_unique_aid` (guarded `<a id="">` risk).
- `seen_ids` threading extended to all remaining render-calling builders
  (`build_session_notes`, `build_reasoning_journey`, `build_references`,
  `build_changelog`) — the initial implementation only covered domain tabs,
  overview, and discarded alternatives.

Gates: `make lint` clean, **631 passed**, **91.79%** coverage. PR #125 merged.

### Next steps

1. **PR-12: README rewrite** — P3-2 (lead with v2 MD flow), P3-3 (For AI
   Agents: lead with starter.md), P3-4 (scope version-compat claim to v1 only).
   The Opus review fix initiative is now **complete** (PR-7b was the last open
   item; PR-12 README and PR-1 release safety remain).
2. **PR-1: Release safety** — P0-2 (move tag after publish in release.yml),
   P3-1 (backfill CHANGELOG.md), P3-5 (per-version release notes extraction).
   One open follow-up: verify the per-version release notes extraction works
   end-to-end on the next real release.

### Blockers

- None.

## Session 2026-06-23 (session 41)

### What was done

Shipped **PR-14: Design spikes** — three design decisions + implementations,
versioned as **1.18.0**:

**Decision 1 — P1-8 framework token overhead: closed/no-change.**
The framework is empirically load-bearing for agent compliance (sessions 16/17
showed agents without the full text skip the no-tool-call gate). Any "separate
cheatsheet" split would risk that regression. Decision recorded in plan.md
"Future improvements" as closed; no code change.

**Decision 2 — v1 sunset: deprecation warnings on all v1 entry points.**
Added `"Warning: v1 JSON format is deprecated and will be removed in v2.0. …"`
to stderr in every v1 code path:
- `commands/build.py` `perform_build` (after JSON load): steer to `migrate-v1-to-v2`
- `commands/validate.py` `cmd_validate` (after JSON load): same
- `commands/upgrade.py` `cmd_upgrade` (before json.load try-except): same
- `commands/init.py` `_init_v1` (already existed, not added): steer to
  `research-buddy init` without `--v1`

Tests: `TestV1DeprecationWarning` (4 tests) in `test_main_coverage.py`.

**Decision 3 — P1-7 empty-queue UX: add `agent_state: complete`.**
Three-part implementation:
- `validator_md.py`: `_VALID_AGENT_STATES = frozenset({"needs_session_zero",
  "ready", "complete"})` + unknown-state warning in `_check_frontmatter`.
- `turn1.py`: guard in `build_brief_skeleton` — raises `Turn1Error` if
  `agent_state == "complete"` with a remedy hint (`set agent_state: ready`).
- `starter.md`: preamble `agent_state` description updated; new bullet in
  `detect-session-state` for the `complete` case (greet + offer three options:
  add queue / write synthesis / leave as-is); queue rule empty-queue option (4)
  now says "set `agent_state: complete` in the YAML frontmatter on the Turn 2
  atomic write".

Tests: `TestAgentStateValidation` (5) in `test_validator_md.py`;
`TestCompleteState` (3) in `test_turn1.py`.

Gates: `make lint` clean, `make test-cov` **614 passed** (↑12), **91.71%**
coverage, examples in sync (after `make regen-examples`), starter validates
error-clean, version-sync 1.18.0 in all five files.

### Next steps

1. **PR-7b: migrate dedup + drop marker (deferred)** — P2-10 (verdict-label
   dedup, needs renderer-wide `seen_ids`) + P2-13c (dropped-content marker,
   needs clearer spec). Only open item in the Opus review fix initiative
   besides PR-12. Still deferred.
2. **PR-12: README rewrite** — P3-2 (lead with v2 MD flow), P3-3 (For AI
   Agents: lead with starter.md), P3-4 (scope version-compat claim to v1 only).
3. **PR-1: Release safety** still has an outstanding open item (verify the
   per-version release notes extraction works end-to-end on the next release).

### Blockers

- None.

## Session 2026-06-23 (session 40)

### What was done

Shipped **PR-13: Deliverable Synthesis capstone** — versioned as **1.17.0**:

- **Edit A — Empty-queue option (5).** Added "(5) synthesize deliverable — write or
  refresh the `## Deliverable Synthesis` section, compiling the tracker findings into
  the project's stated deliverable form" to the empty-queue rule in Queue rules.
- **Edit B — Section scaffold.** New `## Deliverable Synthesis` section after
  `## Changelog`, with `<!-- @anchor: synthesis -->` / `<!-- @end: synthesis -->` pair
  and an instructional HTML comment covering cite-or-cut rule, living-section
  semantics (rewrite wholesale each refresh), and validator exemption.
- **Edit C — Framework documentation.** Living-section exception added to File editing
  convention 3 (append-only sections list) and to the Self-validation mechanical checks
  bullet. Cross-links to `#deliverable-synthesis` were intentionally NOT used in
  framework prose — the section is optional and its absence would produce
  broken-cross-link errors in migrated docs; backtick notation used instead.
- **validator_md.py.** New `_LIVING_ANCHORS = frozenset({"synthesis"})` constant near
  the diff-based checks section. `_check_anchor_preservation` skips anchors in this
  set — removing the synthesis section from one version to the next does not fire
  `anchor-removed`.
- **Tests.** `TestSynthesisLivingSection` (5 tests): anchor-removed does not fire when
  synthesis disappears; non-synthesis anchors still fire; synthesis in both versions
  passes; content rewrite generates no append-only errors.

Gates: `make lint` clean, `make test-cov` **602 passed** (↑4), **91.69%** coverage,
examples in sync, starter validates error-clean. PR: #123.

### Next steps

1. **PR-12: README rewrite** — P3-2 (lead with v2 MD flow), P3-3 (For AI Agents:
   lead with starter.md), P3-4 (scope version-compat claim to v1 only).
2. **PR-14: Design spikes** — P1-8 framework token overhead, v1 sunset, P1-7
   empty-queue UX.

### Blockers

- None.

## Session 2026-06-23 (session 39)

### What was done

Shipped **PR-5: Methodology completeness** — six editorial additions to `starter.md`, versioned as **1.16.0**:

- **P1-3 — Turn-2 hypothesis resolution step.** Added new Turn 2 step 3: "Resolve pre-registered hypotheses" — compare findings + vetted second opinions against pre-registered PASS/FAIL metrics, assign `VALIDATED` / `PROPOSED` / `REJECTED` to each. The prior flow pre-registered hypotheses in Turn 1 step 4 but never had an explicit Turn 2 step to resolve them. Steps 3–8 renumbered to 4–9; "Turn 2 step 3 gates step 4" in Common failure modes updated to "step 4 gates step 5."
- **P1-3 — Session-note template synced with `bump.py`.** Added hypothesis-resolution table (`| Hypothesis | Pre-registered metric | Outcome | Evidence |`), `**Cross-section impact.**`, and `**Compliance validation.**` fields to the `### Templates` session-note block; aligned placeholder style (`{{…}}`) and link format. Template now matches `_session_skeleton()` output exactly.
- **Sync guard: `TestSessionSkeletonSyncWithStarterTemplate` (2 tests)** in `test_bump.py` — section-heading and table-header rows from `_session_skeleton` must appear in the starter.md template.
- **P1-5 — Excellence bar guidance.** Note in §Second-opinion brief template explaining that `{{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}` must specify minimum source count, domain rigor standard, and specificity requirement.
- **P1-5 — Queue prioritization rubric.** 4-point rubric (dependency, risk-to-deliverable, yield-per-turn, evidence freshness) in §Queue rules.
- **P1-5 — Rule supersession mechanics.** Step-by-step in §Adopted Rules for updating old rule to `SUPERSEDED` + `superseded_by`, new rule to `supersedes`, Changelog note.
- **P1-5 — Queue/tracker dual-membership rule.** Explicit MUST NOT in §Queue rules (Done items + Re-queuing paragraphs); new `[mechanical]` Common failure mode entry.

Gates: `make lint` clean, `make test-cov` **598 passed** (↑2), **91.68%** coverage, examples in sync, starter validates error-clean. PR: #121.

### Next steps

1. **PR-12: README rewrite** — P3-2 (lead with v2 MD flow), P3-3 (For AI Agents: lead with starter.md), P3-4 (scope version-compat claim to v1 only).
2. **PR-13: Deliverable Synthesis capstone**, **PR-14: Design spikes**.

### Blockers

- None.

## Session 2026-06-23 (session 38)

### What was done

Shipped **PR-4: Brief-skeleton unification** — one editorial fix + two sync tests, versioned as **1.15.0**:

- **P1-2 — Unify preamble skeleton + `turn1.py` placeholder names.** The preamble's compact brief skeleton (inside the HTML comment operating manual) used 4 shorter placeholder names that differed from the canonical `Second-opinion brief template` in `framework.reference.brief`. An agent hand-writing from the preamble would produce different placeholder names than `research-buddy turn1` output. Fixed by updating to canonical names and adding the missing article "a":
  - `{{PROJECT_AND_CHARACTERISTICS}}` → `{{PROJECT_AND_BASIC_CHARACTERISTICS}}`
  - `{{LIST_OF_QUESTIONS}}` → `{{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}`
  - `{{RESEARCH_EXCELLENCE_LEVEL}}` → `{{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}`
  - `{{TIER_1_AND_TIER_2}}` → `{{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}`
- **Sync guard tests** (`TestBriefSkeletonSyncWithCanonicalTemplate` in `test_turn1.py`, 2 tests):
  - `test_static_prose_lines_appear_in_brief_output` — every non-placeholder prose line from the canonical template must appear in `turn1` output.
  - `test_placeholder_names_in_turn1_source_match_canonical` — every canonical placeholder name (except `TIER_REJECT_RULES`, pre-filled by `turn1`) must appear in `turn1.py`'s source code.
- **Version bump 1.14.0 → 1.15.0.** `make version-sync` + `make regen-examples`. 596 passed, lint clean, examples in sync.

PR: #120.

### Next steps

1. **PR-5: Methodology completeness** — P1-3 (Turn-2 hypothesis resolution step + session-note template matches `bump.py`), P1-5 (excellence bar guidance, queue prioritization rubric, rule supersession mechanics, queue/tracker dual-membership rule).
2. **PR-12: README rewrite**, **PR-13: Deliverable Synthesis**, **PR-14: Design spikes**.

### Blockers

- None.

## Session 2026-06-23 (session 37)

### What was done

Shipped **PR-3: Framework ↔ tooling truth-up** — five editorial fixes to `starter.md`, versioned as **1.14.0**:

- **P0-1(a) + P1-1 — Surface bump/locate/diff-summary as blessed Turn-2 path.** Three places updated:
  - Preamble "Tools at hand" line now lists `bump <file> <Q-NNN> --apply` (all mechanical Turn-2 edits), `locate <file> <anchor>` (exact `@end` insertion-point line), and `diff-summary <prior.md> <new.md>` (mechanical `@summary` block) with one-line descriptions, placed before the existing `validate`/`turn1` entries.
  - Turn-2 step 4 ("Write atomically") opens with the `bump --apply` shortcut and `locate` guidance; the manual per-section list follows as the no-shell-access path.
  - Turn-2 step 6 (change summary) adds the `diff-summary` shortcut with its `{{placeholder}}` narrative note.
- **P1-4 — Fix version-compat pause contradiction.** "Both flows are exactly 2 turns, with no confirmation gate between them" was contradicted by the MINOR version-compat check that says "Wait for the answer" before Turn 1. Rewritten: "Both session flows use exactly **2 turns** (Turn 1: brief + research; Turn 2: vet + validate + write) with no confirmation gate between them. The MINOR version-compat check above is a pre-session gate: if it fires, the user answers one question before Turn 1 begins; the session's 2-turn clock starts only once the user picks (a) or (b)."
- **P1-6 — Fix "validate mechanically flags plain-text refs" claim.** The validator does NOT check for plain-text `R-XXX-N`/`DA-XXX`/`Q-NNN` references (only broken cross-links). Removed the false bullet from the mechanical-checks list; changed `[mechanical]` → `[semantic]` in the corresponding failure-mode entry.
- **P3-8 — Add `research_buddy_version` to required-fields list.** The self-validation mechanical check listed `doc_format_version, version, date, file_name, title, language.code, project.domain` but omitted `research_buddy_version`, which has been required by the validator since early development. Fixed.
- **Version bump 1.13.0 → 1.14.0.** `make version-sync` + `make regen-examples`. 594 passed, lint clean, examples in sync.

### Next steps

1. **PR-4: Brief-skeleton unification** — P1-2 (single canonical template; unify preamble skeleton + `turn1.py` wording; sync test).
2. **PR-5: Methodology completeness** — P1-3 (Turn-2 hypothesis resolution step + session-note template matches `bump.py`), P1-5 (excellence bar guidance, queue prioritization rubric, rule supersession mechanics, queue/tracker dual-membership rule).
3. **PR-12: README rewrite**, **PR-13: Deliverable Synthesis**, **PR-14: Design spikes**.

### Blockers

- None.

## Session 2026-06-23 (session 36)

### What was done

Shipped **PR-11: upgrade edge cases** — three items across `upgrade.py`,
`upgrade_md.py`, and `commands/upgrade.py`:

- **P2-21 — v1 forward-only version guard.** `upgrade_doc` in `upgrade.py` now
  checks `meta.research_buddy_version` before overwriting: if the doc is ahead of
  the installed tool, it appends a `"not bumped"` note to changes and skips the
  overwrite rather than silently downgrading. Uses `_parse_semver` from
  `validator.py` (same guard v2 already had).
- **P2-22 — v2 skip only version bump when doc is ahead.** `_bump_research_buddy_version`
  in `upgrade_md.py` no longer raises `UpgradeError` when the doc is ahead; it
  returns an informational note so the rest of the upgrade (preamble, framework
  block, agent-reminder blockquote) still runs. `_upgrade_md_file` gains a
  `upgraded == source_text` guard so an informational-only run doesn't write the
  file needlessly. Updated `test_doc_ahead_of_tool_raises` →
  `test_doc_ahead_of_tool_skips_version_bump`.
- **P2-23 — YAML indent sniff + fence-aware preamble/blockquote search.** Three
  sub-fixes in `upgrade_md.py`:
  - New `_sniff_project_indent` / `_reindent_insertion` helpers: `_insert_in_project_block`
    now detects the actual indent of existing `project:` children and reindents
    inserted lines to match (fixes 2-space insertions into 4-space YAML docs).
  - `_find_preamble_bounds` skips fenced lines when searching for the first
    `<!-- @anchor: -->` (fence-aware).
  - `_find_agent_reminder_start` skips fenced lines so a `> **Agent:` inside a
    fenced example is ignored.
  - `_line_in_fence` import promoted to module level (was a local import in one
    function; now needed by three).

+15 tests. 593 passed, lint clean. PR: #118.

### Next steps

1. **PR-7b** (deferred): verdict-label dedup (renderer-wide `seen_ids`) +
   dropped-content marker. Complex; defer unless there's a clear spec.
2. **PR-3: Framework ↔ tooling truth-up** — teach `bump`/`locate`/`diff-summary`
   as the blessed Turn-2 path in starter.md; fix version-compat pause contradiction;
   fix "validate mechanically flags plain-text refs" claim.
3. **PR-4: Brief-skeleton unification**, **PR-5: Methodology completeness** — the
   big editorial batches.
4. **PR-12: README rewrite**, **PR-13: Deliverable Synthesis**, **PR-14: Design spikes**.

### Blockers

- None.

## Session 2026-06-23 (session 35)

### What was done

Shipped **PR-1: Release safety + changelog** — three items:

- **P0-2 — tag after publish.** Moved the annotated-tag push from the `build`
  job to the `github-release` job in `.github/workflows/release.yml`. Previously
  a failed PyPI publish would leave an orphaned `vX.Y.Z` tag, locking the guard
  into "already tagged" forever. Tag creation now runs only after
  `publish-pypi` succeeds (`needs: [guard, publish-pypi]`). Removed the now-
  unnecessary `permissions: contents: write` from the `build` job.
- **P3-1 — CHANGELOG backfill.** Added 17 missing entries covering v1.2.0–
  v1.13.0, reconstructed from `status/next-session.md` session logs. CHANGELOG
  now has complete coverage from v1.0.3 through v1.13.0 (23 entries).
- **P3-5 — per-version release notes.** Replaced the `--notes-file CHANGELOG.md`
  approach (which dumped the entire history) with a Python heredoc that extracts
  only the `## [VERSION]` section matching the release being cut, writing it to
  `/tmp/release-notes.md` before `gh release create`. Uses
  `r"(?m)^## \[" + re.escape(ver) + r"\].*?(?=^## \[|\Z)"` with `re.DOTALL`.

No new tests (workflow-only + doc change). Gates: `make lint` clean, `make test`
**588 passed**.

PR: #117.

### Next steps

1. **PR-7b** (deferred): verdict-label dedup (renderer-wide `seen_ids`) +
   dropped-content marker.
2. **PR-11 (upgrade edge cases)**, then the PR-3/4/5 starter.md editorial
   batches (the biggest editorial lift), and PR-12/13/14.

### Blockers

- None.

## Session 2026-06-23 (session 34)

### What was done

Shipped **PR-8: build safety + render bugs** — five items across
`commands/build.py`, `build_md.py`, `build.py`, and `validator_md.py`:

- **P0-3 — gate the render on validator errors.** `perform_build_md` now
  aborts (exit 1, no HTML written) when `validate_md` returns error-severity
  issues; warnings still build. Pairs with PR-2 (broken cross-links are now
  errors). The existing error test was strengthened to assert no HTML is
  written. The v2 starter and all valid fixtures build clean, so no test broke.
- **P2-14 — escape tab labels.** `data-tab-label="{label}"` used the raw H2
  text; a `"` broke the attribute. Now `html.escape(label, quote=True)`.
- **P2-15 — multi-paragraph inline.** `_md_render_inline` dropped multi-`<p>`
  output verbatim into `<li>`. Found a deeper bug while fixing: the
  single-paragraph `re.fullmatch(r"<p>(.*?)</p>", …, DOTALL)` *also* matches
  multi-paragraph output (the trailing `</p>` anchors to EOF), returning a
  body that still contained `</p><p>`. Fixed by rejecting that branch when the
  capture has an interior `</p>`, then joining real paragraphs with `<br><br>`.
- **P2-17 — neutralize `</style>`.** New shared `build._neutralize_style_close`
  backslash-escapes any `</style>` in user theme CSS before it's inlined into
  the `<style>` block (Jinja is `autoescape=False`). Applied on both the v1
  (`build.py`) and v2 (`build_md.py`) theme paths.
- **P3-V2-TRUST — dangerous-HTML warnings.** New `_check_dangerous_html` warns
  (`unsafe-html-script` / `-event-handler` / `-js-uri`) on `<script>`, inline
  `on*=`, or `javascript:` in the body, skipping fenced and inline code. The
  bundled starter is clean of these.
- **P2-16 was already shipped in PR-10** (non-UTF-8 MD-source guard) — verified,
  not re-done.

8 new tests (`TestBuildSafety`, `TestThemeOverride` addition, `TestDangerousHtml`,
strengthened CLI gate test). Gates: `make lint` clean, `make test-cov`
**586 passed**, **91.68%**.

This partially closes the "v2 escaping / trust model" backlog item (the
`</style>` break-out is neutralized and dangerous patterns are flagged); full
`r_svg`/raw-HTML sanitization on the v2 path remains open.

### Next steps

1. **PR-1 (release safety + changelog)** — P0-2 (`release.yml`: move tag after
   publish), P3-1 (backfill `CHANGELOG.md` since v1.2.0), P3-5 (extract
   current-version section for release notes).
2. **PR-7b** (deferred): verdict-label dedup (renderer-wide `seen_ids`) +
   dropped-content marker.
3. **PR-11 (upgrade edge cases)**, then the PR-3/4/5 starter.md editorial
   batches (the biggest editorial lift), and PR-12/13/14.

### Blockers

- None.

## Session 2026-06-23 (session 33)

### What was done

Shipped **PR-2: append-only enforcement** — four validator hardening items in
`validator_md.py`, each verified against the real code first (the scoping agent
was wrong on two points, corrected below):

- **P0-1(b) — extend `_check_append_only`.** Added **tracker-row preservation**
  (every `Q-`/`T-` first-column id in prior must remain; the seed `T-000` is
  exempt, matching `_section_has_entries`) and **individual reference-bullet
  preservation** (the existing H3 check only caught whole per-version
  subsections, not a single citation dropped from within one). **Session-id
  preservation was already enforced** — `_collect_anchors` collects `@session`
  markers, so a removed session already fires `anchor-removed`; adding a
  dedicated `session-id-removed` check would just double-report, so it was
  intentionally omitted (documented).
- **P2-1 — `_check_unclosed_fence`.** New always-run check: a fence opened with
  ``` / ~~~ and never closed before EOF is an error pointing at the opener.
  Without it the unclosed fence silently swallows the rest of the doc (every
  later marker/link/heading reads as code) and the other checks go quiet.
- **P2-2 — broken-cross-link → error.** A `[text](#slug)` with no matching
  target was a warning; now an error (a real dangling reference). The
  starter-mode `info` downgrade for illustrative example targets
  (`#r-xxx-1`, …) is preserved, so the bundled starter still validates
  error-clean.
- **P2-3 — `_collect_entry_ids` fence-aware.** It scanned the whole text with
  `re.MULTILINE`, collecting `@da`/`@rule`/`@session` markers from inside fenced
  template examples. Now skips fenced lines via `_line_in_fence`. (The agent
  claimed `_collect_anchors` needed the same fix — it's *already* fence-aware,
  so only `_collect_entry_ids` was touched.)

7 new tests (`TestPriorMode` additions, `TestUnclosedFence`,
`TestBrokenLinkStarterDowngrade`); updated `test_broken_link_warns` →
`test_broken_link_errors`. Gates: `make lint` clean, `make test-cov`
**577 passed**, **91.64%**.

Note: promoting broken-cross-link to error makes `bump`/`build`'s error gating
stricter for downstream docs with pre-existing dangling links — that's the
intent (the link is a real defect), and the starter is clean.

### Next steps

1. **PR-8 (build safety + render bugs)** — P0-3 (gate HTML render on validator
   errors; pairs naturally with PR-2 now that broken links are errors), plus
   P2-14..17 render-escaping fixes and P3-V2-TRUST (warn on `<script>`/`on*=`/
   `javascript:` in body).
2. **PR-7b** (deferred): verdict-label dedup (needs renderer-wide `seen_ids`
   threading) + dropped-content marker.
3. **PR-1 (release safety + changelog)**, then the PR-3/4/5 starter.md
   editorial batches (biggest editorial lift).

### Blockers

- None.

## Session 2026-06-22 (session 32)

### What was done

Shipped **PR-7: migrate hardening (bulk)** — 5 of the 7 audit items, all in
`migrate_v1_to_v2.py`, each confirmed against a repro before fixing:

- **P0-4a — patch-aware changelog sort.** `build_changelog._key` returned
  `(major, minor)`, collapsing `1.1.0` and `1.1.4` to the same key → unstable
  order. Now `re.findall(r"\d+", …)` → a padded 3-tuple `(maj, min, patch)`.
  (There is no literal `_normalize_version`; the version-normalization collision
  the audit named manifested here.)
- **P0-4b — collision-free queue IDs.** `_strip_done_rows_from_queue` synthesized
  `Q-{i+1}` from the row index, which could dup a tracker ID or an inline ID on
  another row. Now two-pass: collect existing inline IDs + `tracker_ids` into a
  `used` set, then assign the lowest free `Q-NNN`. Repro: an unlabeled first row
  + inline `Q-003` later + tracker `{Q-001}` produced `[Q-001, Q-003, Q-003,
  Q-004]` (two collisions); now `[Q-002, Q-003, Q-004, Q-005]`.
- **P0-4c — slugified verdict `<a id>`.** Both `_render_verdict_as_rule/_da` did
  `aid = rid.lower()`, leaving spaces/punctuation in the id when a label lacked a
  clean `R-`/`DA-` prefix. New `_slug()` helper; idempotent for well-formed ids
  (`R-FM-1` → `r-fm-1`, still pairs with `<!-- @rule: R-FM-1 -->`).
- **P2-11 — reserve canonical anchors.** `build_domain_tab` now mangles a label
  that slugs to a framework anchor (`References`, `Changelog`, …) to `…-tab`
  via a `CANONICAL_ANCHORS` set, so the framework section keeps the canonical id.
- **P2-12 / P2-13a — changelog dates.** Entries render `### vX.Y — DATE`; the
  synthetic top entry carries `meta.date`.
- **P2-13b — frontmatter tiers/rules.** `build_frontmatter` now writes
  `project.source_tiers` (tier_1 / tier_2 / discovery, matching `starter.md`) +
  `project.domain_rules`, recovered from the resolved project spec.

**Deferred to a follow-up (PR-7b), documented in plan.md:**
- **P2-10 (dedup verdict labels)** — needs a `seen_ids` set threaded through the
  whole `render_block`/`render_blocks`/`render_subsections` pipeline; too
  invasive to bundle safely with the collision fixes.
- **P2-13c (dropped-content marker)** — emit an HTML comment when content is
  intentionally dropped (e.g. `Research Methodology`). A design choice (what to
  mark, where) that needs a clearer spec than the audit gave.

8 new tests (`TestMigrateHardening`). Gates: `make lint` clean, `make test-cov`
**569 passed**, **91.53%**. The existing `TestEndToEnd` runs `validate_md` on
migrated output, so the new frontmatter + changelog-date format validate clean.

### Next steps

1. **PR-2 (append-only enforcement)** — validator-side P0-1(b) (tracker-row +
   session-id + bullet-level reference preservation in `_check_append_only`),
   P2-1 (`_check_unclosed_fence`), P2-2 (promote broken-cross-link to error),
   P2-3 (make `_collect_entry_ids` fence-aware). High-value correctness work.
2. **PR-8 (build safety + render bugs)** — P0-3 (gate HTML render on validator
   errors) + several P2 render escaping fixes.
3. **PR-7b** (the two deferred items above) when convenient.
4. Then the PR-3/4/5 starter.md editorial batches (biggest editorial lift).

### Blockers

- None.

## Session 2026-06-22 (session 31)

### What was done

Shipped **PR-6: clean_md correctness** (Opus review fix initiative). Both items
were confirmed as REAL bugs before touching code:

- **P2-8 — `collect_framework_targets` fence-awareness.** Verified against the
  live `starter.md`: the framework's `### Templates` subsection has fenced
  example blocks carrying `<a id="r-example-1">`, `<a id="da-example-1">`,
  `<a id="q-001">` and placeholder headings (`### Q-001: {{topic}}`, etc.).
  These were being collected as framework targets. The real harm: once an agent
  promotes Q-001 to the Research Tracker (emitting a genuine `<a id="q-001">`),
  a body link `[Q-001](#q-001)` would be unwrapped to plain text in the clean
  view — a broken/lost link. Fix: skip fenced lines using
  `validator_md._line_in_fence` (the same helper `commands/locate.py` reuses),
  iterating the framework region by absolute index. End-to-end check confirms a
  promoted `[Q-001](#q-001)` body link now survives `clean_md_text`.
- **P2-9 — `strip_framework_block` EOF content loss.** The last session's
  heads-up was right that the happy paths preserved content; the actual bug was
  the **malformed-opener path**. A `framework.core` opener with no matching
  `@end` did `break`, which dropped the opener and *every line after it* to EOF
  — directly contradicting its own comment ("leave the file untouched … to
  avoid silently destroying content"). Repro: `strip_framework_block("Body1\n
  <opener>\nBody2\nBody3\n")` returned just `"Body1\n"`. Fix: `out.extend(
  lines[i:]); break` so everything from the opener on is preserved verbatim.
  The existing `test_malformed_no_closer_leaves_text_intact` had encoded the
  buggy behavior (asserted only that the marker was absent, while its own
  comment admitted the body was dropped); corrected it to assert the body
  survives, and added `test_malformed_no_closer_preserves_surrounding_content`.

No import cycle: `validator_md` does not import `clean_md`. Tests: +2 net new
in `test_clean_md.py` (fence-skip + malformed-preserve) plus the corrected
existing test. Gates: `make lint` clean, `make test-cov` **561 passed**,
**91.42%**.

### Next steps

Continue the Opus review fix initiative (code fixes before the starter.md
editorial batches):
1. **PR-7 (migrate hardening)** — three P0-4 ID/version collision bugs
   (`_normalize_version`, two-pass queue-ID collision, slugify verdict labels)
   + four P2-10..13 correctness fixes, all in `migrate_v1_to_v2.py`.
2. **PR-2 (append-only enforcement)** — validator-side P0-1(b) (tracker-row +
   session-id + bullet-level reference preservation in `_check_append_only`),
   P2-1 (`_check_unclosed_fence`), P2-2 (promote broken-cross-link to error),
   P2-3 (make `_collect_entry_ids` fence-aware).
3. Then PR-8 (build safety) and the PR-3/4/5 starter.md editorial batches.

### Blockers

- None.

## Session 2026-06-22 (session 30)

### What was done

Shipped **PR-10: File-I/O helpers** (Opus review fix initiative, the
recommended-next batch).

- **New `src/research_buddy/fileio.py`** with two shared helpers:
  - `read_text_or_error(path)` — reads UTF-8, raises `FileReadError` on invalid
    bytes with a uniform message. Closes the gap where user `.md`/`theme.css`
    files with bad bytes would traceback (parity with the JSON reads PR #93
    hardened).
  - `atomic_write(path, text)` — temp-sibling write → `replace`, wrapped in
    `try/finally` so a failed write removes the `.tmp` (P2-20). After a
    successful rename the temp path is gone, so cleanup is a happy-path no-op.
- **Encoding guard wired into the build path** (the documented P2-16 gap):
  `perform_build_md` source read + the v1 (`perform_build`) and v2 theme loads
  now use `read_text_or_error` and return exit 1 with a clean stderr message.
- **`atomic_write` adopted by every atomic writer:** `commands/bump.py`,
  `commands/upgrade.py` (both the md text and the json dump — serialize to a
  string first), `commands/migrate.py`, `commands/init.py` (md + json), and
  `migrate_v1_to_v2.py`'s module `main()`.
- **Scoping note:** the bundled-starter loads in `_shared.py` / `upgrade_md`
  were left unguarded on purpose — they read our own ASCII files via
  `importlib.resources` (a `Traversable`, not a `Path`), so invalid UTF-8 isn't
  a real risk and the helper's `Path` API doesn't fit. Recorded in CLAUDE.md.
- Tests: `tests/test_fileio.py` (10 unit tests: valid/invalid UTF-8, message
  shape, atomic write/overwrite/non-ascii, no-tmp-on-success, tmp-cleanup when
  rename fails via monkeypatched `Path.replace`) + 2 integration tests in
  `TestPerformBuildMd` (bad-UTF-8 source and theme both report cleanly).

Gates: `make lint` clean, `make test-cov` **558 passed** (↑11 from 547),
**91.40%** coverage; end-to-end `init` smoke confirmed no `.tmp` leftover.

### Next steps

Continue the Opus review fix initiative. Recommended order (from session 29,
still valid):
1. **PR-6 (clean_md correctness)** — already scoped this session by a
   background agent. Two bugs: **P2-8** make `collect_framework_targets`
   fence-aware (reuse `validator_md._line_in_fence`, the same pattern
   `commands/locate.py` uses — iterate lines, skip `in_fence[i]` before the
   heading/`<a id>` regexes); **P2-9** `strip_framework_block` EOF content
   loss. **Heads-up on P2-9:** the agent could NOT pin the exact boundary from
   inspection alone — the happy paths it traced all preserved content. Start by
   writing reproduction tests (framework block at EOF; blank line(s) then body
   after `@end`; `---` + blank + body) and find which one actually drops
   content before touching the slicing at `clean_md.py:147-153`. Don't assume
   there's an off-by-one until a test proves it; it may be a thinner fix than
   the finding implies.
2. **PR-7 (migrate hardening)** — three P0-4 ID/version collision bugs + four
   P2-10..13 correctness fixes, all in `migrate_v1_to_v2.py`.
3. **PR-2 (append-only enforcement)** — validator-side P0-1(b) + unclosed-fence
   + broken-cross-link promotion.

PRs 3–5 (starter.md framework text) are the biggest editorial lift; keep doing
code fixes first.

### Blockers

- None.

## Session 2026-06-22 (session 29)

### What was done

Started the **Opus review fix initiative** — a comprehensive audit (findings
in `tmp/review-fix-list.md`) surfaced 13 PR batches. This session:

1. **Created the plan** — added "Opus review fix initiative" section to
   `status/plan.md` with all 13 PR batches, each item cross-referenced to
   the review finding code (P0-N, P1-N, etc.).
2. **Shipped PR-9: Script/test hygiene** (all 6 items):
   - **P3-9** — deleted broken `test-all` Makefile target (used
     `--run-slow`, an unregistered pytest option under `--strict-markers`);
     removed the unused `slow`/`integration` marker declarations from
     `pyproject.toml`.
   - **P3-10** — `tests/test_turn1.py` `_FM` fixture: changed hard-coded
     `research_buddy_version: "1.13.0"` to `"1.0.0"` so it won't rot.
   - **P3-11** — `.pre-commit-config.yaml` version-sync hook: added
     `src/research_buddy/starter\.md` to the `files:` trigger pattern.
   - **P2-18** — `scripts/sync_version.py`: all four updaters now use
     `re.subn` and raise `ValueError` on count==0 (previously three of
     four silently no-oped and printed "Updated"). README pattern widened
     from `v\d+\.\d+\.\d+` to `v\S+` to match the checker's pattern.
   - **P2-7** — deleted dead `STARTER_NULLABLE` constant from
     `validator_md.py` (7 lines, never referenced anywhere).
   - **P3-12** — `CLAUDE.md`: softened "TDD ceremony enforced" →
     "class-grouped, TDD by convention".

Gates: `make lint` clean, `make test-cov` **547 passed** (↑4), **91.43%**
coverage.

### Next steps

Pick the next PR batch from `status/plan.md`. Recommended order:
1. **PR-10 (File-I/O helpers)** — `read_text_or_error` + `atomic_write`
   helpers. Low-risk, self-contained, unblocks PR-8 (build safety).
2. **PR-6 (clean_md correctness)** — `collect_framework_targets` fence-
   awareness + EOF content-loss fix. Small, focused.
3. **PR-7 (migrate hardening)** — three P0-4 ID/version collision bugs plus
   four P2-10..13 correctness fixes. All in `migrate_v1_to_v2.py`.
4. **PR-2 (append-only enforcement)** — the validator-side P0-1(b) + unclosed-
   fence + broken-cross-link promotion. High-value correctness work.

PRs 3–5 (starter.md framework text) are the biggest editorial lift; do code
fixes first so the framework changes ship on a solid base.

### Blockers

None.

## Session 2026-06-08 (session 28)

### What was done

Released **1.13.0** (MINOR — additive). Driven by a real research session
(pasted by the user) where the agent skipped the second-opinion brief and
mis-diagnosed the cause as "the framework is missing from the file".

- **Root cause found (and it corrects the agent's own diagnosis).** The
  framework is intact in `starter.md`. The agent had almost certainly been
  given a **clean view** (`*_v*.md`), not the source (`*_v*-source.md`):
  `clean`/`build_md` strip the framework block but the AGENT-STOP **preamble**
  sits *before* `<!-- @anchor: title -->`, outside both the framework and title
  regions, so it survived — and `unwrap_framework_links` rewrote its
  `[Framework (Core)](#framework-core)` links into dangling plain text. Result:
  an operating manual pointing at sections that no longer exist. Exact match
  for the transcript symptom.
- **Fix 1 — `clean` strips the preamble.** New `clean_md.strip_agent_preamble`
  removes it and inserts a one-line self-identifying note pointing back at the
  `*-source.md`, so a mis-uploaded clean view self-corrects. (HTML build never
  carried the preamble — it's dropped with everything before the first H2.)
- **Fix 2 — hardened starter preamble.** Brief gate is now the first imperative
  AND the closing line (primacy + recency); names concrete tool families;
  inlines a fill-in brief skeleton (markers referenced as backticked tokens to
  avoid breaking the enclosing HTML comment). Propagates to existing docs via
  `upgrade --apply`. Updated `test_upgrade_md.py` landmark
  (`DO NOT CALL ANY TOOL` → `THE BRIEF GATE`).
- **Fix 3 — `research-buddy turn1 <file>`.** New read-only helper (`turn1.py` +
  `commands/turn1.py`, wired into `cli.py` + `main.py`) prints the brief
  skeleton pre-filled from frontmatter + top queue row; reuses `bump`'s
  comment-aware queue parser; body mirrors the canonical brief template. Also
  surfaced in the preamble + brief-template section.
- **Translation — `localize.py`.** HTML build displays framework section
  headings in `language.code` (ships Spanish) while keeping English slugs/ids
  (verified: `data-tab="open-research-queue"` + visible "Cola de investigación"
  + `<html lang="es">`); `section_labels` frontmatter overrides/extends.
  Display-only — clean MD keeps English headings (a heading's slug *is* its
  text there). README "Multi-language support" rewritten.
- **Finding: `ui_strings` is dead config in v2.** No renderer reads it; v2 has
  no fixed status column. Documented as a v1 carryover; not wired. The agent
  writes localized status text / `rb-ok`/`rb-flag` chips directly.

Gates green: `make lint`, `make test-cov` (543 passed, 91.39%),
`make check-examples-sync`. `make version-sync` + `make regen-examples` ran for
the 1.13.0 bump.

### Next steps

- Empirical: watch whether the hardened preamble + `turn1` + clean-view fix
  actually stop the brief skip downstream (agent compliance is empirical, per
  sessions 16/17).
- Backlog unchanged (framework token overhead highest-leverage; the two
  file-I/O cleanups are low-risk warm-ups). Could add more `localize.py`
  languages on demand, or wire `section_labels` into the starter frontmatter as
  a documented optional field if discoverability matters.

### Blockers

- None.

## Session 2026-06-05 (session 27)

### What was done

- **Fixed four `migrate-v1-to-v2` bugs** surfaced migrating a mature v1.14 JSON
  (~rb 1.4.0 schema, 31 topics) on rb 1.12.0. One crash + three silent-data-loss
  bugs. All in `src/research_buddy/migrate_v1_to_v2.py`:
  1. **[crash] `meta.language` as a string** killed `build_frontmatter`
     (`(meta.get("language") or {}).get("code")` assumed an object). New
     `resolve_language()` coerces `str → {code, label}`, mapping the label via
     `build._LANGUAGE_NAME_TO_CODE`, falling back to `"und"` for unknown labels.
  2. **[data loss] project spec read only from `agent_guidelines.project_specific`**
     — in mature docs that block is the untouched `[FILL]` template; the real
     spec lives at top-level `doc["project_specific"]`. New `resolve_project_spec()`
     does a per-field merge (filled agent_guidelines value wins, else recover the
     top-level one) via `_is_filled` (recursive, treats `[FILL]`/empty as unfilled)
     + `_normalize_top_level_ps` (key aliases: `deliverable→deliverable_type`,
     `timeline→timing`, `source_tiers.tier_3→discovery`, `never_tier→never`).
     Used by both `build_frontmatter` and `migrate`.
  3. **[data loss] `tabs[overview]` dropped unconditionally.** New
     `build_overview_tab()` renders an Overview H2 (placed right after Project
     Specification) carrying substantive sections as H3s; only nav sections
     (`OVERVIEW_NAV_SECTIONS`: Quick Links / How to Navigate / …) are dropped.
     Returns "" for a pure-nav tab so `migrate` omits it. `build_domain_tab` grew
     a `skip_sections` param.
  4. **[structural] queue done-detection keyed only on the ✦ glyph.** A row whose
     status read "Researched v1.3" (no glyph) stayed in the Open Research Queue
     *and* the Research Tracker (violating "no ID in both"). New `_row_done`
     also matches `/researched/i` text and any row whose Q-NNN is already in the
     tracker (`_tracker_ids`). `_strip_done_rows_from_queue` + `build_open_research_queue`
     thread the tracker IDs through.
- **Regression tests** (`tests/test_migrate_v1_to_v2.py`, +22): `TestLanguageCoercion`,
  `TestProjectSpecResolution`, `TestOverviewTabSurvival`, `TestQueueDoneDetection`,
  and `TestSessionNotesCatchAll` (guards the monolithic `Session Notes` catch-all
  that already works — flagged "not a bug, add a guard"). Suite 483 → **505 passed**,
  coverage **91.16%**.
- **Released 1.12.1** (PATCH — bug fix). `make version-sync` + `make regen-examples`
  (starter.md embeds the version). Gates green: `make lint`, `make check-examples-sync`,
  `make test-cov`. End-to-end smoke on a synthetic repro doc confirmed all four
  fixes; the only `validate` warning is the expected filename-mismatch from a custom
  `-o` name.

### Next steps

- Numbered roadmap (1–14) remains complete; backlog ("Future improvements") is the
  next pickup — framework-token-overhead is highest leverage but design-heavy; the
  two file-I/O cleanups (`read_text_or_error`, `atomic_write`) are low-risk warm-ups.

### Blockers

- None.

## Session 2026-06-01 (session 26)

### What was done

- **Released v1.11.0** (MINOR bump from 1.10.0). Covers the three feature
  PRs that shipped against 1.10.0 without a bump: `bump` (#95), `locate` +
  `diff-summary` (#96), and the starter marker-hygiene fix. Backward-
  compatible (new CLI subcommands only), so MINOR.
- Workflow: edited `pyproject.toml`, ran `make version-sync` (propagated to
  `__init__.py`, `starter.json`, `starter.md`, `README.md`) + `make
  regen-examples` (both committed HTML examples embed `research_buddy_version`).
  Gates green: `make lint` (incl. `check-version-sync`), `check-examples-sync`,
  `test-cov` 452 passed / 89.8%.

### Next steps

- Numbered roadmap (1–14) is complete; remaining work is the "Future
  improvements" backlog (framework-token-overhead is highest leverage but
  design-heavy; the two file-I/O cleanups are low-risk warm-ups).

### Blockers

- None.

## Session 2026-06-01 (session 25)

### What was done

Shipped the remaining three agent-efficiency helpers (#12–#14) in one PR:

- **#13 `locate <source.md> <anchor>`** (`commands/locate.py`) — prints the
  *live* `<!-- @end: <anchor> -->` marker line + context. Matches **full-line**
  markers outside fenced blocks (reuses `validator_md._line_in_fence`), so
  inline prose mentions and fenced template examples never collide. Accepts
  `rules`, `@end: rules`, or the full comment form. This is the real fix for
  the v1.12 "found multiple times" grep pain — fence-and-full-line-aware where
  plain grep isn't.
- **#14 `diff-summary <old.md> <new.md>`** (`diff_summary.py` +
  `commands/diff_summary.py`) — emits the mechanical part of the Turn-2
  `@summary` block (version bump, queue→tracker moves, rules added/revised,
  DAs/sessions added, append-only PASS/FAIL), narrative left as
  `{{placeholder}}`. Exit 1 on append-only violation. Rule-revision detection
  uses a local `_entry_blocks` (block-text compare), since
  `_collect_entry_ids` only returns IDs.
- **#12 starter marker hygiene** (`starter.md` + `test_starter_hygiene.py`) —
  reworded the 7 prose lines that embedded a literal `<!-- @end: X -->` to
  "this section's closing `@end` marker", so each live `@end: X` is now the
  unique occurrence of its ID. Invariant test enforces it. **Deviation from
  the plan, intentional:** the fix is *rewording*, not *fencing* — inline
  mentions can't be fenced cleanly and fencing wouldn't help a plain grep
  anyway. No `upgrade_md` change needed: the 4 framework-block lines propagate
  via the existing wholesale framework re-sync; the 3 user-section intros
  reach new projects only (acceptable — `locate` covers existing ones).

### Verification

- New tests: `test_locate.py`, `test_diff_summary.py`, `test_starter_hygiene.py`.
  `make test-cov` 434 → **452 passed, 89.8%**; `make lint` clean;
  `make check-examples-sync` green after `make regen-md-example` (starter.md
  edit required the v2 example rebuild). End-to-end CLI smoke for all three.
- Docs: CLAUDE.md layout + non-obvious notes; plan.md #12/#13/#14 checked off;
  new backlog item "consistent temp-file cleanup across atomic writers" (from
  the #95 review) added next to the encoding-handling item.

### Next steps

1. **The numbered roadmap (steps 1–14) is now fully shipped.** Next work comes
   from "Future improvements" — these are design-heavy / outward-facing and
   were explicitly flagged as needing a decision before execution, not blind
   pickup. Highest-leverage: **framework token overhead** (the ~674-line
   framework rides every upload, every session). Needs a real design pass —
   any split must not regress the no-tool-call gate or session-state detection.
2. Two low-risk "centralize a file-I/O concern" cleanups are ready when
   wanted: the **encoding helper** (`read_text_or_error`) and the **atomic-write
   helper** (`atomic_write`). Good warm-up tasks; could pair into one PR.

### Blockers

- None.

## Session 2026-06-01 (session 24)

### What was done

- **Roadmap step #11 shipped — `research-buddy bump <source.md> <Q-NNN>`.**
  The biggest agent-efficiency win: one command does all the mechanical
  Turn-2 edits so the agent only writes prose. Two new modules:
  - `bump.py` — pure text transforms (no I/O): `next_minor_version`
    (1.0→1.1, drops a trailing PATCH), `pop_queue_row` (comment-aware so
    the queue's example rows inside `<!-- -->` are never matched),
    `append_tracker_row`, the session/changelog/references block builders,
    and `bump_md_text` which orchestrates all five edits + frontmatter
    version/date (reuses `init._set_frontmatter_scalar`).
  - `commands/bump.py` — `cmd_bump`: extension/starter/required-field
    guards, dry-run by default, `--apply` writes a NEW
    `{file_name}_v{next}-source.md` atomically, `--force` to overwrite,
    `--no-validate` to skip. Wired into `cli.py` (parser + dispatch) and
    re-exported from `main.py`.
- **Design choice — bump emits a new versioned file, not in-place.**
  Matches the agent workflow (each version is its own file) and lets the
  apply path validate the output with the **input as `--prior`**, so
  anchor-preservation + append-only invariants are checked mechanically.
  The headline test asserts the bumped file is `validate_md`-clean against
  its prior.
- **Plan text was stale post-#9.** #11 said "CLI handler in `main.py`";
  after the split, handlers live in `commands/*`. Noted in plan.md.
- **Verified.** `tests/test_bump.py` (15 tests: version math, table
  helpers, dry-run/apply/guards/dispatch). `make test-cov` 419 → **434
  passed, 89.6%**; `make lint` clean; end-to-end CLI smoke (lowercase
  `q-001` normalized, 1.3→1.4) green. Docs: CLAUDE.md layout + a bump
  non-obvious note; plan.md #11 checked off.

### Next steps

1. **#12 Starter marker hygiene** — fence the scaffolding examples in
   `starter.md` so agent greps stop false-matching; ship an `upgrade_md`
   pass. Cheap, unblocks every future agent grep.
2. **#13 `locate`** / **#14 `diff-summary`** — remaining agent-efficiency
   helpers; smaller leverage, can follow #12.
3. **Encoding-handling backlog** (Future improvements) — extend
   `UnicodeDecodeError` guards to the `read_text` sites.
4. **Deferred design items** still await a decision (framework token
   overhead first).

### Blockers

- None.

## Session 2026-06-01 (session 23)

### What was done

- **Roadmap step #9 shipped — split `main.py` (1007 → 66 lines).**
  Extracted the CLI into:
  - `cli.py` — `build_parser()` (all argparse wiring) + `main()`
    (argcomplete + dispatch table).
  - `commands/` package, one module per subcommand: `_shared.py`
    (`_resolve_source` + starter-template loaders), `build.py`
    (`perform_build`, `perform_build_md`, `cmd_build` — 336 lines, the
    biggest), `validate.py`, `clean.py`, `migrate.py`, `init.py`
    (incl. `_set_frontmatter_scalar`, `_init_v1/_v2`), `upgrade.py`
    (incl. `_upgrade_md_file`).
  - `main.py` is now a **thin re-export façade**: it exposes `main`
    for the `research_buddy.main:main` console script and re-exports
    every command handler + helper (via `__all__`) so existing
    imports `from research_buddy.main import cmd_build` keep resolving.
- **Behaviour-preserving.** Function bodies copied verbatim (the only
  cosmetic change: `\uXXXX` escapes → the literal `…`/`⚠`/`✔` glyphs,
  identical output bytes). All 411 tests pass unchanged except the 3
  `cmd_upgrade` monkeypatch targets in `test_upgrade.py`, which moved
  from `research_buddy.main.{validate,_load_starter_template}` to
  `research_buddy.commands.upgrade.*` (a patched name must match where
  the function does its global lookup — documented in CLAUDE.md
  "Non-obvious things").
- **Verified.** `make test-cov` 411 passed / 89.3%; `make lint`
  (ruff + format + mypy, now 23 source files) clean; `make
  check-examples-sync` green; smoke-tested the console entry point,
  a real `build`, and `python -m research_buddy.main`.
- **Docs.** CLAUDE.md layout + a new façade/monkeypatch note;
  plan.md #9 checked off.
- **Gemini review fixes → split into separate PR #93 (final call).**
  Initially folded into #92, but the user then chose to keep #92 a
  pure, behaviour-preserving refactor; the fixes were peeled back out
  (force-pushed #92 to the pure split) and moved to a stacked follow-up
  **#93** (`fix/cli-json-robustness`). Both PRs are now **merged**.
  The fixes (all pre-existing-code, with tests):
  - `build --all` discovery/sort regex widened from `_vMAJOR.MINOR`
    to `_vMAJOR.MINOR(.PATCH…)` — three-component versions
    (`_v1.0.3.json`) were silently skipped despite `perform_build`'s
    fallback supporting them. `_version_key` now returns
    `tuple[int, ...]` (shorter-prefix sorts first, so 1.0 < 1.0.3).
  - `json.JSONDecodeError` now caught in `perform_build`,
    `cmd_build --validate-only`, `cmd_validate`, and `cmd_upgrade`
    (previously only `cmd_migrate` guarded it) — malformed input
    prints a clean error + exit code instead of a traceback.
  - A second Gemini round on #93 flagged that `json.load` over a file
    raises `UnicodeDecodeError` (a sibling of `JSONDecodeError` under
    `ValueError`, **not** a subclass) on invalid UTF-8 bytes, so the
    new guards still let it traceback. Caught both across
    `build`/`validate`/`upgrade`/**`migrate`** (migrate had the same
    latent crash) — now reports "is not valid JSON or has invalid
    encoding". Scoped to JSON reads only; the `read_text` sites
    (v2 MD build, theme/starter loads) are a backlog item (see plan.md).
  - New `tests/test_main_coverage.py` classes
    `TestMalformedJsonHandling` (4) + `TestBuildAllVersionDiscovery`
    (1) + `TestInvalidEncodingHandling` (3); suite 411 → 419,
    coverage 89.4%.
  - **Rebase note:** #92 squash-merged, so #93 (based on the old
    refactor commit) showed conflicts; `git rebase --onto origin/main
    0b5ba3b` dropped the redundant refactor commit and replayed only
    the two fix commits cleanly.

### Next steps

1. **#11–#14 agent-efficiency helpers** are now unblocked and should
   land as new `commands/*` modules (e.g. `commands/bump.py`) wired
   into `cli.py`, not as growth in `main.py`. #11 (`bump`) is the
   biggest single win.
2. **Deferred design items** still await a decision (framework token
   overhead first — highest leverage).

### Blockers

- None.

## Session 2026-06-01 (session 22)

### What was done

- **Project-review pass + roadmap reshape.** User asked for an
  improvement review, then decided to **exclude all further mutmut
  work** and execute the rest. Shipped the safe, high-value guard
  rails this session; deferred the design-heavy items to a decision.

- **Mutmut cleanup discontinued (#7c–#7j).** Marked discontinued in
  `plan.md`. Rationale recorded there: the baseline (#7) + `validator`
  (#7a, PR #89) + `table_layout` (#7b, PR #90) earned their keep, but
  the remaining ~3,700 survivors across eight modules (tail: `build`
  630, `main` 849, `migrate_v1_to_v2` 1198) is a low-ROI treadmill
  yielding brittle exact-string/boundary tests. mutmut config stays in
  `pyproject.toml` for ad-hoc use; we just stop grinding to zero.

- **#8 — coverage gate in CI (shipped).** New `make test-cov` runs
  pytest with `--cov --cov-report=term-missing --cov-fail-under=85`;
  CI's test job calls it instead of bare `pytest`. `[tool.coverage.run]
  source = ["research_buddy"]` added so a bare `--cov` measures the
  package only. Kept the gate OUT of global `addopts` so `make test`
  stays fast/ungated locally and mutmut's pytest runs are unaffected.
  Current total coverage **89.1%**, so the 85% floor has headroom.

- **#8a — `starter-example/` sync guard (shipped).** New
  `scripts/check_examples_sync.py` (mirrors `check_version_sync.py`
  style) + `make check-examples-sync`, wired into the CI **lint** job
  (3.12 only, to avoid cross-version byte-diff flakiness). It
  regenerates both examples to a temp dir and byte-compares against the
  committed copies. **It immediately caught real drift**: the committed
  examples were last regenerated at 1.8.0 (session 15) and never
  rebuilt through the 1.9/1.10 bumps. Only meaningful diff was the
  footer `v1.8.0 → v1.10.0` (the 72KB raw diff is just the inlined
  base64 logo sharing that physical line). Regenerated both via
  `make regen-examples` and committed.

- **`main.py` split (#9) — line count corrected.** Plan said "421
  lines"; it is now **1007**. Updated #9 and noted it must land BEFORE
  the #11–#14 agent-efficiency subcommands (which all add code *into*
  `main.py`). Not executed this session — it's the next real refactor.

- **Design-heavy items captured in `plan.md` "Future improvements"**
  (need a decision, not blind execution): framework token overhead
  (highest leverage; ~674-line framework rides every session), v2
  escaping/trust model (`autoescape=False` + LLM-authored source), v1
  sunset with a dated target (dual-path surface area), user-facing
  CHANGELOG.

- **Docs.** CLAUDE.md commands table + layout updated for `test-cov`,
  `check-examples-sync`, and `check_examples_sync.py`.

### Next steps

1. Open the PR for this branch (`claude/friendly-sagan-TNkRY`).
2. **#9 — split `main.py` (1007 lines).** Extract `cli.py` +
   `commands/`; keep `main.py` a thin shim. Biggest reviewable refactor
   in the queue; do it before #11–#14.
3. **Decide on the deferred design items** (framework overhead first —
   it's the highest-leverage and affects every session).

### Blockers

- None.

## Session 2026-05-18 (session 21)

### What was done

- **Roadmap step #7b shipped — `table_layout` mutation survivors.**
  Re-ran `mutmut run "research_buddy.table_layout.*"` against the
  baseline (the cache was reset after the validator-specific re-run in
  session #20). 219 mutants total, 49 survivors confirmed. Classified
  them:
  - **10 EQUIVALENT** (accepted, no test changes):
    - `_layout_from_profiles#52` (`sum(clamped) or 1.0` → `or 2.0`).
      `clamped` always has ≥1 element (line-138 guard) and each value
      is `≥ MIN_PCT = 12`, so `sum(clamped) ≥ 12 > 0` is truthy and
      the `or` fallback is unreachable.
    - `_layout_from_profiles#75` (`reverse=diff > 0` → `reverse=diff
      >= 0`) and `#79` (`step = 1 if diff > 0` → `if diff >= 0`).
      Both sit inside `if diff != 0:` so `diff` is non-zero when the
      mutated expressions evaluate, making `> 0` and `>= 0`
      observationally identical.
    - `compute_layouts#26/27/28/29/30/31/32` — all seven mutate the
      `is not None` fallback `TableLayout({}, (), False)` in the
      return comprehension. Every index in `layouts` is assigned by
      either the singleton or group branch (each `i ∈ range(len(
      tables))` lands in exactly one signature group via
      `setdefault`), so the fallback is dead code; the syntactic
      variants (`None` substitutions, dropped positional args,
      `False → True`) are unreachable under normal flow.
  - **39 REAL_GAP**: killed by 20 new tests in
    `tests/test_table_layout_mutations.py` organised into 9 classes:
    - `TestProfileColumnPercentiles` — exact `p50` / `p90`
      indexing, kills `profile_column#22/31/33`.
    - `TestProfileColumnSpacesCount` — three cases at the
      `n_with_spaces * 2 >= n` boundary (1/4, 1/3, 2/4), kills
      `#39/44/45`.
    - `TestProfileColumnTokenBoundary` — `<=` inclusivity on both
      `p90` and `max_len`, kills `#50/51`.
    - `TestProfileTableRagged` — ragged-row padding (kills both
      `profile_table#7` via `IndexError` and `#8` via wrong `p90`).
    - `TestAggregateGroup` — one assertion per `_aggregate` field,
      kills `#6/8/9/10`.
    - `TestLayoutFromProfilesEarlyReturns` — single-profile and
      all-token return paths, kills `#3/22/24`.
    - `TestLayoutFromProfilesWeights` — `max(1, p90)` floor and the
      raw/scaled multiplicative constants, kills `#33/37/38/39/55`
      via a 2-col case (`p90=[2, 3]`) that clamps one column to
      `MAX_PCT=50`.
    - `TestLayoutFromProfilesRedistribution` — positive-diff case
      (`p90=[3, 6, 10]`, `diff=+1`) kills `#56/63/64/67/70/71/74/76
      /78/80/85/86`; negative-diff case (`p90=[3, 5, 12]`,
      `diff=-1`) kills `#81/82`.
    - `TestComputeLayoutsGrouping` — two-table cases that pin
      specific col_widths, kills `compute_layouts#19/22/24` (the
      existing `test_grouped_tables_share_one_layout` only asserted
      `layouts[0] == layouts[1]`, which the `None`-fallback mutants
      preserve).

- **mutmut re-verification.** After landing the tests, re-ran
  `mutmut run "research_buddy.table_layout.*"`. Result: 39 killed,
  10 still survive (the accepted equivalents). Per-module table_layout
  survivor count: **49 → 10** (80% kill rate on the survivor cohort;
  100% on real gaps).

- **Operational note.** mutmut 3.x accepts a wildcard filter
  `module.*` for the run command — confirmed working with
  `mutmut run "research_buddy.table_layout.*"`. Passing the bare
  module name (`research_buddy.table_layout`) fails with
  `AssertionError: Filtered for specific mutants, but nothing
  matches`. Future module-cleanup steps should use the wildcard form.

- **Gemini review on PR #89.** `gemini-code-assist` flagged two
  duplicated literals in `tests/test_validator_mutations.py` — the
  inline meta dict at the deep-path test was identical to
  `_BASE_META`, and the inline tabs list at the missing-rb-version
  test was identical to `_BASE_TABS`. Both replaced with the shared
  constants; pure dedup (semantics unchanged). Landed as
  `bd09029` on the `chore/mutmut-step-7a-validator` branch before
  merge; PR #89 merged as `a947742`.

### Next steps

1. Ship session #21 as the step #7b PR — `tests/test_table_layout_mutations.py`
   + `status/plan.md` (check off #7b) + `status/next-session.md`.
2. **Step #7c — `clean_md` survivors** (52 mutants). Same playbook:
   `uv run mutmut run "research_buddy.clean_md.*"`, run the report,
   classify, write targeted tests, re-run.
3. **Step #8 — coverage threshold in CI.** Still queued. Wire
   `--cov-fail-under=85` and `pytest-cov` into CI test job.

### Blockers

- None.

## Session 2026-05-18 (session 20)

### What was done

- **Roadmap step #7a shipped — validator mutation survivors.** Ran
  `.claude/skills/mutmut-report/analyze_mutmut.py --module validator`
  against the baseline survivor set (46 mutants). Classified them:
  - **6 EQUIVALENT** (accepted, no test changes):
    - `_load_schema#9/10/11/15` — encoding variants (`utf-8`/None/
      omitted/`UTF-8`). `schema.json` is pure ASCII, so all four
      decodings produce identical bytes; testing the difference would
      require corrupting the bundled schema with non-ASCII content.
    - `_walk_references#27/45` — boundary swap `> 1` → `>= 1` on the
      version/date count check. With exactly one item,
      `sorted([x], reverse=True) == [x]`, so no warning fires either
      way — observationally identical.
  - **40 REAL_GAP**: covered by 19 new tests in a dedicated
    `tests/test_validator_mutations.py` organised into 8 buckets:
    - `TestParseDateInternals` — direct assertions on
      `_parse_date("2026-04-01") == (2026, 4, 1)`,
      `_parse_date("2026-04-01-rev5") == (2026, 4, 1)` (forces
      `re.match` short-circuit, distinguishes the numeric-fallback
      branch), and `_parse_date("April 2026") == (2026, 4, 0)`
      (pins the trailing-0 day).
    - `TestParseSemverInternals` — pin zero-fill on missing minor
      (`"1" → (1,0,0)`) and missing patch (`"1.0" → (1,0,0)`).
    - `TestVersionCompatibilityExactMessage` — assert the full
      "Unrecognized version format" warning verbatim (kills the
      XX-wrap + casing mutants on the hint sentence).
    - `TestSchemaErrorPathFormatting` — assert the bracketed prefix
      "[(root)]" for root-level errors and "[tabs.0]" for deep errors;
      explicitly reject the mutant variants `[None]`, `[(ROOT)]`,
      `[XX(root)XX]`, `[tabsXX.XX0]`, `[None.None]`.
    - `TestSchemaErrorSortOrder` — feed a doc where `iter_errors`
      natural order would be `[meta, changelog]` (schema declaration
      order) but path-sort puts `[changelog]` first. The mutant that
      replaces the sort key with the constant `str(None)` collapses
      to a stable no-op and preserves natural order, so asserting
      `changelog_idx < meta_idx` kills it.
    - `TestRbVersionMissingExactMessage` — pin the leading and
      trailing static substrings of the missing-rb-version warning
      (TOOL_VERSION is interpolated in the middle).
    - `TestLanguageExactMessages` — assert both `[meta.language]`
      warnings verbatim, plus an absence-of-warning test for the
      missing-language case (kills the `is not None` → `is None`
      mutant).
    - `TestEmptyKeyDefaults` — exercise `_validate_references` /
      `_walk_references` with tabs missing `sections`, sections
      missing `blocks`, and references blocks missing `items`. The
      mutants that change the default `{}`/`[]` to `None` would
      crash on `None.items()` / `for x in None`; the original
      walks cleanly.
    - `TestSubsectionsRecursion` — nest a subsection containing
      a misordered references block. Original recurses into
      `sec.get("subsections", {})` and emits the warning; mutants
      that swap the key name (`None`, `"XXsubsectionsXX"`,
      `"SUBSECTIONS"`) or pass `warnings=None` either skip the
      recursion or crash inside it.

- **mutmut re-verification.** After landing the new tests, re-ran
  `mutmut run` against the 46 validator survivor IDs. Result: 40 now
  killed, 6 still survive (the accepted equivalents). Per-module
  validator survivor count: **46 → 6** (87% kill rate on the survivor
  cohort).

- **Operational note.** `mutmut run <mutant_id>` reset the entire
  cache state to "not checked" on the first invocation when the
  argument list was passed as a single newline-separated string
  (shell quoting trap). Re-running the full validator mutant set
  (247 mutants) takes ~7 minutes. Future runs: pass mutant IDs as
  separate shell tokens, e.g. `mutmut run $(cat file.txt | xargs)`.

### Next steps

1. Ship session #20 as the step #7a PR — `tests/test_validator_mutations.py`
   + `status/plan.md` (check off #7a) + `status/next-session.md`.
2. **Step #7b — `table_layout` survivors** (49 mutants). Same
   playbook: run the report, classify, write targeted tests, re-run.
3. **Step #8 — coverage threshold in CI.** Still queued. Wire
   `--cov-fail-under=85` and `pytest-cov` into CI test job.

### Blockers

- None.

## Session 2026-05-18 (session 19)

### What was done

- **Roadmap step #7 shipped — mutation-testing baseline.** Set up
  `mutmut` against `src/research_buddy/` and captured the baseline
  numbers. Four pieces:
  1. **Install.** Added `mutmut>=3.0.0` to
     `[project.optional-dependencies].dev` in `pyproject.toml`.
     mutmut 3.5.0 resolves via `uv sync --extra dev`.
  2. **Config.** New `[tool.mutmut]` section pointing
     `paths_to_mutate = ["src/research_buddy/"]`,
     `tests_dir = ["tests/"]`, `do_not_mutate =
     ["src/research_buddy/__init__.py"]` (the file holds only
     `__version__`, already guarded by `test_version_sync.py`).
  3. **Sandbox compatibility.** mutmut runs the test suite from a
     `mutants/` copy of the repo that contains `pyproject.toml`,
     `src/`, `tests/` but **not** `README.md`. That broke
     `test_readme_matches_pyproject` which reads
     `REPO_ROOT/README.md` to assert version sync. Fix: module-level
     `pytestmark = pytest.mark.skipif(not (REPO_ROOT /
     "README.md").exists(), ...)` on the whole `test_version_sync.py`
     file — the entire file is a repo-state guardrail (none of the
     tests exercise mutated product code), so skipping it in the
     mutmut sandbox is correct. Real-CI / local `make test` still
     run all 5 assertions because README.md is present there.
  4. **Gitignore.** `mutants/` added to `.gitignore` so the ~676 KB
     mutant workspace doesn't surface in `git status`.

- **Baseline numbers (8964 total mutants):**
  - Killed: **4643** (51.8%)
  - Survived: **3792** (42.3%)
  - No-tests: **511** (5.7%)
  - Timeout: **18** (0.2%)
  - Stats live in `mutants/mutmut-cicd-stats.json` (also gitignored;
    regenerate with `uv run mutmut export-cicd-stats`).

- **Per-module survivor distribution** (sorted ascending, drives
  the #7a–#7j cleanup order in `plan.md`):
  ```
  validator           46
  table_layout        49
  clean_md            52
  upgrade             88
  upgrade_md         188
  validator_md       308
  build_md           384
  build              630
  main               849
  migrate_v1_to_v2  1198
  ```

- **`plan.md` reshape.** Step #7 marked shipped. Inserted #7a–#7j
  (one per module) ordered by survivor count ascending — smallest
  first so the muscle is built up on simpler modules before
  tackling `migrate_v1_to_v2`. Decided in-conversation that bundling
  the survivor fixes into the baseline PR would balloon scope (per-
  module fixes look like ≥100 LOC of new test cases each); shipping
  the baseline alone keeps the PR reviewable.

### Next steps

1. Ship session #19 as the step #7 PR — pyproject + .gitignore +
   tests/test_version_sync.py + plan.md + next-session.md. Single
   commit on `chore/mutmut-step-7`.
2. **Step #7a — validator survivors.** Run
   `.claude/skills/mutmut-report/analyze_mutmut.py --module validator
   --max 60`, classify the 46 survivors, fix real gaps. Most look
   like: `encoding="utf-8"` → `None`/omitted (likely equivalent,
   reading our own JSON); `_parse_date` regex mutations (real gap —
   tests don't assert parsed year/month/day values); `.get(key, {})`
   → `.get(key, None)` (real gap — missing-key path not exercised);
   `len(x) > 1` → `>= 1` (real gap — boundary case).
3. **Step #8 — coverage threshold in CI.** Still queued. Wire
   `--cov-fail-under=85` and `pytest-cov` into CI test job.
4. **Note: mutmut-report skill has a parser bug for mutmut 3.x.**
   It uses `re.match(r"x_(.+?)__mutmut_(\d+)", ...)` but mutmut 3.x
   names class-method mutants `xǁClassǁmethod__mutmut_N` (Unicode
   `ǁ`). The skill mis-groups these as separate single-survivor
   "modules" and lists them above the real modules in the
   "smallest first" sort. Workaround: it still classifies free-
   function mutants correctly, which covers most survivors. Fix
   later or skip if the work is otherwise tractable.

### Blockers

- None.

## Session 2026-05-18 (session 18)

### What was done

- **Roadmap step #6 shipped — raise coverage on `main.py` and
  `validator.py` to ≥85%.** Total project coverage 82% → 89%.
  Two pieces:
  1. **`validator.py` 63% → 100%.** Removed a closed dead-code
     subgraph (`build_changelog_nav`, `_ensure_entry_id`,
     `_collect_all_ids`, `_collect_block_ids`, `_walk_section_ids`
     — ~75 lines, plus the now-unneeded `slugify` import). Added
     in 2d11252 ("enhance build engine") but never referenced by
     `build.py`, `build_md.py`, or any caller — the sidebar nav
     was reimplemented inline in both renderers. Testing
     load-bearing-untested code would have locked it in with no
     caller. Added three small targeted tests for `_parse_date`
     numeric fallback, `_parse_semver` non-string rejection, and
     the malformed-tool-version silent branch in
     `_check_version_compatibility`.
  2. **`main.py` 61% → 88%.** New `tests/test_main_coverage.py`
     with 41 tests across seven classes covering the
     previously-untested branches: `main()` argparse + dispatch
     via `sys.argv` patching (catching `SystemExit`); the entire
     `cmd_migrate`, `cmd_clean`, and `cmd_validate` MD path; the
     `_upgrade_md_file` helper; `cmd_build` error branches
     (`.json`/`.md` mixing, `--watch` + `.md`, `--pdf` + `.md`,
     `--watch` + multiple paths, `--all` empty directory,
     `--validate-only` with invalid doc); `perform_build_md`
     theme cascade (explicit `--theme` flag, frontmatter
     `theme_css` field, `--no-versioning`); `_set_frontmatter_scalar`
     edge cases (no leading `---`, no closing `---`, missing key);
     and `perform_build`'s `--pdf` success + weasyprint-missing
     paths.
- Pre-work review surfaced four queued agent-efficiency helpers
  (steps #11–#14 in `plan.md`) derived from a real research-buddy
  v1.11→v1.12 session transcript: `bump <id>` scaffold, starter
  marker hygiene, `locate <anchor>`, `diff-summary`. Ordered after
  #6 per the original roadmap.

### Next steps

1. Ship session #18 as a PR — single bundled commit covers the
   dead-code removal + new test file.
2. **Roadmap step #7 — mutation-testing baseline.** Install
   `mutmut`, configure against `src/research_buddy/`, capture
   baseline survivor count using the `.claude/skills/mutmut-report/`
   skill to group survivors into real-gap / equivalent / untestable.
3. **Roadmap step #8 — coverage threshold in CI.** Add
   `--cov-fail-under=85` to pytest and wire `pytest-cov` into the
   CI test job.
4. After steps #6–#10 close, start the agent-efficiency helpers
   (#11 `bump` is the biggest single win).

### Blockers

- None.

## Session 2026-05-14 (session 17)

### What was done

- **Operating-manual hardening — 1.9.1 → 1.10.0 (single PR).** Driven
  by a postmortem from a downstream agent that called
  `launch_extended_search_task` before emitting the second-opinion
  brief. Root cause: the agent's first read window stopped around
  line 47 and the load-bearing "read Framework Core first"
  reminder was below that line; the surrounding chat-environment
  tool mandate ("USE ONLY THE LAUNCH EXTENDED SEARCH TOOL") won
  the tug-of-war against the in-file protocol. Five things shipped
  together:
  1. **Compacted operating manual** (HTML comment between
     frontmatter and the first `@anchor`). Now ≤12 lines, all
     critical content above line 41. Order: STOP banner + Continue
     interpretation → DO NOT CALL ANY TOOL with 3 numbered
     preconditions (read framework, detect state, emit brief) →
     Tools at hand / install rule → precedence over chat-env tool
     mandates. Dropped the redundant "Deliverable = .md file"
     paragraph (it's stated in framework Core, which is mandatory
     reading per the no-tool-call gate).
  2. **Install rule promoted to the operating manual.** Previously
     only at line 412 (inside Framework Reference → Self-validation).
     Now also stated at the top: "if you have shell or
     code-execution access and `research-buddy --version` fails,
     `pip install research-buddy`". Cross-links to the full rule
     at [Self-validation](#self-validation).
  3. **Framework Core version-compatibility check rewritten.**
     Same-MAJOR/MINOR-older now pauses at top of Turn 1 and asks
     the user "(a) pause so you can run `research-buddy upgrade
     <file>.md --apply` and re-upload, or (b) proceed with the
     older framework this session?" *before* composing the brief
     or calling any research tool. Previously: silent note in the
     Turn 2 change summary. The new behavior can cost a turn, but
     that's the trade-off — if (a), the next session resumes from
     a refreshed file.
  4. **Visible blockquote inside the title block** now names tool
     calls explicitly ("before any other action — including any
     tool call (web search, extended research, code execution,
     etc.)"). Belt-and-suspenders for agents that skip HTML
     comments.
  5. **Upgrade pathway** — `research-buddy upgrade <file>.md
     --apply` now refreshes three template-owned regions: the
     preamble (the HTML comment), the framework block (existing),
     and the visible blockquote. Implemented as two new functions
     in `src/research_buddy/upgrade_md.py` (`_replace_preamble`,
     `_refresh_agent_reminder`) wired into `upgrade_md()`
     alongside the existing frontmatter migration and
     framework-block swap. Six new tests in
     `TestPreambleReplacement` and `TestAgentReminderRefresh`.
     Existing v1.9.1 projects will pick up the operating-manual
     changes on `upgrade --apply`.

### Next steps

- Watch downstream agents to confirm the no-tool-call gate
  actually changes behavior. The structural fix is in place but
  agent compliance is empirical — the next agent skip would tell
  us whether the prominence + precedence statement was enough or
  whether the operating manual needs to be promoted out of HTML
  comments into visible Markdown.
- If the preamble proves load-bearing, consider extending
  `upgrade_md.py` to refresh the visible title-block prose too
  (currently it's mostly project-owned with the blockquote being
  the only template-owned line inside, but the format line and
  filename-convention list could grow template-owned bits).

### Blockers / open

- None.

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
