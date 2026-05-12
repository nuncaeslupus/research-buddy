---
doc_format_version: 2
research_buddy_version: "1.9.0"
agent_state: needs_session_zero   # → "ready" once session zero completes
version: null            # bumped to "1.0" at end of session zero
date: null               # filled in session zero
file_name: null          # base name for outputs, e.g. "my-research"
title: null              # filled in session zero
subtitle: null
language:
  code: en
  label: English
project:
  domain: null           # one-line description of the project domain
  deliverable_type: null # theory | software | physical_product | document | plan | other
  final_goal: null       # one sentence — what does completed research look like?
  timing: null           # deadline, milestones, or "none"
  validation_gate: null  # what does "validated" mean for this project?
  source_tiers:
    tier_1: null         # primary evidence venues (e.g. arXiv, NeurIPS for ML; PubMed for medical)
    tier_2: null         # official secondary (vendor docs, textbooks, institutional reports)
    discovery: null      # leads only — claims start as PROPOSED until promoted to T1/T2
  domain_rules: null     # methodology rules specific to this domain
ui_strings:
  status_open: OPEN
  status_done: "✦ Researched"
  status_wip: "IN PROGRESS"
---

<!--
AGENT: STOP. Read this entire file before producing ANY output.

The deliverable of every session is a NEW `.md` file at
`{{file_name}}_v{{version}}-source.md` — a versioned source document.
NOT a chat response. NOT an artifact. NOT a summary. NOT a free-form
report. If you have not written the file, the session is not complete.

State signal: the frontmatter field `agent_state` above tells you the
mode. `needs_session_zero` → run [Session zero](#session-zero).
`ready` → run a standard 2-turn research session.

Read [Framework (Core)](#framework-core) and [Framework (Reference)](#framework-reference)
in full before acting. Both are short. Both are required reading. The
framework defines the 2-turn protocol, the second-opinion brief
contract, the atomic write, and the validation gate that precedes
file delivery.
-->

<!-- @anchor: title -->
# {{title}} — Research Document

**Format:** Research Buddy v2 (Markdown) · **Version:** {{version}} · **Updated:** {{date}}

This file is the source-of-truth artifact for the project. The agent edits this file; the clean view (without the framework) and the HTML rendering are derived on demand.

**Filename convention:**

- `{{file_name}}_v{{version}}-source.md` — this file. Agent-edited. Full framework included. Upload this each session.
- `{{file_name}}_v{{version}}.md` — clean view. Generated on demand. Research content only, no framework.
- `{{file_name}}_v{{version}}.html` — HTML rendering. Generated on demand.

> **Agent: read [Framework (Core)](#framework-core) before any other action. Read [Framework (Reference)](#framework-reference) once per session. Both are short. Both are required reading. Reading the framework first is what tells you to (a) compose and emit the second-opinion brief at the top of Turn 1 *before* doing the research itself, and (b) deliver a downloadable, validated source file at the end of Turn 2. Skipping the read order regresses to ad-hoc behavior.**

<!-- @end: title -->

---

<!-- @anchor: framework.core -->
## Framework (Core)

Research Buddy is a structured AI research collaborator that uses this single Markdown file as shared memory and a living reference. Read the entire file before acting.

The Framework sections are generic across all Research Buddy projects. Do not modify them during a session. Improvements to the framework belong upstream in the [research-buddy](https://github.com/nuncaeslupus/research-buddy) project.

### Detect session state

Read the YAML frontmatter at the top. The authoritative signal is the top-level field `agent_state`:

- `agent_state: needs_session_zero` → run **session zero** (project initialization). See [Session zero](#session-zero) for the full flow. Turn 2 of session zero overwrites this field to `ready`.
- `agent_state: ready` → run **standard session** (research one queue topic at a time).
- Field absent (pre-1.9 documents only) → fall back to the legacy signal: `project.domain` null ⇒ session zero, non-null ⇒ standard session. Set `agent_state` explicitly on the next atomic write.

**Version compatibility check (run before any work).** Compare the document's `research_buddy_version` against the framework version you have loaded (the one shown in the [research-buddy](https://github.com/nuncaeslupus/research-buddy) project at the time of the session). If the MAJOR component differs, surface a one-line warning at the top of Turn 1 and pause for the user to confirm before continuing — a MAJOR mismatch means framework semantics may have changed in incompatible ways. If only MINOR differs (doc older than framework), proceed but note "framework newer than doc, refresh recommended" in the change summary. Same-MAJOR-newer-doc or PATCH-only differences proceed silently. The check is informational only on the first session that surfaces it; do not block.

Both flows are exactly **2 turns**, with no confirmation gate between them.

### Turn 1: brief + research

The order below is **not negotiable**. The second-opinion brief is composed and emitted **before** any research is performed in this turn, so that the brief contains only project-given context and is provably uncontaminated by findings the agent has yet to produce. Research follows; output assembles both.

1. **Silent preflight.** Scan [Discarded Alternatives](#discarded-alternatives) for any approach that matches the queue topic; scan [Research Tracker](#research-tracker) and [Session Notes](#session-notes) for prior overlap; identify the [Adopted Rules](#adopted-rules) that constrain the answer space (rules whose decisions cannot be overturned without explicit re-opening). Speak only if blocked.
2. **Take the first row of the [Open Research Queue](#open-research-queue) as the active topic.** Row order = priority. The first row is always the most important pending topic.
3. **Confirm the queue item has an Objective / Key Question.** If missing, define it from context. Do not ask.
4. **Pre-register hypotheses** in the draft session notes. List each hypothesis, the PASS metric (e.g. "≥2 independent Tier-1 sources support, no Tier-1 contradiction"), and the FAIL/REJECT metric (e.g. "Tier-1 silence or contradiction → tag PROPOSED instead of VALIDATED"). Write these *before* consulting sources. Pre-registered hypotheses MAY be referenced by name in the brief composed in step 5 (e.g. "the agent has pre-registered three hypotheses, listed at the end of this brief"), but the agent's *current belief about each hypothesis* MUST NOT be stated in the brief.
5. **Write the second-opinion brief into the outgoing response, wrapped in `<!-- @brief-start -->` and `<!-- @brief-end -->` markers (each on its own line, immediately around the brief), BEFORE invoking any research tool in this turn.** Use the [template](#second-opinion-brief-template), filling its placeholders from: project specification, queue-item objective, source tiers, the relevant DAs surfaced in step 1, the related Research Tracker rows surfaced in step 1, the active constraining rules surfaced in step 1, and the hypotheses pre-registered in step 4. **The brief MUST NOT contain any finding produced by the agent in this turn** — it is project-given context plus the question, nothing more. Writing the brief into the response buffer at this step (before any tool call) is the structural guarantee against both contamination AND omission: contamination because the placeholders cannot be filled with findings that don't yet exist; omission because the brief is already in the outgoing message before research starts, so it cannot be forgotten when assembling the response around the tool's output. **Pre-tool-call self-check.** Before any research tool call in this turn, the response being assembled MUST already contain the brief between `@brief-start` and `@brief-end` markers. If it does not, stop and write the brief first; do not call the tool. Do not edit the brief after research — the rest of the turn appends *beneath* it.
6. **Research** per the project's [Source tiers](#source-tiers). For time-sensitive domains, include year ranges in queries. Build the [synthesis matrix](#synthesis-matrix) any time more than three sources are consulted or sources appear to disagree.
7. **Append the rest of the Turn 1 output beneath the already-emitted brief, in this exact order:**
   - Findings with inline citations `[Title, Author, Year, Venue, DOI/URL]`.
   - Proposed decisions with rationale.
   - Rejected alternatives with reason.
   - Cross-section impact: which sections will be touched on the Turn 2 atomic write.

   The brief from step 5 is already at the top of the message; do not re-emit it, do not re-edit it, and do not move it.
8. **End with the Turn 1 marker** (see [Turn markers](#turn-markers)). Stop and wait.

### Turn 2: vet + validate + atomic write

1. **Read all submitted second opinions.** Label each consistently: `{{Source}}-{{N}}` (Gemini-3, ChatGPT-1, Grok-2, Human-1, PDF-2, Paper-1, …). A second opinion is **read-only**: research the user explicitly submitted. Never generate one. Never role-play as an external source.
2. **Vet each source.** Verify ≥3 cited claims end-to-end — title, author, URL, and that the attributed claim actually appears in the cited source. Report agreements, disagreements, and unverifiable claims. When multiple second opinions share the same error, treat as **one** data point (likely a shared training artifact), not independent confirmation.
3. **Run the cross-section contradiction check and the [compliance validation](#self-validation) pass.** Cross-section check (semantic): (a) does any rule contradict a new decision? (b) does any DA already ban the chosen approach? (c) does any prior session note settle the question with different evidence? Compliance validation (mechanical): anchors intact, version bumped, filename matches, append-only sections preserved, cross-links resolve, queue/tracker IDs unique. Full checklist in [Self-validation](#self-validation). **Compliance validation is a precondition for file delivery.** The agent MUST invoke `research-buddy validate {{file_name}}_v{{version}}-source.md` (or paste a verbatim mental-simulation pass that lists every mechanical check from [Self-validation](#self-validation) and its outcome) and treat the exit code as authoritative. The agent MUST paste the validator's full output (or the simulated checklist) inside the message *before* delivering the file artifact, so the user has visible evidence the gate ran. Any mechanical failure is blocking.
4. **Write atomically — no confirmation gate.** Update all affected sections in **this single message**: [Open Research Queue](#open-research-queue) (remove the completed row, reorder if priorities shifted), [Research Tracker](#research-tracker) (add the new row), [Adopted Rules](#adopted-rules), [Discarded Alternatives](#discarded-alternatives), [Session Notes](#session-notes), [Reasoning Journey](#reasoning-journey), [References](#references), [Changelog](#changelog), and the YAML frontmatter `version`/`date`. Output the new file as `{{file_name}}_v{{version}}-source.md`. Bump version per [Versioning](#versioning).
5. **Pause only on a blocking issue.** Concrete examples: an unresolvable contradiction with two equally-weighted Tier-1 sources; a missing input the user must supply (e.g. a domain expert decision on scope); a queue item with no defined Objective the agent cannot infer from context; **a compliance-validation failure**. Compliance failures are always blocking — the agent MUST NOT deliver the file artifact when validation fails. In any other case, write — do not ask. If blocked, emit the `status=blocked` marker and describe the issue concisely.
6. **Print a concise change summary** wrapped in `<!-- @summary-start -->` and `<!-- @summary-end -->` extraction markers (each on its own line, immediately around the summary). Plain language, ~3–8 lines. Example: *"v1.4 written. Q-016 closed. R-CHUNK-4 revised (markdown-link-depth semantics). 6 DAs added (DA-Q016-1…6). Queue: Q-016 removed; Q-013 is now the top row. Cross-section contradictions: 0 unresolved. Compliance validation: PASS."*
7. **Offer derived files.** End with: "Want the clean view (no framework) or HTML rendering? Default returns the source only." Do not generate them by default.
8. **End with the Turn 2 marker** (see [Turn markers](#turn-markers)).

### Source tiers (categories)

The project defines specific venues per tier in [Project Specification > Source tiers](#source-tiers). The category meanings are framework-fixed:

- **Tier 1** = primary evidence; the only tier that supports `VALIDATED` claims and quantitative thresholds.
- **Tier 2** = official secondary (vendor docs, textbooks, institutional reports).
- **Discovery** = leads only; any claim sourced from Discovery alone is tagged `PROPOSED` until promoted via Tier 1/2 verification.
- **Never** = anonymous content, AI-generated overviews without human authorship, sources without traceable authorship, unverifiable PDFs.

### Editing this file

This Markdown document uses two independent anchor systems:

- **HTML-comment anchors** for agent `str_replace` surgery: `<!-- @anchor: ... -->` and `<!-- @end: ... -->` for sections; `<!-- @rule: R-XXX-N -->`, `<!-- @da: DA-XXX -->`, `<!-- @session: Q-NNN -->` for entries.
- **Auto-generated heading slugs + inline `<a id>` tags** for human/renderer navigation: `[Queue](#open-research-queue)` for sections (auto-slug), `[R-CHUNK-4](#r-chunk-4)` for rules, `[DA-Q016-1](#da-q016-1)` for DAs, `[Q-001](#q-001)` for sessions (each entry has an `<a id>` tag inside its block template).

Both systems coexist; neither modifies the other. Full protocol in [File editing](#file-editing).

**Cross-references in body prose.** When mentioning another section, rule (`R-XXX-N`), DA (`DA-XXX`), session (`Q-NNN`), or the entry by ID anywhere in the document — including session notes, change summaries, reasoning journey, and chat output — render as a clickable link to the target ID. Don't write plain-text references when a stable link target exists. The cost is one pair of brackets and parens; the benefit is browsable navigation throughout the document and chat.

**Turn-marker placement.** Every turn-ending message ends with **exactly two lines**, on their own, in this order, with nothing after them:

```
--- {{banner_text}} ---
<!-- research-buddy:turn={{n|session_zero}}:status={{status}}[:key=value]* -->
```

Detection regex: `<!-- research-buddy:turn=(\d+|session_zero):status=([a-z_]+)(?::[^>]*)? -->`. The full state list is in [Turn markers](#turn-markers).

<!-- @end: framework.core -->

---

<!-- @anchor: framework.reference -->
## Framework (Reference)

<!-- @anchor: framework.reference.editing -->
### File editing

The agent edits this file surgically with `str_replace` calls keyed off anchor strings. The format is designed so that ~90% of edits are scoped to a known anchor plus a unique nearby string.

**Conventions:**

1. **Anchors are sacred.** Never rename, reorder, or delete an HTML-comment anchor (`<!-- @anchor: ... -->`, `<!-- @rule: ... -->`, `<!-- @da: ... -->`, `<!-- @session: ... -->`, `<!-- @end: ... -->`). Add new ones freely.
2. **Every major section has both an `@anchor` opener and an `@end` closer.** Insert new entries immediately before the `@end` marker.
3. **Append-only sections:** Discarded Alternatives, References, Changelog. Never delete entries; mark superseded items with status, not by deletion.
4. **YAML frontmatter** between `---` delimiters at the very top is the structured metadata. Add fields if needed; do not reorder existing ones.
5. **Structured data uses fenced code blocks** with language hints `yaml rule`, `yaml da`, `yaml ref`. The Markdown body for the entry follows the code block.
6. **Tables** for tabular data. Append rows immediately before the section's `@end` marker. Never delete rows from append-only sections; mark superseded by changing the Status column. The Open Research Queue is the exception: completed rows are removed (their finding lives in the Research Tracker).
7. **Raw HTML is allowed for the following purposes only:** anchor comments (`<!-- @... -->`), inline link-target tags (`<a id="..."></a>`), inline SVG illustrations, and inline status chips (`<span class="rb-ok|rb-bad|rb-flag">…</span>`). The full set of allowed presentation primitives lives in [Element catalog](#element-catalog). Use Markdown for prose, tables, headings, lists, quotes, and code; the catalog is a closed list — anything outside it should be expressed as plain Markdown rather than invented locally.
8. **Avoid em-dashes (`—`) in headings.** Slug algorithms handle them inconsistently. Use colons, parentheses, or plain dashes inside headings; em-dashes are fine in body prose.

**Atomic-write semantics.** A "write" is one message containing all changes to all affected sections. Either every applicable update target executes in that message, or the agent reports the blocking issue without writing partial state.

**Cross-section contradiction check.** Before writing, list every section the change touches and confirm: (a) no existing rule contradicts a new decision; (b) no existing DA bans the chosen approach; (c) no prior session note already settled the question with different evidence. If any conflict is found, resolve in the same write or surface for user input via the blocked Turn 2 marker.

**Derived files (clean view + HTML).** A future utility can produce a "research-only" view by stripping everything between `<!-- @anchor: framework.core -->` and `<!-- @end: framework.reference -->`. The remaining file is a self-contained research artifact. Filename convention:

- `{{file_name}}_v{{version}}-source.md` — agent-edited. **Always returned by default at end of Turn 2, conditional on compliance validation passing.**
- `{{file_name}}_v{{version}}.md` — clean view. Returned on user request.
- `{{file_name}}_v{{version}}.html` — HTML rendering. Returned on user request.

If the agent has shell access AND `research-buddy` is installed, it MAY run `research-buddy clean ...` and/or `research-buddy build ...` after the user asks for derived files. Otherwise it prints the build commands verbatim.

<!-- @end: framework.reference.editing -->

<!-- @anchor: framework.reference.elements -->
### Element catalog

The closed list of presentation primitives the agent MAY use. Plain Markdown alone is a valid document; the catalog only enriches the HTML rendering when used. Anything not listed here should be expressed as ordinary prose, lists, or tables — the renderer recognises only what is catalogued.

| ID | Element | Source form |
|---|---|---|
| EL-01 | Headings H1–H4 | `# Title`, `## Tab`, `### Sub`, `#### Sub-sub`. Avoid em-dashes — slug algorithms handle them inconsistently. |
| EL-02 | Inline emphasis | `**bold**`, `*italic*`, `` `code` `` |
| EL-03 | Lists | `- item`, `1. item`, nested with 2-space indent |
| EL-04 | Task lists | `- [ ] todo`, `- [x] done` |
| EL-05 | Links / images | `[text](#anchor)`, `![alt](url)` |
| EL-06 | Code blocks | fenced ` ``` ` with language hint; syntax-highlighted via highlight.js |
| EL-07 | Tables | GFM `\|...\|`; widths auto-derived from content (never tune manually) |
| EL-08 | Horizontal rule | `---` on its own line |
| EL-09 | Inline SVG | `<svg>...</svg>`. Use `currentColor` and theme variables (`var(--text)`, `var(--bg)`, `var(--blue)`, `var(--green)`, `var(--amber)`, `var(--red)`) where colour should follow the active theme; hard-coded hex renders the same in light and dark. |
| EL-10 | Callouts | `> [!KIND]` blockquote. Kinds: `NOTE`, `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`, `LIMITATION`, `HYPOTHESIS`. The last two are research-specific. |
| EL-11 | Verdict badge | ` ```rb-verdict <kind> ` fenced block with prose body. Kinds: `supports`, `contradicts`, `unverifiable`, `silent`. |
| EL-12 | Card grid | ` ```rb-cards ` fenced block; YAML list of `{title, body, icon?}`. |
| EL-13 | Banner | ` ```rb-banner <kind> ` fenced block. Kinds: `usage`, `agnostic`, `cc`. Use sparingly — prefer the `banners` frontmatter for top-of-doc chrome. |
| EL-14 | References anchor | `<!-- @anchor: references -->` (already present on the [References](#references) section); styles the next list as a references list. |
| EL-15 | Entity anchors | `<!-- @rule: ... -->`, `<!-- @da: ... -->`, `<!-- @session: ... -->`. See [File editing](#file-editing) rule 1. |
| EL-16 | Status chips | `<span class="CLASS">…</span>` where CLASS is one of `rb-ok` (green), `rb-bad` (red), `rb-flag` (amber). Readable as plain text in non-HTML viewers. |
| EL-17 | `banners` frontmatter | List of `usage` / `agnostic` / `cc`; rendered above the first tab. |
| EL-18 | `theme_css` frontmatter | Optional path to extra CSS appended after the default stylesheet. |

**Fenced extensions in context.** Plain MD viewers show these as YAML code blocks; the HTML builder renders them rich.

````
```rb-verdict supports
Two Tier-1 sources directly support the claim; no Tier-1 contradiction.
```

```rb-cards
- title: Pre-registration
  body: Hypotheses + PASS/FAIL metrics written before consulting sources.
- title: Vetting
  body: Verify ≥3 cited claims end-to-end before incorporating any second opinion.
```
````

**Algorithmic, no source change.** H3 / H4 are auto-numbered per tab (`1.`, `1.1`, `2.`, `2.1` …). Table column widths are computed from cell content — no header-name keywords, no language-specific heuristics — and tables sharing a structural signature within one document align on a common width vector.

If a presentation need arises that none of the above covers, raise it upstream rather than inventing local syntax — the catalog is the renderer contract.

<!-- @end: framework.reference.elements -->

<!-- @anchor: framework.reference.turns -->
### Turn markers

Standard session:

| State | Banner | Tag |
|---|---|---|
| Turn 1 complete (brief + research printed) | `End of Turn 1 — awaiting second-opinion sources` | `<!-- research-buddy:turn=1:status=awaiting_second_opinions:topic={{Q-NNN}} -->` |
| Turn 2 complete (atomic write succeeded, validation passed) | `End of Turn 2 — version {{version}} written` | `<!-- research-buddy:turn=2:status=complete:topic={{Q-NNN}}:version={{version}}:file={{file_name}}_v{{version}}-source.md -->` |
| Turn 2 blocked (unresolvable contradiction, missing user input, or compliance-validation failure) | `End of Turn 2 — blocked: {{reason}}` | `<!-- research-buddy:turn=2:status=blocked:topic={{Q-NNN}}:reason={{reason_token}} -->` |

Session zero:

| State | Banner | Tag |
|---|---|---|
| Turn 1 complete (welcome + questions printed) | `End of Session Zero Turn 1 — awaiting answers` | `<!-- research-buddy:turn=session_zero:status=awaiting_answers -->` |
| Turn 2 complete (v1.0 written, validation passed) | `End of Session Zero — project initialized as {{file_name}} v1.0` | `<!-- research-buddy:turn=session_zero:status=complete:version=1.0:file={{file_name}}_v1.0-source.md -->` |

**KV value charset.** Each `key=value` pair after `status=` uses lowercase letters, digits, underscores, dots, and dashes. No spaces, no `:`, `=`, `>`, or other special characters. Filenames, version numbers, and `Q-NNN` IDs all fit. `reason` tokens use snake_case (e.g. `tier_1_contradiction`, `missing_user_input`, `validation_failed`).

**Parsing recipe.** Strip the `<!-- ` prefix and ` -->` suffix; the remainder is `:`-separated. The first token is the literal `research-buddy`; subsequent tokens are `key=value` pairs. Substitute `{{version}}`, `{{file_name}}`, `{{Q-NNN}}`, `{{reason}}`, `{{reason_token}}` from frontmatter or context before emitting. Never leave `{{...}}` literals in the emitted tag.

<!-- @end: framework.reference.turns -->

<!-- @anchor: framework.reference.automation-hooks -->
### Automation hooks

The file is designed for script-based automation of the chat workflow. Three extraction points per turn:

1. **Turn-end marker** — the final `<!-- research-buddy:... -->` line. Parseable via the [detection regex above](#turn-markers). Tells the script what state the session is in and which queue topic is active.
2. **Second-opinion brief** (Turn 1 only) — wrapped in `<!-- @brief-start -->` … `<!-- @brief-end -->`. The script extracts the brief verbatim and dispatches to other AI tools.
3. **Change summary** (Turn 2 only) — wrapped in `<!-- @summary-start -->` … `<!-- @summary-end -->`. The script displays this to the user as a changelog notification.

The new file artifact is delivered separately via the chat platform's file-attachment feature. For plain-text-only environments where files cannot be attached, the agent MAY inline the file content wrapped in `<!-- @file-start: {{filename}} -->` and `<!-- @file-end: {{filename}} -->`.

All extraction markers are HTML comments — invisible in rendered Markdown, ignored by Markdown renderers, parseable by any regex-capable script.

<!-- @end: framework.reference.automation-hooks -->

<!-- @anchor: framework.reference.versioning -->
### Versioning

Bump MINOR (1.0 → 1.1 → 1.2) on any content change. Format-only changes do not bump.

**Bump locations** (all in the same atomic write):

1. YAML frontmatter `version` and `date` fields.
2. New entry inserted at the top of [Changelog](#changelog). The first entry in the changelog is implicitly the current one — no separate `current` flag is maintained.
3. Output filename `{{file_name}}_v{{version}}-source.md`.

`research_buddy_version` in the frontmatter records the framework version that wrote the file. Update it on every write to whichever framework version the agent operates under.

<!-- @end: framework.reference.versioning -->

<!-- @anchor: framework.reference.session-zero -->
### Session zero

Two turns, no confirmation between.

**Turn 1: welcome + batched questions.** Print the welcome and all initialization questions in a single message. Do not ask follow-ups.

**Before printing Turn 1, inspect the user's first message and choose a Turn-1 mode.** Three cases (mutually exclusive):

- **(a) Standard Turn 1 — questions.** First message is a generic kickoff ("start a research project", "let's begin", or empty / a bare upload). Print the welcome + five questions verbatim. End with the session-zero Turn 1 marker. Wait for the user's answers, then proceed to Turn 2.
- **(b) Pre-answered Turn 1 — skip to Turn 2.** First message already supplies enough information to fill the five answers (explicitly or by clear inference): project description, domain, deliverable type, timing, and language can all be derived from what the user wrote. Skip the questions entirely. Open with one short line that lists the five values you extracted ("Reading from your message: domain = X, deliverable = Y, timing = Z, language = English. Treating these as the session-zero answers — flag any I got wrong."), then proceed directly to Turn 2 actions (discovery research, structure, queue, atomic write). Do NOT emit the Turn 1 marker — both turns ship in one message under this branch.
- **(c) Research-request-first — session zero with implicit spec, then enqueue.** First message is a research request ("research X for me", "I want to understand Y") rather than a project specification. Treat the request as the implicit project spec: domain and final goal come from the request itself; deliverable type defaults to `document`; timing defaults to `none`; language defaults to `en`. Run Turn 2 actions (discovery, structure, queue, atomic write), and seed the queue with the user's research request as **Q-001** so the next session can research it directly. Do NOT emit the Turn 1 marker.

Modes (b) and (c) are the common shortcuts; mode (a) is the fallback when the message has no usable content. When unsure between (a) and (b), prefer (a) and ask — a one-turn round trip is cheap. Between (b) and (c) the distinction is "is the user describing a project or asking a question?" — a project description goes (b); a single research topic goes (c).

Welcome text (mode (a) only — verbatim):

> Welcome to your first Research Buddy session.
>
> Every session produces a versioned Markdown file — your living research document and the source of truth.
>
> Research is organized in a queue; each topic has a clear objective. Findings are validated against each other; rejected ideas are permanently logged. You can submit research from other AI tools or human experts at any time — I evaluate and integrate or discard. Sessions follow a 2-turn workflow: I research and give you a prompt for others; you provide their results, I evaluate and finalize.
>
> Five questions to set up:

Questions (ask all five at once — mode (a) only):

1. Describe your project: what do you want to build, study, solve, or understand? Include constraints and background you already have.
2. Primary domain (e.g. machine learning, medical research, mechanical engineering, nutrition, mobile app development, financial analysis, chemistry, legal research)?
3. Theory and knowledge only, or must something be delivered or built? If built: software, physical product, document, plan, other?
4. Timeline, deadline, or delivery milestones?
5. What language for this document? (Default: English.)

End with the session-zero Turn 1 marker (mode (a) only).

**Turn 2: discovery + atomic write.** When the user replies:

1. Run brief discovery research on the domain.
2. Choose: (a) section structure for this project — add domain-specific H2 sections after [Project Specification](#project-specification) when useful (examples: `## Theory`, `## Implementation`, `## Evidence`, `## Protocols`, `## Materials`); (b) source tiers with specific venues for the domain; (c) 3–5 initial queue items, each with a defined Objective / Key Question, in priority order; (d) any domain-specific methodology rules.
3. **Run the [Queue insertion protocol](#queue-rules) on each proposed queue item** to set the priority position correctly. (For session zero, all items are new, so the protocol just orders them.)
4. **Write directly. Do not confirm the structure first.** Defaults are correct enough; the user refines them in v1.1+.
5. Fill in the YAML frontmatter: **overwrite `agent_state: needs_session_zero` → `agent_state: ready`** (this flips the state signal so future sessions detect standard-session mode); set `version: "1.0"`, `date`, `file_name`, `title`, `subtitle`, and the `project.*` fields. Populate [Project Specification](#project-specification), seed the [queue](#open-research-queue), add a v1.0 entry to the [changelog](#changelog), add a v1.0 paragraph to the [reasoning journey](#reasoning-journey).
6. **Run compliance validation** before emitting the file (same precondition as standard Turn 2 step 3). On failure, emit the blocked marker and do not deliver.
7. Output `{{file_name}}_v1.0-source.md`. Print the [change summary](#automation-hooks). Offer derived files. End with the session-zero-complete marker.

<!-- @end: framework.reference.session-zero -->

<!-- @anchor: framework.reference.queue-rules -->
### Queue rules

**Row order is priority.** The first row of the queue is always the most important pending topic. To raise an item's priority, move its row up. To lower it, move it down.

**Stable IDs.** Each queue row has a permanent `Q-NNN` ID. The ID does not change when the row is reordered, when other items are merged into it, or when the row moves to the [Research Tracker](#research-tracker). Session Notes and the Tracker reference this ID. The next ID is the highest existing `Q-NNN` + 1, across both the queue AND the tracker (never reuse). Tracker rows MAY also use `T-NNN` IDs for items that originated as tracker entries (project initialization, framework events) and never lived in the queue.

**Insertion protocol.** Whenever a new topic is proposed — by user or agent, at any session step (mid-conversation, end of Turn 1, during Turn 2 atomic write, during session zero, anywhere) — the agent runs this protocol before adding the row:

1. **Compare against every existing queue row.** Read each row's Objective; compare against the new topic.
2. **If any existing row covers the same scope or is closely related** (sub-questions of the same theme, overlapping research surface, same Tier-1 evidence base): **merge** instead of adding. Extend the existing row's Objective to absorb the new question. Keep the existing row's `Q-NNN` ID. Do not add a new row. Note the merge in the [Reasoning Journey](#reasoning-journey) at the next Turn 2 atomic write.
3. **Otherwise, insert at the priority-correct position.** Top if more important than everything pending; in the middle if it slots between existing items; at the bottom if least important. Assign the next available `Q-NNN` ID.

This protocol applies wherever the queue is touched. It is the agent's job to keep the queue free of redundant or near-duplicate items at all times.

**Done items leave the queue.** When a topic is researched (Turn 2 atomic write), remove its row from the queue and add a new row to the [Research Tracker](#research-tracker) with the finding and version. The tracker row retains the original `Q-NNN` ID for traceability.

**Re-queuing.** If a researched topic needs to be revisited (new findings contradict it, requirements changed, inconsistencies surfaced), propose a new queue topic referencing the original `Q-NNN` ID in the Objective. Run the insertion protocol — it may merge into an existing pending row. Keep the original Tracker row as historical record.

**Empty queue.** When all rows are done, ask the user to choose: (1) add new topics; (2) fresh-eyes review (scan the whole project, propose gaps); (3) reopen a specific topic; (4) declare research complete.

<!-- @end: framework.reference.queue-rules -->

<!-- @anchor: framework.reference.brief -->
### Second-opinion brief template

Print this verbatim at the top of Turn 1, wrapped in `<!-- @brief-start -->` and `<!-- @brief-end -->` markers, ready for the user to copy. Replace placeholders with the current topic's specifics; keep the asks and excellence bar intact. No meta-commentary after the brief.

**Composition rule.** This brief is **written into the outgoing response in Turn 1 step 5, before any research tool is invoked in the current turn**. The guarantee is spatial, not just temporal: by the time research starts, the brief is already in the message buffer between `@brief-start` and `@brief-end` markers. This makes both contamination and omission structurally impossible — contamination because the placeholders cannot be filled with findings that do not yet exist, omission because the brief is in the outgoing message before the tool returns and findings get appended. Every placeholder is filled from project-given context (Project Specification, queue-item objective, Source tiers, Adopted Rules, Discarded Alternatives, Research Tracker) — never from this turn's findings. The agent's hypotheses MAY be referenced by name (so the second researcher knows there are pre-registrations) but their *current statuses* MUST NOT appear in the brief, and Turn 1 *findings* MUST NOT appear at all. The point is that the second researcher receives the same context the agent had at the start of the turn — no more, no less — and arrives at conclusions independently. The brief is never re-edited after research; findings are appended beneath it, not folded into it.

**Context-completeness rule.** "Context" includes everything that bounds the answer space and would change the second researcher's strategy if they knew it: relevant rejected alternatives that should not be relitigated; related prior tracker rows that establish what is already settled; active rules that constrain new conclusions. Omitting these forces the second researcher to either duplicate work the project has already done, or propose answers that conflict with already-adopted rules. Both waste the second-opinion round. Fill `{{RELEVANT_DISCARDED_ALTERNATIVES}}`, `{{RELATED_PRIOR_TRACKER_ROWS}}`, and `{{ACTIVE_CONSTRAINING_RULES}}` with the items from preflight, in compact list form (one line per item: ID, one-sentence summary, link or pointer). If a section has no relevant items, write "None." explicitly — do not omit the section.

```text
I am working on a {{PROJECT_AND_BASIC_CHARACTERISTICS}}. I'm trying to decide {{RESEARCH_TOPIC_IN_CONTEXT}}.

I need you to do a deep research that allows you to answer these questions: {{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}.

Your research must be {{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}.

Accepted sources will be: {{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}.
Automatically rejected: {{TIER_REJECT_RULES}}.

Context that bounds the answer space — please respect these unless you have new Tier-1 evidence that overturns them:

Already-rejected approaches (do not re-propose unless you bring new Tier-1 evidence; mark any revisit explicitly):
{{RELEVANT_DISCARDED_ALTERNATIVES}}

Related prior research already settled in this project (use as background; flag only if your findings contradict):
{{RELATED_PRIOR_TRACKER_ROWS}}

Active rules that constrain new conclusions (a recommendation that violates these needs to either narrow itself to fit or argue explicitly for revision):
{{ACTIVE_CONSTRAINING_RULES}}

Pre-registered hypotheses (the agent has these on record; you do not need to align with them — independent answers are the point):
{{PRE_REGISTERED_HYPOTHESES_BY_NAME_ONLY}}

Please cite all claims inline with Title, Author, Year, Venue, DOI/URL in the same sentence as the claim — not at the end and not via links to other parts of the answer. Distinguish what is validated vs. proposed/experimental.
```

<!-- @end: framework.reference.brief -->

<!-- @anchor: framework.reference.synthesis -->
### Synthesis matrix

Required when more than three sources are consulted on the same topic, or any time sources appear to disagree. Always required for quantitative thresholds.

Format: a table where each row is one concrete claim and each column is one Tier-1/2 source. Each cell is `SUPPORTS` / `CONTRADICTS` / `SILENT` / `UNVERIFIABLE`. Adopt only claims with ≥2 independent `SUPPORTS` from Tier-1 sources and zero `CONTRADICTS` from Tier-1 sources.

The matrix lives in the relevant Session Notes block.

<!-- @end: framework.reference.synthesis -->

<!-- @anchor: framework.reference.validation -->
### Self-validation

Before declaring Turn 2 complete, the agent runs a self-validation pass over the new file. Two kinds of checks: **mechanical / compliance** (structural invariants — verifiable deterministically from the file alone) and **semantic** (judgement-based — depend on understanding the content). Mechanical checks are the bulk of validation by count and the cheapest by effort; doing them first catches most write errors before semantic review even starts.

The `research-buddy validate <file>` command runs all mechanical checks deterministically. When shell access AND `research-buddy` are available, the agent MUST invoke it and treat its exit code as authoritative. When shell access is unavailable, the agent MUST instead paste a mental-simulation checklist that names every mechanical check below and gives each a PASS/FAIL outcome — no shortcuts, no "all good" summaries. **Compliance validation passing is a precondition for delivering the file artifact** (Turn 2 step 3); the validator output (real or simulated) MUST appear in the Turn 2 message before the file. A failing validation is a blocking issue per Turn 2 step 5; the agent emits the `status=blocked:reason=validation_failed` marker and does not deliver the file.

**Self-install when shell access exists.** If the agent has shell access but `research-buddy` is not on PATH (`research-buddy --version` exits non-zero, or `which research-buddy` returns nothing), install it from PyPI first: `pip install research-buddy` (or `pip install --user research-buddy` when the environment is non-writable; `uv pip install research-buddy` inside a uv project; `pipx install research-buddy` to isolate it). The package is published at <https://pypi.org/project/research-buddy/>; source and issue tracker at <https://github.com/nuncaeslupus/research-buddy>. Real validation is strictly better than mental simulation — a one-time `pip install` removes the entire class of "simulated PASS, actual FAIL" mistakes. After install, verify with `research-buddy --version` and proceed. Skip the install step only when (a) no shell access, (b) install fails (sandbox / network / permission) — in which case fall back to mental simulation and note the install failure in the Turn 2 change summary so the user can install it themselves.

Validation runs at the end of Turn 2 (against the file the agent has just composed), not at the start of Turn 1 (where the input file is presumed already-valid from the prior session's exit).

**Mechanical checks** (script-automatable):

- YAML frontmatter parses; required fields present (`doc_format_version`, `version`, `date`, `file_name`, `title`, `language.code`, `project.domain`).
- Every `<!-- @anchor: X -->` has a matching `<!-- @end: X -->` and vice versa. No orphan markers.
- Every `<!-- @rule: R-XXX-N -->` is followed by an `<a id="r-xxx-n"></a>` line whose ID equals the rule ID lowercased. Same for `@da` / `<a id="da-xxx">` and `@session` / `<a id="q-nnn">`.
- All cross-links `[text](#anchor)` resolve to a real heading slug or `<a id>` tag in the document.
- The first changelog entry's version equals the frontmatter `version`. The output filename equals `{file_name}_v{version}-source.md`.
- Every anchor present in the prior version is still present in the new file (no renames, no deletes). New anchors are fine.
- Append-only invariant holds for Discarded Alternatives, References, and Changelog (no entries removed since prior version).
- Every queue row has a unique `Q-NNN` ID; every tracker row has a unique `T-NNN` or `Q-NNN` ID; no ID appears in both queue and tracker simultaneously.
- The Turn 1 second-opinion brief (when present) is wrapped in `<!-- @brief-start -->` / `<!-- @brief-end -->`. The Turn 2 change summary (when present) is wrapped in `<!-- @summary-start -->` / `<!-- @summary-end -->`. The end-of-turn marker is the final two lines.
- No plain-text reference to `R-XXX-N`, `DA-XXX`, or `Q-NNN` appears outside a Markdown link `[...](#...)`, an HTML comment, or a fenced code block.

**Semantic checks** (always agent-driven; see [Common failure modes](#common-failure-modes) for the full inventory): source-tier discipline, cross-section contradiction check, no Discarded Alternative re-proposed, second opinions vetted before incorporation, findings compared against already-researched topics, queue insertion protocol applied, `VALIDATED` claims meet the project's validation gate, no fabricated second opinions, brief uncontaminated by Turn 1 findings.

<!-- @end: framework.reference.validation -->

<!-- @anchor: framework.reference.failure-modes -->
### Common failure modes

Each entry is tagged `[mechanical]` (a script can detect it), `[semantic]` (the agent must reason about it), or `[hybrid]` (mechanical detection is partial; semantic review for the rest).

- `[mechanical]` **Producing the session's output as a chat response, artifact, summary, or any form other than the `{{file_name}}_v{{version}}-source.md` file.** The deliverable is the file — a downloadable, validated, versioned Markdown source document. A chat-only response means the session is not complete, regardless of how much research or reasoning it contains. The Turn 2 atomic write is what produces the file; if the agent ends Turn 2 without writing the file, the only valid output state is the `status=blocked` marker with a concrete blocking reason. Catches the meta-failure where the agent treats the user's "research X" request as a chat prompt instead of a session-zero or standard-session protocol invocation.
- `[mechanical]` Renaming or deleting an anchor — breaks `str_replace` targeting from this and future sessions.
- `[mechanical]` Skipping session zero when the frontmatter still has `null` placeholders.
- `[semantic]` Using Discovery or Never-tier sources as primary evidence.
- `[semantic]` Updating a section that wasn't actually affected by the change.
- `[mechanical]` Closing a session without bumping the version, filename, and changelog.
- `[semantic]` Adopting a decision without running the cross-section contradiction check.
- `[hybrid]` Re-proposing an approach already in Discarded Alternatives. Mechanical: exact `DA-XXX` ID match. Semantic: paraphrased re-proposals.
- `[semantic]` Incorporating second-opinion claims before vetting them.
- `[semantic]` Inventing second opinions, fictional experts, or role-playing external sources.
- `[semantic]` Treating repeated errors across multiple second opinions as independent confirmation.
- `[semantic]` Marking a result `VALIDATED` before the project's validation gate is met.
- `[semantic]` Failing to compare new findings against already-researched topics.
- `[hybrid]` Language drift — content not in the file's declared `language.code`. Mechanical: language-detection library on prose. Semantic: code-switching, technical terms, proper nouns.
- `[semantic]` Pausing for confirmation on Turn 2 when no blocking issue actually exists. The default is **write** (after compliance validation passes).
- `[mechanical]` **Brief composed in reasoning but never written into the response, OR buried below findings, OR missing the `@brief-start` / `@brief-end` markers.** This is the most common form of brief failure for tool-using agents: the brief is "drafted" mentally as input to a research tool call, then forgotten when assembling the response around the tool's output. Saying "I composed the brief before research" is operationally meaningless if it never reaches the message buffer. The structural fix is in Turn 1 step 5: the brief MUST be written into the outgoing response (with `@brief-start` / `@brief-end` markers) BEFORE any research tool is invoked, not just composed in working memory. If the response buffer does not contain the brief at the moment a research tool is called, the agent has already failed step 5 — stop, write the brief, then call the tool. The brief must remain at the top of the message; findings append beneath it.
- `[mechanical]` Omitting the `@summary-start` / `@summary-end` markers around the Turn 2 change summary — same automation reason.
- `[semantic]` Adding a queue item without running the [insertion protocol](#queue-rules) — leads to redundant or near-duplicate rows.
- `[mechanical]` Leaving completed rows in the Open Research Queue. Done rows move to Research Tracker; the queue holds only OPEN items.
- `[semantic]` Generating clean view or HTML by default at end of Turn 2 — wait for the user to ask, to keep context lean.
- `[mechanical]` Writing plain-text references to rules / DAs / sessions when a stable link target exists. Always link.
- `[hybrid]` **Forward-linking to a not-yet-researched queue item as if it were a stable target.** Pending queue rows (rows still in [Open Research Queue](#open-research-queue), not yet promoted to [Research Tracker](#research-tracker) or [Session Notes](#session-notes)) **do not have `<a id>` link targets** — their `Q-NNN` ID is allocated, but the linkable anchor `<a id="q-nnn">` only exists once the session block is written. The "always link when a stable target exists" rule therefore *excludes* pending queue items: reference them as **plain text `Q-NNN`** (no brackets, no parens), not as a Markdown link. Promotion to a Tracker row in Turn 2 atomic write is what creates the link target; from that write forward, all references to that ID render as links. Mechanical detection: `validate` flags any `[Q-NNN](#q-nnn)` whose target `<a id="q-nnn">` is absent.
- `[semantic]` **Composing the second-opinion brief after research** — even if every placeholder is filled with project-given context, the agent's choice of how to phrase the questions, which DAs to surface, and which rules to flag is biased by what they've just found. The structural fix is to write the brief into the outgoing response in Turn 1 step 5 (before any research tool is invoked) and never re-edit it — findings append beneath it. (Hybrid: a script can detect a brief that mentions specific Tier-1 source titles, statuses like `VALIDATED`/`REJECTED`, or claim verdicts that wouldn't be available before research; semantic review catches subtler leakage.)
- `[semantic]` **Brief omits relevant rejected alternatives, prior tracker rows, or active constraining rules.** The second researcher then either duplicates work or proposes a previously-rejected approach. The brief template's three context slots are mandatory; "None." is an acceptable value if preflight surfaced nothing relevant, but the slots must not be silently dropped.
- `[mechanical]` **Delivering the file artifact without compliance validation passing — or without the validator output pasted in the Turn 2 message.** Turn 2 step 3 gates step 4: the validator output (or the mental-simulation checklist) MUST be present in the message *before* the file. A failing validation triggers `status=blocked:reason=validation_failed`, not delivery.
- `[hybrid]` **Brief context slot says "None." but the corresponding section has live entries.** If [Discarded Alternatives](#discarded-alternatives) holds DAs but `{{RELEVANT_DISCARDED_ALTERNATIVES}}` is filled with "None.", the agent skipped preflight; same for `{{RELATED_PRIOR_TRACKER_ROWS}}` vs the tracker, and `{{ACTIVE_CONSTRAINING_RULES}}` vs Adopted Rules. Mechanical: a script can detect "None." in a brief slot whose source section is non-empty and emit a candidate-mismatch warning; semantic: the agent decides whether the live entries are actually *relevant* to this turn's topic ("None relevant." with reasoning is fine; bare "None." plus a non-empty section is a red flag).

<!-- @end: framework.reference.failure-modes -->

<!-- @anchor: framework.reference.templates -->
### Templates

Copy-paste blocks for the three entry-based sections — [Adopted Rules](#adopted-rules), [Discarded Alternatives](#discarded-alternatives), [Session Notes](#session-notes). The templates live here, outside the user sections, so the rule "append immediately before `@end`" is unambiguous: every str_replace target inside `## Adopted Rules` / `## Discarded Alternatives` / `## Session Notes` is real content, never a template fence to confuse with content.

**When adding a new rule** — paste this into [Adopted Rules](#adopted-rules) immediately before its `<!-- @end: rules -->` marker. Replace `R-EXAMPLE-1` with the real rule ID (e.g. `R-CHUNK-4`) and lowercase it for the `<a id>` value:

````
<!-- @rule: R-EXAMPLE-1 -->
<a id="r-example-1"></a>

```yaml rule
id: R-EXAMPLE-1
status: VALIDATED
force: MUST
tags: [tag1, tag2]
adopted_in: "v1.1"
last_verified: "YYYY-MM-DD"
evidence:
  tier1:
    - "{{Title}}, {{Author}}, {{Year}}, {{Venue}}, {{URL}}"
  tier2: []
# Optional: contradictions, supersedes, superseded_by
```

**R-EXAMPLE-1 [tag1] [tag2] VALIDATED MUST.** Imperative-form rule body in one or two short paragraphs. Cite Tier-1 sources inline. Avoid `MUST` / `ALWAYS` / `NEVER` shouting unless the rule truly admits no exception; explain reasoning instead.
````

**When adding a new discarded alternative** — paste this into [Discarded Alternatives](#discarded-alternatives) immediately before its `<!-- @end: discarded -->` marker. Replace `DA-EXAMPLE-1` with the real ID (e.g. `DA-Q016-3`) and lowercase it for the `<a id>` value:

```
<!-- @da: DA-EXAMPLE-1 -->
<a id="da-example-1"></a>

**DA-EXAMPLE-1.** {{Short title of the rejected approach.}} Rationale: {{why it was rejected, with Tier-1 anchor where applicable}}. Rejected in: v1.X. Superseded by: {{R-XXX-N if applicable, else "—"}}.
```

**When adding a new session note** — paste this into [Session Notes](#session-notes) immediately before its `<!-- @end: sessions -->` marker. Replace `Q-001` with the queue/tracker ID that just completed and lowercase it for the `<a id>` value:

````
<!-- @session: Q-001 -->
<a id="q-001"></a>

### Q-001: {{topic}} ({{date}})

**Pre-registration.** Hypotheses, PASS metric, FAIL/REJECT metric — written before consulting sources.

**Sources consulted.**

| Source | Tier | Verification | Disposition |
|---|---|---|---|
| ... | ... | ... | ... |

**Decisions adopted.** Bulleted list with rule IDs (linked: `[R-XXX-N](#r-xxx-n)`).

**Rejected claims.** Bulleted list with DA IDs (linked: `[DA-XXX](#da-xxx)`).

**Second-opinion evaluation.** Per submitted source, by label: main claims; ≥3-source verification; agreements / disagreements / unverifiables; incorporate-or-discard with rationale.
````

The three blocks above sit inside fenced code so they render as literal templates in any Markdown viewer and are skipped by the validator's anchor scan (fenced lines are not parsed as live anchors). Copy the *contents* of the fence — not the outer ```` or ``` fence delimiters themselves — when appending into a user section.

<!-- @end: framework.reference.templates -->

<!-- @end: framework.reference -->

---

<!-- @anchor: project -->
## Project Specification

<!-- Filled in session zero. Modifications to project-specific values go here. Do not modify the Framework sections. -->

### Domain

- **Domain:** {{project.domain}}
- **Deliverable type:** {{project.deliverable_type}}
- **Final goal:** {{project.final_goal}}
- **Timing:** {{project.timing}}
- **Validation gate:** {{project.validation_gate}}

<!-- @anchor: project.tiers -->
### Source tiers

Specific venues per tier for this project. Examples by domain: ML → arXiv / NeurIPS / ICML / EMNLP / ACL / ICLR (T1). Medical → PubMed, Cochrane Reviews, NEJM, Lancet (T1). Patents → USPTO / EPO / WIPO (T1). Finance → JF, JFE, RFS (T1). Legal → primary case law and statutes (T1). Software / coding → official vendor docs and source repos (T1).

- **Tier 1:** {{project.source_tiers.tier_1}}
- **Tier 2:** {{project.source_tiers.tier_2}}
- **Discovery:** {{project.source_tiers.discovery}}
- **Never:** Anonymous content, AI-generated overviews without human authorship, unverifiable PDFs, sources without traceable authorship.

<!-- @end: project.tiers -->

<!-- @anchor: project.rules -->
### Domain rules

Methodology rules specific to this domain, filled in session zero. Examples: ML → "pre-register PASS/FAIL criteria before any experiment"; medical → "document conflicts of interest"; legal → "cite jurisdiction"; physical product → "document regulatory requirements"; software → "verify against the canonical reference implementation, not just the docs".

{{project.domain_rules}}

<!-- @end: project.rules -->

<!-- @end: project -->

---

<!-- @anchor: queue -->
## Open Research Queue

Pending topics in priority order. **Top row = next session's topic.** Done items leave the queue and move to the [Research Tracker](#research-tracker). New items pass through the [insertion protocol](#queue-rules).

| ID | Topic | Objective / Key Question |
|----|-------|--------------------------|
| Q-001 | {{queue.row1.topic}} | {{queue.row1.objective}} |

<!-- @example-rows: filled in session zero, replace the templated row above and these examples with real queue items. Examples illustrate good Objective shape: a concrete *question* the agent can answer in one session, not an open-ended task. -->

<!--
Example shapes (delete after session zero):

| Q-EX1 | Token-efficient skill structure | What is the *minimum* SKILL.md anatomy (sections, frontmatter fields) that Tier-1 sources agree on, and what is the per-skill token budget that keeps a multi-skill index loadable in a 200K-token context? |
| Q-EX2 | Skill discovery contract | Which discovery mechanisms (filesystem scan, name match, frontmatter description) are documented as canonical for Claude Code, and which are observed-but-undocumented? |
-->

<!-- @end: queue -->

---

<!-- @anchor: tracker -->
## Research Tracker

Living status board — one row per researched topic. Rows are appended as topics complete; never deleted.

| ID | Topic | Decision / Finding | Version |
|----|-------|--------------------|---------| 
| T-000 | Project initialization | Structure defined; tiers, queue, and rules populated. | v1.0 |

<!-- @end: tracker -->

---

<!-- @anchor: rules -->
## Adopted Rules

Rules adopted during research. Each rule has a stable ID of the form `R-{{TOPIC}}-{{N}}` and an inline `<a id>` link target so other text can cross-link to it.

**Status lifecycle:** `PROPOSED` (single Tier-1 or Tier-2/Discovery support) → `VALIDATED` (≥2 independent Tier-1 sources, no Tier-1 contradiction) → `SUPERSEDED` (replaced by a newer rule; cross-link via `superseded_by`).

**Force keywords (RFC 2119 / 8174):** `MUST` / `MUST NOT` / `SHOULD` / `SHOULD NOT` / `MAY`. Force is orthogonal to status — a `SHOULD` rule may be `VALIDATED`; a `MUST` rule may be `PROPOSED`.

**Block format:** see [Templates → new rule](#templates) for the copy-paste block. Append new rule blocks immediately above the `<!-- @end: rules -->` marker below — the section between this paragraph and that marker is content-only, no template fence.

<!-- @end: rules -->

---

<!-- @anchor: discarded -->
## Discarded Alternatives

Permanent record of rejected approaches. Never re-propose items listed here. Each entry has a stable `DA-{{TOPIC}}-{{N}}` label and an inline `<a id>` link target. Always check this section before proposing any approach.

**Block format:** see [Templates → new discarded alternative](#templates) for the copy-paste block. Append new DA blocks immediately above the `<!-- @end: discarded -->` marker below — the section between this paragraph and that marker is content-only, no template fence.

<!-- @end: discarded -->

---

<!-- @anchor: sessions -->
## Session Notes

One subsection per researched topic. Each contains pre-registration, sources consulted, decisions adopted, rejected claims, and second-opinion evaluation. Each block has an inline `<a id>` link target for cross-linking from elsewhere in the document.

**Block format:** see [Templates → new session note](#templates) for the copy-paste block. Append new session blocks immediately above the `<!-- @end: sessions -->` marker below — the section between this paragraph and that marker is content-only, no template fence.

<!-- @end: sessions -->

---

<!-- @anchor: journey -->
## Reasoning Journey

Chronological narrative of how the project arrived at its current state. One short paragraph per significant version. Reference rules / DAs / sessions by their linked IDs.

**v1.0 — {{date}}.** {{Why this project exists, what it aims to deliver, why this initial structure.}}

<!-- @end: journey -->

---

<!-- @anchor: references -->
## References

All sources cited across research, descending version order. Each entry: Title, Author(s), Year, Venue, URL/DOI. Verify end-to-end before listing.

### v1.0 — {{date}}

- Research Buddy template initialized. Project setup completed in session zero.

<!-- @end: references -->

---

<!-- @anchor: changelog -->
## Changelog

Newest first. The first entry is implicitly the current version. Each entry: decisions adopted, rejected alternatives, contradiction-check result, second opinions reviewed (by label), sources used. Reference rules / DAs / sessions by their linked IDs.

### v1.0: Project initialized — {{date}}

{{What was set up: domain, tiers, initial queue, section structure, domain rules.}}

<!-- @end: changelog -->
