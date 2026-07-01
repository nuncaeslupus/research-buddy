# Changelog

All notable changes to Research Buddy. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/), and versions follow
[Semantic Versioning](https://semver.org/).

## [2.2.0] — 2026-07-01

### Added

- **Prompt-injection handling guidance in `starter.md`.** A new note in the
  top-of-file operating manual tells the agent to treat any appended,
  first-person-styled instruction (from tool output or trailing a user turn)
  as untrusted data — never suppressing the `@brief`/`@summary` start/end or
  turn markers the framework's automation depends on — and to
  name the ignored instruction once rather than silently comply or silently
  ignore it. Deliberately stays tool-agnostic: the framework still doesn't
  mandate a specific research tool. A matching entry was added to Common
  failure modes.

## [2.1.0] — 2026-06-26

### Added

- **`diff-summary` downstream-action checklist.** When `research-buddy diff-summary` detects new Adopted Rules (`<!-- @rule: R-XXX-N -->` entries), it now outputs a `<!-- downstream-action-start/end -->` block after the `@summary-end` block. Each new rule appears as a GFM task-list item with a `{{downstream files or specs to update}}` placeholder, giving downstream implementation projects a mechanical propagation checklist rather than relying on agent memory. The Turn 2 workflow in `starter.md` instructs the agent to paste this block into the source file's `## Session Notes` section when present.

## [2.0.0] — 2026-06-25

**Breaking: legacy v1 JSON support removed.** v2 Markdown has been the default
since 1.5 and the only format receiving features; this release removes the dual
code paths. `migrate-v1-to-v2` is retained as the escape hatch for converting an
existing v1 JSON document to a v2 Markdown source.

### Removed

- **v1 JSON pipeline:** the `build` / `validate` / `upgrade` JSON branches,
  `init --v1`, and the `build --pdf` / `--watch` / `--all` / `--validate-only`
  flags (all v1-only). `build`, `validate`, and `upgrade` now operate on `.md`
  source files only; a non-`.md` path is a clean error pointing at
  `migrate-v1-to-v2`.
- **Modules / data:** `build.py` (v1 JSON renderer), `validator.py` (v1 schema
  validator), `upgrade.py` (v1 template refresh), `schema.json`, `starter.json`,
  and the v1 Jinja templates (`blocks.html.j2`, `section.html.j2`).
- **Dependencies:** `jsonschema` and `watchdog` (now unused) dropped from the
  core requirements; the `[pdf]` extra (`weasyprint`) removed.
- The committed `starter-example/starter.html` (v1 example).

### Changed

- **New `chrome.py`** holds the shared HTML chrome (Jinja env, asset loading,
  `BuildState`, footer, language resolution) the v2 renderer and the migrator
  need — extracted from the deleted `build.py` so no v1 rendering code survives.
  `_parse_semver` moved to `upgrade_md.py` (its only remaining caller).
- `migrate-v1-to-v2` is retained and still tested; its v1 sample input now lives
  in `tests/fixtures/v1_starter.json` (test data, no longer shipped in the wheel).
- README and CLAUDE.md rewritten for the v2-only tool; `migrate` is documented as
  the sole remaining JSON-reading command.

## [1.21.0] — 2026-06-25

v2 HTML sanitization — the render-time half of the v2 trust model. A v2 document
is LLM-authored Markdown rendered to a single-file HTML page opened in a browser,
and the renderer passes raw HTML through (for anchors, status chips, inline SVG).
Previously a prompt-injected or careless agent emitting `<script>` / `onerror=` /
`javascript:` was only *warned* about (1.14.0 / PR-8); now it is also stripped at
build time.

### Added

- **`sanitize_html` (new `sanitize_html.py`, backed by `nh3`/ammonia).** Every
  agent-authored HTML fragment on the v2 build path — each tab's rendered body,
  the frontmatter `banners`, and the tab labels — is sanitized against an
  allowlist matched to the framework's element catalog. Active content is removed
  (`<script>` and its contents, inline `on*=` handlers, `javascript:`/`data:`
  URIs, `<iframe>`/`<object>`/`<foreignObject>`/`<animate>`, and any unlisted
  tag/attribute) while prose, tables, callouts, verdicts, cards, status chips,
  and **inline SVG illustrations** are preserved. SVG is rendered but sanitized
  as untrusted.
- **`nh3>=0.3.0`** added as a core dependency (the `filter_style_properties`
  sanitizer option requires 0.3.0).
- **"Security & trust model (v2 Markdown)" section** in the README documenting
  the trust boundary and the validate-warns / build-strips defense in depth.

### Changed

- **Frontmatter scalars are escaped into the page chrome.** `title`, `version`,
  and `date` (which reach `<title>`, the footer and the sidebar) and the resolved
  `lang_code` (`<html lang>`) are now `html.escape`d in `build_md`, closing a
  `title: </title><script>…</script>` breakout in the otherwise-trusted chrome.
- **`starter.md` rule 7** now states that the build enforces the raw-HTML
  allowlist (strips active content), so agents don't rely on executable HTML.

## [1.20.0] — 2026-06-25

Print / browser-PDF stylesheet overhaul. The generated HTML now produces a
clean printout (browser "Print → Save as PDF", or WeasyPrint on the v1 path)
instead of a clipped, dark-theme-bleeding page. Shared stylesheet, so both the
v2 Markdown and v1 JSON outputs benefit.

### Changed

- **`@media print` rewritten.** It now:
  - forces the **light palette** regardless of the on-screen theme toggle, and
    sets `print-color-adjust: exact` so badge/tag/table-header background colours
    still print legibly;
  - **unpins the fixed app-shell layout** (`#layout` / `#main` height + overflow)
    so the document flows across pages instead of being clipped to one screen;
  - **starts each tab on a fresh page** and stacks every tab, mirroring the
    on-screen tab structure;
  - keeps **cards, tables, code blocks, callouts and verdicts from splitting**
    across a page boundary (`break-inside: avoid`), **repeats table headers** on
    each page, and keeps a heading with the content that follows it;
  - **wraps long code lines** (`white-space: pre-wrap`) instead of clipping them,
    since paper has no horizontal scroll;
  - sets sane `@page` margins and trims the wide on-screen section gaps.

## [1.19.0] — 2026-06-23

Mobile-friendly tab bar.

### Changed

- **Scrollable tab strip with fade-edge affordances.** The tab buttons now live
  in a dedicated horizontally-scrollable container (`#tab-scroll` inside
  `#tab-scroll-wrap`). JS-controlled left/right fade overlays appear when more
  tabs are off-screen, and switching tabs scrolls the active button into view.
  The menu and theme toggles stay pinned outside the scroll area.

## [1.18.0] — 2026-06-23

Three design decisions from the Opus review initiative (PR-14):

### Added

- **`agent_state: complete`** — new recognized frontmatter state for when a project's research is declared done (empty-queue option 4). Framework documents the state, validator warns on unknown `agent_state` values, and `research-buddy turn1` surfaces a clear "project is complete" error instead of producing a blank brief.
- **v1 JSON deprecation warnings** — all v1 entry points (`build`, `validate`, `upgrade`, `init --v1`) now print a deprecation notice to stderr when processing a `.json` file. v1 is feature-frozen; planned removal in v2.0.

### Framework changes

- **`agent_state: complete` arm** added to the session state detection table in Framework (Core): agents that receive a complete-marked file offer three options (add topics, refresh Deliverable Synthesis, or leave as-is) instead of automatically starting a session.
- **Empty-queue option (4)** now explicitly directs agents to set `agent_state: complete` on the Turn 2 atomic write when the user declares research complete.

### Decisions recorded (no code change)

- **Framework token overhead (P1-8):** closed without implementation. The ~730-line framework is load-bearing for agent compliance (empirically demonstrated in sessions 16/17); context windows handle it comfortably; the agent-efficiency tooling (`turn1`, `bump`, `locate`, `diff-summary`) already covers mechanical overhead. Any framework split risks fragmenting the compliance mechanism without proportional benefit.
- **v1 sunset targets:** v1 feature-frozen as of this release. Planned: v2.0 — v1 `init --v1` removed (no new v1 doc creation); v3.0 — v1 build/validate/upgrade paths fully removed.

## [1.17.0] — 2026-06-23

Deliverable Synthesis capstone — adds an optional closing section for
synthesizing project findings into the stated deliverable form.

### Added

- **`## Deliverable Synthesis` section** — optional closing section in the
  v2 starter with `<!-- @anchor: synthesis -->` / `<!-- @end: synthesis -->`.
  Activated by a new empty-queue option (5): "synthesize deliverable — write or
  refresh the Deliverable Synthesis section." Carries cite-or-cut guardrails
  (every claim must be anchored to a tracker finding or named uncertain) and
  living-section semantics (safe to rewrite wholesale each refresh).
- **`_LIVING_ANCHORS`** in `validator_md.py` — a named set of anchor IDs exempt
  from the append-only invariant. Currently contains only `"synthesis"`: removing
  the Deliverable Synthesis section between versions does not fire `anchor-removed`.
- **Empty-queue option (5)** added to Queue rules in the framework; agents that
  encounter an empty queue now have five choices, including refreshing the
  Deliverable Synthesis.

## [1.16.0] — 2026-06-23

Methodology completeness release — six editorial additions to `starter.md`
aligning the framework text with actual tool behavior and established research
best practices.

### Added

- **Turn-2 hypothesis resolution step** — explicit Turn 2 step 3: "Resolve
  pre-registered hypotheses." Agents compare findings + vetted second opinions
  against pre-registered PASS/FAIL metrics and assign `VALIDATED` / `PROPOSED` /
  `REJECTED` to each. Prior versions pre-registered hypotheses in Turn 1 step 4
  but had no explicit Turn 2 step to close the loop. Steps 3–8 renumbered 4–9.
- **Session-note template now matches `bump.py` output exactly.** Added a
  hypothesis-resolution table, `**Cross-section impact.**`, and
  `**Compliance validation.**` fields. Two sync-guard tests
  (`TestSessionSkeletonSyncWithStarterTemplate`) enforce the template stays in
  lockstep with `_session_skeleton()` output.
- **Excellence bar guidance.** Note in the Second-opinion brief template
  explaining that the excellence-level placeholder must specify minimum source
  count, domain rigor standard, and specificity requirement.
- **Queue prioritization rubric.** Four-point rubric in Queue rules:
  dependency, risk-to-deliverable, yield-per-turn, evidence freshness.
- **Rule supersession mechanics.** Step-by-step instructions in Adopted Rules
  for marking old rules `SUPERSEDED` + `superseded_by`, new rules `supersedes`,
  and writing the Changelog note.
- **Queue/tracker dual-membership rule.** Explicit prohibition in Queue rules:
  a topic ID must not appear in both the Open Research Queue and the Research
  Tracker simultaneously.

## [1.15.0] — 2026-06-23

Brief-skeleton unification — aligns the preamble's compact brief skeleton with
the canonical Second-opinion brief template so agents hand-writing from the
preamble produce the same placeholder names as `research-buddy turn1` output.

### Changed

- **Preamble brief skeleton placeholder names unified** with the canonical
  template: `{{PROJECT_AND_BASIC_CHARACTERISTICS}}`,
  `{{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}`,
  `{{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}`,
  `{{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}`. Previously used shorter
  names that diverged from `turn1` output, causing agents to produce mismatched
  placeholders depending on which source they read.
- **Sync guard tests** (`TestBriefSkeletonSyncWithCanonicalTemplate`, 2 tests):
  every non-placeholder prose line from the canonical template must appear in
  `turn1` output; every canonical placeholder name must appear in `turn1.py`'s
  source. Catches future name drift automatically.

## [1.14.0] — 2026-06-23

Opus review initiative — first batch of code quality and correctness fixes
surfaced by a comprehensive codebase audit, plus editorial framework improvements.

### Added

- **`src/research_buddy/fileio.py`** — two shared file-I/O helpers:
  `read_text_or_error(path)` reads UTF-8 and raises `FileReadError` on invalid
  bytes (uniform message + exit 1, matching the JSON read hardening from
  v1.11.0); `atomic_write(path, text)` does a temp-sibling write → rename with
  `try/finally` cleanup so a failed write leaves no `.tmp` behind. Adopted by
  all atomic writers: `bump`, `upgrade`, `migrate`, and `init`.
- **`research-buddy build` now gates the v2 HTML render on validator errors** —
  if `validate` finds error-severity issues the build aborts (exit 1, no HTML
  written). Warnings still build.

### Fixed

- **`validate` append-only enforcement extended** to Research Tracker rows
  (`Q-`/`T-` first-column IDs; the seed `T-000` is exempt) and individual
  reference bullets. Previously only whole per-version reference subsections and
  anchor names were protected. An unclosed fenced code block is now an error
  pointing at the opener (it used to silently swallow the rest of the document).
  Broken cross-links promoted from warning to error (starter illustrative example
  targets remain `info`). `_collect_entry_ids` made fence-aware so `@da`/`@rule`
  markers inside template examples are not collected as live entries.
- **`migrate-v1-to-v2` collision bugs** fixed:
  - Changelog sort was not patch-aware (`1.1.0` and `1.1.4` sorted to the same
    key, producing an unstable order). Now uses a 3-tuple `(major, minor, patch)`.
  - Queue-ID synthesis was not collision-free (`Q-{i+1}` could duplicate a
    tracker ID or an inline ID). Now two-pass: collect all existing IDs first,
    then assign the lowest free `Q-NNN`.
  - Verdict `<a id>` was `rid.lower()` — left spaces/punctuation in the ID for
    labels without a clean `R-`/`DA-` prefix. New `_slug()` helper; idempotent
    for well-formed IDs.
  - A v1 tab label that slugs to a canonical framework anchor (e.g. "References")
    would clobber the framework's own anchor. Now mangled to `…-tab` via a
    `CANONICAL_ANCHORS` set.
  - Changelog entries now render `### vX.Y — DATE`; the synthetic top entry
    carries `meta.date`.
  - `build_frontmatter` now writes `project.source_tiers` (tier_1/tier_2/discovery) and `project.domain_rules`, matching the v2 starter shape.
- **`clean_md` fence-awareness** — `collect_framework_targets` now skips lines
  inside fenced code blocks. The starter's `### Templates` section carries
  fenced example blocks with placeholder `<a id>` values and headings; collecting
  them caused `unwrap_framework_links` to incorrectly strip body links like
  `[Q-001](#q-001)` (a promoted tracker row) to plain text.
- **`clean_md` EOF content loss** — a malformed-opener path (a `framework.core`
  anchor with no matching `@end`) did `break`, dropping everything from the opener
  to EOF. Now preserves the opener and all remaining lines verbatim.
- **HTML tab label escaping** — `data-tab-label` now uses `html.escape`, so a
  label containing `"` no longer breaks the attribute.
- **Multi-paragraph inline content** — `_md_render_inline` correctly flattens
  multi-paragraph input to `<br><br>` instead of leaving `</p><p>` inside inline
  HTML contexts.
- **`</style>` in theme CSS neutralized** — backslash-escapes any `</style>`
  before user theme CSS is inlined into the `<style>` block (both v1 and v2
  paths), closing a Jinja `autoescape=False` injection point.
- **`upgrade` edge cases** — v1 upgrade now refuses to overwrite the doc's
  `research_buddy_version` with a lower tool version (forward-only guard,
  matching v2). v2 upgrade now skips only the version-bump step when the doc is
  ahead, still refreshing the preamble and framework block. YAML indent is
  sniffed and matched when inserting new frontmatter keys.

### Changed

- **Framework truth-up** — `starter.md` updated to match actual tool behavior:
  `bump`, `locate`, and `diff-summary` surfaced as the blessed Turn-2 path
  in "Tools at hand" and Turn-2 steps 4 + 6; the version-compat pause
  clarified as a pre-session gate; the mechanical self-checks list corrected
  (plain-text `R-XXX-N` references are *not* flagged by `validate`);
  `research_buddy_version` added to the required-fields checklist.
- **Dangerous HTML warnings** — the v2 validator now warns on `<script>`,
  inline `on*=`, or `javascript:` in the document body (outside fenced/inline
  code). These are warnings, not errors, so illustrative examples still build.
- **Release workflow** — the `vX.Y.Z` git tag is now created in the
  `github-release` job (after PyPI publish succeeds), not in the `build` job.
  A failed PyPI upload no longer leaves an orphaned tag that locks the release
  guard. Release notes now extract only the matching `## [VERSION]` section from
  `CHANGELOG.md` instead of dumping the entire history.

## [1.13.0] — 2026-06-08

Brief-gate hardening and localization release. Root cause traced to a real
session where an agent skipped the second-opinion brief: it had been uploaded a
*clean view* (`*_v*.md`) instead of the source file, and the preamble that
survived `clean` referenced framework sections `clean` had removed — dangling
links that turned "fill a template" into "generate from scratch."

### Added

- **`research-buddy turn1 <file>`** — prints the Turn-1 second-opinion brief
  skeleton pre-filled from frontmatter (project description, source tiers, fixed
  Never-tier) plus the top Open Research Queue row (topic + objective). Judgement
  slots are left as `{{placeholders}}`; guidance to stderr so stdout is clean to
  paste. "Fill, don't remember."
- **HTML section-heading localization** (`localize.py`): framework headings
  ("Open Research Queue", "References", Project Specification subheadings)
  display in the document's `language.code` while English slugs/IDs are preserved
  so cross-links never break. Ships Spanish (`es`); `section_labels` frontmatter
  overrides/extends.

### Fixed

- **`research-buddy clean` now strips the agent preamble.** The operating-manual
  HTML comment between the frontmatter and the first `<!-- @anchor:` line is
  replaced with a one-line self-identifying note pointing back at the
  `*-source.md`. Previously the preamble survived `clean` with its framework
  cross-links rewritten to dangling plain text — an operating manual pointing at
  sections that no longer existed.
- **Hardened starter preamble**: brief gate stated first *and* last (primacy +
  recency), concrete tool families named, inline fill-in brief skeleton so agents
  with a short read window still see the brief contract. Propagates to existing
  docs via `research-buddy upgrade <file>.md --apply`.

## [1.12.1] — 2026-06-05

Bug-fix patch for `migrate-v1-to-v2`. Discovered when migrating a real mature
v1.14 document (31 topics, mixed schema vintage).

### Fixed

- **Language coercion crash.** `meta.language` as a plain string (e.g.
  `"English"`) crashed `migrate` in `build_frontmatter`. Now coerced to
  `{"code": "en", "label": "English"}` via the BCP-47 mapping `build` uses.
- **Project spec read from the wrong location.** In mature v1 docs the real spec
  lives in top-level `doc["project_specific"]`, not in
  `agent_guidelines.project_specific` (which stays at the `[FILL]` template
  value). `migrate` now does a per-field merge: the filled `agent_guidelines`
  value wins; missing fields fall back to the top-level field. Recovers
  `deliverable_type`, `timing`, source tiers, and never-tier.
- **Overview tab dropped unconditionally.** `migrate` now extracts substantive
  sections from the `overview` tab into a top-level `## Overview` section,
  dropping only navigation boilerplate (Quick Links / How to Navigate / …).
- **Queue done-detection based only on the ✦ glyph.** A row marked "Researched
  v1.3" (no glyph) remained in both the Open Research Queue *and* the Research
  Tracker, violating the "no ID in both" invariant. Detection now also matches
  `/researched/i` text and any row whose Q-NNN ID is already in the tracker.

## [1.12.0] — 2026-06-02

Validation-hardening release motivated by a real recovery effort: when a v2
document is hand-assembled or repaired (e.g. reconstructing content the old
lossy v1→v2 migration had dropped), it is easy to leave **duplicate anchor or
entity markers** at section boundaries. The validator previously paired markers
by name and ignored a second occurrence, so these slipped through — yet they are
exactly the kind of latent hazard that derails an agent's `str_replace` surgery
(and `locate`), since the insertion point is no longer unique. This release
makes anchor/entry uniqueness an enforced invariant. Backwards-compatible for
any document that was already well-formed.

### Added

- **`duplicate-anchor` / `duplicate-end` validation errors** — a second
  `<!-- @anchor: X -->` or `<!-- @end: X -->` for the same name is now an error
  (it reports the line of the first occurrence). Markers inside fenced code
  blocks are still ignored.
- **`duplicate-entry` validation error** — a second `<!-- @rule: -->`,
  `<!-- @da: -->`, or `<!-- @session: -->` for the same ID is now an error
  (duplicate IDs produce duplicate `<a id>` link targets and an ambiguous
  insertion point). A flagged duplicate skips the link-target lookahead so it
  isn't re-reported as a separate error.

### Fixed

- **Migration `None`-handling**: a v1 block field set to an explicit `null`
  (`title`, `body`, `phase`, `blocks`) no longer serialises as the literal
  string `"None"` or raises `TypeError` — these spots now coerce via `or ""`
  / `or []`, completing the unvalidated-JSON hardening from 1.11.x.

## [1.11.0] — 2026-06-01

Agent-efficiency release: three new read-only/mechanical helper commands that
take the deterministic parts of the 2-turn workflow off the agent's plate, plus
robustness and starter-hygiene fixes. All additions are backwards-compatible —
existing v2 documents build and validate unchanged.

### Added

- **`research-buddy bump <source.md> <Q-NNN>`** — performs the mechanical
  Turn-2 edits for one researched queue item in a single command: MINOR
  `version` + `date` bump, moves the `Q-NNN` row from the Open Research Queue
  into the Research Tracker (preserving the ID, attributing the new version),
  inserts an empty Session Notes skeleton (pre-registration, a
  hypothesis-resolution table, sources table, cross-section-impact and
  compliance-validation lines), and prepends empty Changelog + References
  stubs. `{{placeholders}}` are left for the agent to fill. Dry-run by
  default; `--apply` writes a new
  `{file_name}_v{version}-source.md` atomically and validates it with the input
  as `--prior`.
- **`research-buddy locate <source.md> <anchor>`** — prints the line of the
  *live* `<!-- @end: <anchor> -->` insertion point plus surrounding context.
  Matches full-line markers outside fenced code blocks, so inline prose
  mentions and fenced template examples never collide with the real marker (the
  fence-and-full-line-aware lookup a plain `grep` can't do). Accepts `rules`,
  `@end: rules`, or the full comment form.
- **`research-buddy diff-summary <old.md> <new.md>`** — emits the mechanical
  part of the Turn-2 `<!-- @summary-start --> … <!-- @summary-end -->` block by
  diffing two versions: version bump, queue→tracker moves, Adopted Rules
  added/revised, Discarded Alternatives and Session Notes added, and the
  append-only-invariant check (PASS / the violations found). The narrative
  sentences stay agent-authored as a `{{placeholder}}`; exit code 1 signals an
  append-only violation.

### Changed

- **Starter marker hygiene.** Reworded the prose mentions in `starter.md` that
  embedded a literal `<!-- @end: X -->` (e.g. *"paste this immediately before
  its `<!-- @end: rules -->` marker"*) to *"this section's closing `@end`
  marker"*, so every live `@end: X` marker is now the unique occurrence of its
  ID. An agent grepping for an insertion point gets one hit instead of "found
  multiple times". The framework-block changes propagate to existing projects
  via `research-buddy upgrade <file>.md --apply`.
- **Internal layout.** Split the monolithic `main.py` into `cli.py` (argparse
  construction + dispatch) and a `commands/` package (one module per
  subcommand). `main.py` remains a re-export façade, so
  `from research_buddy.main import …` imports keep working.

### Fixed

- **Malformed-input handling on the JSON paths** (`build` / `validate` /
  `upgrade` / `migrate`): invalid UTF-8 bytes and unparseable JSON now report a
  clean error and exit code instead of an uncaught traceback. Version discovery
  was also hardened for multi-component version strings.

## [1.10.0] — 2026-05-14

Operating-manual hardening for the v2 starter, with an upgrade pathway so
existing projects pick up the same improvements via `research-buddy
upgrade <file>.md --apply`.

### Changed

- **Starter operating manual** (top HTML comment between frontmatter and the
  first `@anchor`): compacted into a tight ≤12-line block that fits inside
  any reasonable first-read window. Carries an explicit no-tool-call gate
  ("DO NOT CALL ANY TOOL until you have read framework, detected state,
  and emitted the brief"), the install rule ("if shell access exists and
  `research-buddy --version` fails, `pip install research-buddy`"), and a
  precedence statement over chat-environment tool-priority mandates ("MUST
  use tool X first", "use only tool Y"). Driven by a postmortem of an agent
  that skipped the second-opinion brief because surrounding tool mandates
  outweighed the framework's instructions.
- **Framework Core version-compatibility check** (`research_buddy_version`
  vs the framework loaded for the session): same-MAJOR/MINOR-older now
  *pauses at the top of Turn 1* and asks the user "(a) pause so you can
  run `research-buddy upgrade <file>.md --apply` locally and re-upload, or
  (b) proceed with the older framework this session?" before composing the
  brief or calling any research tool. Previous behavior was a silent note
  in the Turn 2 change summary, which surfaced after the work was done.
- **Visible agent-reminder blockquote** inside the title block now names
  tool calls explicitly ("before any other action — including any tool
  call (web search, extended research, code execution, etc.)").

### Added

- **`research-buddy upgrade <file>.md --apply` now refreshes three
  template-owned regions** instead of one. Previously only the framework
  block (between `<!-- @anchor: framework.core -->` and `<!-- @end:
  framework.reference -->`) was swapped. Now also:
    - the **preamble** — the operating-manual HTML comment between the
      frontmatter close and the first `<!-- @anchor:` line;
    - the **agent-reminder blockquote** — the single visible
      `> **Agent: ...` line inside the title block.
  Project-owned content (frontmatter values, title heading, project spec,
  queue, tracker, rules, DAs, sessions, references, changelog) is still
  preserved exactly. Existing v1.9.1 projects will pick up the operating-
  manual hardening on `upgrade --apply`.

## [1.9.1] — 2026-05-14

### Fixed

- Starter template: the `adopted_in` field in the Adopted Rules template now
  uses `v1.X` as its placeholder (was `v1.0`, which misled agents into writing
  the initial version number instead of the current session version).

## [1.9.0] — 2026-05-12

Session-zero hardening release. Driven by a postmortem where an agent mis-ran
session zero, mistaking `[FILL]` placeholders for evidence the project was
already configured.

### Added

- **`agent_state` frontmatter field** — explicit `needs_session_zero` / `ready`
  state token the agent overwrites in session zero Turn 2. Replaces the implicit
  "domain null → session zero" convention. `research-buddy upgrade <file>.md
  --apply` backfills `agent_state: ready` for existing post-session-zero docs.
- **Unmissable operating-manual preamble** — multi-line HTML comment immediately
  after the YAML frontmatter: STOP, read the file first, deliverable is a
  versioned `.md` file, NOT a chat response.
- **Session-zero Turn 1 mode-switch**: three-case detection — (a) generic
  kickoff → ask 5 setup questions; (b) all answers supplied/inferable → skip
  questions, ship both turns in one message; (c) a research request → treat it
  as implicit spec and seed it as Q-001.
- **Forward-reference convention** — pending queue items (not yet promoted to
  Tracker / Session Notes) have no `<a id>` target; reference them as plain
  `Q-NNN`, not as a Markdown link. `research-buddy validate` enforces it.
- **`### Templates` subsection** in Framework Reference — the three fenced
  template examples (rule, DA, session) moved out of the user sections so
  naïve `str_replace` inserts before `<!-- @end: ... -->` can't accidentally
  clobber template scaffolding.
- **Self-install instruction** — when the agent has shell access but
  `research-buddy` is not installed, run `pip install research-buddy` first.

### Changed

- **Common failure modes** — "chat-output" anti-pattern added as the first
  bullet: producing the session output as a chat response / artifact rather than
  the versioned source file.

## [1.8.0] — 2026-05-10

v2 element catalog — standardized vocabulary and HTML renderers for structured
content in v2 Markdown documents.

### Added

- **Element catalog** in Framework Reference: 18 supported elements + 7 callout
  kinds + 2 algorithmic items. Closed list — anything not listed should be prose,
  lists, or tables.
- **Callout rendering** — GFM `> [!KIND]` admonitions render as styled callout
  boxes: `NOTE`, `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`, `LIMITATION`,
  `HYPOTHESIS`.
- **Fenced block renderers**: `rb-verdict` (evidence verdict with color + icon),
  `rb-cards` (card grid), `rb-banner` (styled banner). YAML body syntax.
- **`rb-ok` / `rb-bad` / `rb-flag` inline chips** — raw
  `<span class="rb-ok">…</span>` pass through markdown-it's `html=True`.
- **References section styling** — `<!-- @anchor: references -->` triggers a
  compact `<ul class="references">` style (tighter spacing, hanging indent).
- **Frontmatter `banners`** — list of banner blocks rendered above the first tab.
- **Frontmatter `theme_css` cascade** — custom CSS applied in order: CLI
  `--theme` flag → `theme_css` frontmatter field → conventional `theme.css` in
  the project directory.
- **Numbered H3/H4 subheadings** — `### 1.1` / `#### 1.1.1` render a
  `<span class="num">` prefix matching v1 behavior.
- **Content-based table column widths** — new `table_layout.py` module computes
  language-independent column widths from per-column text profiles (p50/p90,
  has-spaces, is-token). Similar tables share a column signature so widths stay
  consistent across a document.

## [1.7.0] — 2026-05-07

### Added

- **`research-buddy upgrade <file>.md`** — v2 dispatch path (dry-run default,
  `--apply` to write). Replaces the framework block in an existing v2 source
  file with the installed `starter.md` version, bumps `research_buddy_version`
  forward only (refuses to downgrade), renames legacy `format_version` →
  `doc_format_version`, and inserts missing `project.source_tiers` /
  `project.domain_rules` frontmatter fields.
- **`research-buddy init` defaults to v2 Markdown** — `research-buddy init
  <dir>` now scaffolds `source/research-document.md`; `--v1` keeps the legacy
  JSON scaffold.

### Changed

- v2 `upgrade` raises an error when the document's `research_buddy_version` is
  *ahead* of the installed tool, directing the user to upgrade the CLI or
  manually set the field. (v1 `upgrade` still silently downgrades — known
  divergence.)

## [1.6.0] — 2026-05-07

Framework hardening release — substantial new rules and a renamed frontmatter key.

### Added

- **Validation MUST** — Turn 2 now requires agents to invoke `research-buddy
  validate` (or paste a mental-simulation checklist when shell access is missing)
  and include the validator output *before* the file artifact. Was a SHOULD.
- **`doc_format_version` frontmatter key** — replaces the legacy `format_version`
  key (still accepted with a `deprecated-format-version-key` warning).
  `research-buddy upgrade <file>.md --apply` renames the key.
- **`project.source_tiers` and `project.domain_rules`** frontmatter blocks —
  fix previously-dangling `{{project.source_tiers.tier_1}}` placeholder
  references.
- **Rules status lifecycle and force-keyword guidance** (`Status: Active /
  Superseded / Retired`, RFC 2119/8174 keyword norms).
- **Queue Stable IDs and Re-queuing rules** — IDs never change once assigned;
  resolved topics may be re-entered with a new ID.
- **`brief-slot-empty-but-section-non-empty` validation warning** — fires when
  the Turn 1 brief context slot says "None." but the corresponding section has
  live entries.
- **Session-start version-compatibility check** — advisory comparison of
  `research_buddy_version` in the doc against the loaded framework version; MAJOR
  mismatch surfaces as a one-line warning before work starts.

## [1.5.0] — 2026-05-07

v2 Markdown is now the **recommended format** for new research projects. The
complete v2 surface ships production-ready.

### Added

- **`build_md.py`** — renders v2 Markdown source files to single-file HTML using
  the same tab-bar / sidebar chrome as v1 JSON. Each `## H2` becomes a tab;
  `### H3` / `#### H4` feed the sidebar navigation. `research-buddy build`
  dispatches on file extension (`.md` → v2 pipeline, `.json` → v1 pipeline).
- **`validator_md.py`** — validates v2 source files: frontmatter required fields,
  `@anchor`/`@end` pairing, `@rule`/`@da`/`@session` IDs, cross-links,
  `--prior` append-only invariants, version compatibility.
- **`clean_md.py`** — strips the framework block and agent preamble to produce a
  clean reader-facing Markdown view. Called by `research-buddy clean`.
- **`migrate_v1_to_v2.py`** — converts a v1 JSON document to v2 Markdown source.
  Invoked via `research-buddy migrate-v1-to-v2`.
- **`starter.md`** — bundled v2 session-zero template (shipped in the wheel).
- **`starter-example/starter-md.html`** — rendered v2 example alongside the
  existing `starter.html`.
- **New runtime dependencies**: `markdown-it-py>=3.0`, `mdit-py-plugins>=0.4`.

### Changed

- `research_buddy_version` in `starter.md` frontmatter is now tracked by
  `scripts/sync_version.py` alongside the four existing version-sync targets
  (five total).

## [1.4.0] — 2026-04-26

### Changed

- **`build.py` migrated to Jinja2 templates.** All HTML markup moved from Python
  f-strings into `base.html.j2`, `blocks.html.j2`, and `section.html.j2`.
  Python functions are now 1–4 line wrappers around Jinja macros. Output is
  byte-identical to 1.3.x (confirmed by `make regen-example`). Theme-aware
  conditionals and future block types are now cheap template edits.

### Added

- New runtime dependency: `jinja2>=3.1` (+ transitive `markupsafe`).

## [1.3.4] — 2026-04-25

### Changed

- **Light theme by default** — generated HTML now opens with a light palette;
  the ☀/☾ toggle in the tab bar switches to dark and persists the preference in
  `localStorage.setItem('rb-theme', …)`. An inline `<head>` script reads the stored
  preference before first paint to avoid FOUC.

## [1.3.3] — 2026-04-25

### Fixed

- **Sidebar overlay on landscape phones.** Media query expanded from
  `(max-width: 768px)` to `(max-width: 768px), (max-height: 500px)`; the
  JavaScript side uses `window.matchMedia` with the same query so CSS and JS
  can't drift.

## [1.3.2] — 2026-04-25

### Fixed

- **Tab bar mobile overflow** — on narrow screens the tab bar clipped with no
  way to scroll. Added `overflow-x: auto`, hidden scrollbar, and `flex-shrink:
  0; white-space: nowrap` on tab buttons. Sidebar burger menu is
  `position: sticky; left: 0` so it stays pinned while tabs scroll.

## [1.3.1] — 2026-04-25

### Fixed

- **Oversized logo** — bundled `research-buddy.png` resized from 1536×1536 px /
  725 KB to 200×200 px / 27 KB (−96%). Generated HTML drops from ~944 KB to
  ~190 KB per document.

## [1.3.0] — 2026-04-25

### Added

- **`research-buddy upgrade <path>/*.json --apply`** — re-syncs an existing v1
  JSON document's `agent_guidelines` with the installed `starter.json`. Preserves
  `agent_guidelines.project_specific` and `session_zero.note`. Dry-run by default
  (exits 1 on changes); `--apply` writes atomically and validates. Idempotent.

### Changed

- **`starter.json` reorganization** — `agent_guidelines.framework` keys reordered
  for top-down readability. Brief template extracted from `turn_1_research` into a
  single canonical `framework.second_opinion_review.brief_template`. Citation
  format aligned to `Title, Author, Year, Venue, DOI/URL` everywhere.
- **`upgrade` reorders existing files** at four key levels (top-level,
  `agent_guidelines`, `meta`, `project_specific`); custom keys land at the end.

## [1.2.2] — 2026-04-24

Maintenance patch. No user-visible changes.

## [1.2.1] — 2026-04-19

### Added

- **Turn markers** — every defined turn ends with a human-readable banner +
  machine-readable `<!-- research-buddy:turn=...:status=... -->` HTML comment.
  A `detection_regex` is exposed in `starter.json` / `starter.md` for
  external automation.

### Changed

- **Implicit approval** — submitting second-opinion sources and a continue
  signal in the same message, with clean vetting and no blocking contradictions,
  counts as implicit approval; Turn 2 proceeds without a separate go-ahead.
- **`html_generation.agent_action`** now distinguishes shell-access mode (run
  the build command) from no-shell / web-chat mode (print the command verbatim,
  ready to copy).

## [1.2.0] — 2026-04-19

### Added

- **`synthesis_matrix` framework section** — Claim × Source evidence table with
  a pre-registration rule (hypotheses registered before research, not after).
- **`source_discovery` framework section** — multi-database principle, author
  verification, preprint caution, paywalled-access recipes.
- **`pre_update_confirmation` gate** — explicit 4-step preflight before Turn 2
  atomic writes: second-opinion sources present, evidence clean-vetted, no
  blocking contradictions, sources appended to the document.

## [1.1.1] — 2026-04-19

Docs and release-infrastructure patch. No code changes.

### Fixed

- **README**: the "Version compatibility (tool ↔ document)" section described
  in the 1.1.0 CHANGELOG was actually missing from the published README (the
  commit adding it landed 4 minutes after its PR merged and never made it to
  main). 1.1.1 ships the real section with the full MAJOR/MINOR/PATCH
  severity table and the "What if my document is on an older version?"
  subsection.

### Added

- **Automated release pipeline** (`.github/workflows/release.yml`). Pushing
  a `v*` tag now runs: `check-version-sync` + tag/pyproject match →
  `make build` + `twine check` → PyPI upload via trusted publishing (OIDC,
  no stored token) → GitHub release with CHANGELOG body and attached wheel +
  sdist.
- **`RELEASE.md`** runbook: one-time PyPI trusted-publisher setup, the
  bump/tag/push flow, failure recovery, and the PATCH/MINOR/MAJOR rubric.

### Upgrading from 1.1.0

No action required. `pip install --upgrade research-buddy` fetches the new
wheel; the PyPI project page now renders the corrected README.

## [1.1.0] — 2026-04-19

### Added

- **Doc ↔ tool version compatibility check.** Every `research-buddy build` and
  `research-buddy validate` now compares `meta.research_buddy_version` against
  the installed CLI and emits a tiered message:
  - MAJOR differs → error-level warning with a migration recipe.
  - Tool MINOR older than doc MINOR (same MAJOR) → upgrade recommendation.
  - Tool MINOR newer than doc MINOR (same MAJOR) → **silent**. No action required;
    the agent will bump `meta.research_buddy_version` on the next write.
  - PATCH-only difference → silent.

  See the "Version compatibility" section in the README.

- **`--all` on `research-buddy build`** now matches any `*_v*.json` filename,
  not just `document_v*.json`. Consistent with `find_latest_json`. Sort key
  uses only the version suffix so project names that contain digits still
  order correctly.

- **CI version-sync gate.** `make check-version-sync` fails if
  `pyproject.toml`, `src/research_buddy/__init__.py`,
  `src/research_buddy/starter.json`, and the README heading fall out of sync.
  Wired into the lint job.

- **`CLAUDE.md`** at the repo root — short orientation file for AI-assisted
  sessions (layout, Make targets, version-sync flow, test fixtures, 2-turn
  workflow, optional extras).

### Changed (backwards-compatible)

- **HTML assembly refactor.** `build.build_html` no longer contains ~28 lines
  of duplicated footer + language code. Extracted `_resolve_lang_code` and
  `_build_rb_footer_html` helpers; the Research Buddy logo is now loaded and
  base64-encoded exactly once per process via `functools.lru_cache`.

- **BCP-47 language mapping.** A `meta.language` string like `"English"` now
  produces `<html lang="en">` via a lookup table (`_LANGUAGE_NAME_TO_CODE`),
  instead of the literal `lang="English"`. BCP-47 tags (`"en"`, `"pt-BR"`,
  `"es-419"`) pass through. Unknown names fall back to the first whitespace-
  delimited token truncated to 10 chars. Dict form
  (`{"code": "en", ...}`) is unchanged.

- **Error messages.** Four CLI errors that referenced the obsolete
  `document_v*.json` naming now say `*_v*.json`.

- **`validate()` consolidated.** `from research_buddy.validator import validate`
  now lives as a single top-level import in `main.py` (was duplicated in three
  places as lazy imports).

- **`validator.py` internals.** Two ad-hoc `_walk` closures flattened to
  module-scope helpers (`_walk_section_ids`, `_walk_references`). No behaviour
  change.

- **README** restructured: new "Version compatibility" section, the "Document
  format" section now points at the bundled `src/research_buddy/schema.json`,
  and the "Examples" section references `make regen-example`.

### Changed (BREAKING)

- **`weasyprint` is now an optional dependency.** Install the `pdf` extra to
  enable PDF export:

  ```bash
  pip install "research-buddy[pdf]"
  ```

  Rationale: weasyprint has heavy system-level dependencies
  (cairo, pango, gobject-introspection) that blocked installs in restricted
  environments, and the README already described it as optional. If you rely
  on `--pdf`, switch to the extra. The CLI prints a clear install hint if
  weasyprint is missing.

### Fixed

- **`--all` silently ignored most files.** Sorting + globbing were scoped to
  `document_v*.json` only. Now matches any `*_v<MAJOR>.<MINOR>.json` and sorts
  by the version suffix rather than every digit in the filename.

- **Whitespace-only `meta.language` used to raise `IndexError`** inside
  `_resolve_lang_code`. Now falls back to `"en"`.

- **`scripts/sync_version.py`** uses `sys.exit(1)` instead of the REPL builtin
  `exit(1)`.

### Upgrading from 1.0.x

**No action required for existing documents.**

- A document with `meta.research_buddy_version: "1.0"` (or `"1.0.3"`) built
  with this 1.1.0 release is fully backwards-compatible. `research-buddy build`
  and `validate` stay silent, exit 0, and the agent bumps
  `meta.research_buddy_version` automatically the next time it writes.
- If you were relying on `pip install research-buddy` to make `--pdf` work,
  run `pip install --upgrade "research-buddy[pdf]"`.
- If you were scripting against `research-buddy build <dir> --all` and
  suspected it was silently doing nothing, that was this bug — it now picks up
  any `*_v*.json`. Re-run against your directory; the output is the union of
  what was previously selected plus anything that was wrongly skipped.

### Migration guidance for the future

If a future release bumps the MAJOR version (2.0.0, …) you will see an
error-level warning from `research-buddy validate` and `research-buddy build`
the first time you run the new CLI against an old document. The warning will
offer you two concrete options:

1. **Pin the old major** (keep your document as-is):

   ```bash
   pip install 'research-buddy==1.*'
   ```

2. **Migrate the document.** Open the document in an AI session and say
   *"Migrate to research-buddy vX.Y"*. The agent will update the JSON
   structure to match the new schema. The build is not blocked meanwhile;
   output may be wrong until migration is complete.

## [1.0.3] — earlier releases

Not tracked in this file. See `git log` for history prior to 1.1.0.
