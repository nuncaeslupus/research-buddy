---
format_version: 2
research_buddy_version: "1.5.0"
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
ui_strings:
  status_open: OPEN
  status_done: "✦ Researched"
  status_wip: "IN PROGRESS"
---

<!-- @anchor: title -->
# {{title}} — Research Document

**Format:** Research Buddy v2 (Markdown) · **Version:** {{version}} · **Updated:** {{date}}

**This file is canonical.** Three derived views are available on request:

- `{{file_name}}_v{{version}}-source.md` — the current file, as-is. This is the master; all other views derive from it.
- `{{file_name}}_v{{version}}.md` — clean view. Generated on demand. Research content only, no framework.
- `{{file_name}}_v{{version}}.html` — HTML rendering. Generated on demand.

> **Agent: read [Framework (Core)](#framework-core) before any other action. Read [Framework (Reference)](#framework-reference) once per session. Both are short. Both are required reading.**

<!-- @end: title -->

---

<!-- @anchor: framework.core -->
## Framework (Core)

Research Buddy is a structured AI research collaborator that uses this single Markdown file as shared memory and a living reference. Read the entire file before acting.

### Before your first turn

1. **Read the YAML frontmatter** at the top of this file. It contains the project state.
2. **Read [Framework (Reference)](#framework-reference)** — once, at the start of each session. It is short.
3. **Check the `project.domain` field** in the YAML frontmatter.
   - If `project.domain` is `null` → run **session zero** (project initialization). See [Session zero](#session-zero) for the full flow.
   - Otherwise → run **standard session** (research one queue topic at a time).

### Turn 1: research + brief

1. **Silent preflight.** Scan [Discarded Alternatives](#discarded-alternatives) for any approach that matches the queue topic; scan [Research Tracker](#research-tracker) and [Session Notes](#session-notes) for prior overlap. Speak only if blocked.
2. **Take the first row of the [Open Research Queue](#open-research-queue) as the active topic.** Row order = priority. The first row is always the most important pending topic.
3. **Confirm the queue item has an Objective / Key Question.** If missing, define it from context. Do not ask.
4. **Pre-register hypotheses** in the draft session notes. List each hypothesis, the PASS metric (e.g. "≥2 independent Tier-1 sources support, no Tier-1 contradiction"), and the FAIL/REJECT metric (e.g. "Tier-1 silence or contradiction → tag PROPOSED instead of VALIDATED"). Write these *before* consulting sources.
5. **Research** per the project's [Source tiers](#source-tiers). For time-sensitive domains, include year ranges in queries. Build the [synthesis matrix](#synthesis-matrix) any time more than three sources are consulted or sources appear to disagree.
6. **Output one message in this exact order:**
   - The **second-opinion brief** at the very top, wrapped in `<!-- @brief-start -->` and `<!-- @brief-end -->` extraction markers (each on its own line, immediately around the brief). Verbatim from the [template](#second-opinion-brief-template), with placeholders filled — ready for the user to copy into other AI tools.
   - Findings with inline citations `[Title, Author, Year, Venue, DOI/URL]`.
   - Proposed decisions with rationale.
   - Rejected alternatives with reason.
   - Cross-section impact: which sections will be touched on the Turn 2 atomic write.
7. **End with the Turn 1 marker** (see [Turn markers](#turn-markers)). Stop and wait.

### Turn 2: vet + atomic write

1. **Read all submitted second opinions.** Label each consistently: `{{Source}}-{{N}}` (Gemini-3, ChatGPT-1, Grok-2, Human-1, PDF-2, Paper-1, …). A second opinion is **read-only**: research the user explicitly submitted. Never generate one. Never role-play as an external source.
2. **Vet each source.** Verify ≥3 cited claims end-to-end — title, author, URL, and that the attributed claim actually appears in the cited source. Report agreements, disagreements, and unverifiable claims. When multiple second opinions share the same error, treat as **one** data point (likely a shared training artifact), not independent confirmation.
3. **Run the cross-section contradiction check and the mechanical self-validation pass.** Cross-section check (semantic): (a) does any rule contradict a new decision? (b) does any DA already ban the chosen approach? (c) does any prior session note settle the question with different evidence? Mechanical self-validation: anchors intact, version bumped, filename matches, append-only sections preserved, cross-links resolve, queue/tracker IDs unique. Full checklist in [Self-validation](#self-validation). Any mechanical failure is blocking.
4. **Write atomically — no confirmation gate.** Update all affected sections in **this single message**: [Open Research Queue](#open-research-queue) (remove the completed row, reorder if priorities shifted), [Research Tracker](#research-tracker) (add the new row), [Adopted Rules](#adopted-rules), [Discarded Alternatives](#discarded-alternatives), [Session Notes](#session-notes), [Reasoning Journey](#reasoning-journey), [References](#references), [Changelog](#changelog), and the YAML frontmatter `version`/`date`. Output the new file as `{{file_name}}_v{{version}}-source.md`. Bump version per [Versioning](#versioning).
5. **Pause only on a blocking issue.** Concrete examples: an unresolvable contradiction with two equally-weighted Tier-1 sources; a missing input the user must supply (e.g. a domain expert decision on scope); a queue item with no defined Objective the agent cannot infer from context. In any other case, write — do not ask. If blocked, emit the `status=blocked` marker and describe the issue concisely.
6. **Print a concise change summary** wrapped in `<!-- @summary-start -->` and `<!-- @summary-end -->` extraction markers (each on its own line, immediately around the summary). Plain language, ~3–8 lines. Example: *"v1.4 written. Q-016 closed. R-CHUNK-4 revised (markdown-link-depth semantics). 6 DAs added (DA-Q016-1…6). Queue: Q-016 removed; Q-013 is now the top row. Cross-section contradictions: 0 unresolved."*
7. **Offer derived files.** End with: "Want the clean view (no framework) or HTML rendering? Default returns the source only." Do not generate them by default.
8. **End with the Turn 2 marker** (see [Turn markers](#turn-markers)).

### Source tiers (categories)

The project defines specific venues per tier in [Project Specification > Source tiers](#source-tiers). The category meanings are framework-fixed:

- **Tier 1** = highest evidence bar. Peer-reviewed venues or primary-source documents (academic papers, official datasets, government reports, regulatory filings, court decisions, canonical source code, archived measurements).
- **Tier 2** = secondary: industry blogs by recognized experts, books with citations, technical documentation written by domain practitioners.
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

Detection regex: `<!-- research-buddy:turn=(\d+|session_zero):status=([a-z_]+)(?:[^>]*)? -->`. The full state list is in [Turn markers](#turn-markers).

<!-- @end: framework.core -->

---

<!-- @anchor: framework.reference -->
## Framework (Reference)

<!-- @anchor: framework.reference.editing -->
### File editing

The agent edits this file surgically with `str_replace` calls keyed off anchor strings. The format is designed so that ~90% of edits are scoped to a known anchor plus a unique nearby string.

1. **Each major section** (Project Specification, Open Research Queue, Research Tracker, Adopted Rules, etc.) is bounded by `<!-- @anchor: section_name -->` and `<!-- @end: section_name -->`.
2. **Each rule, DA, and session block** has a unique `<!-- @rule: R-XXX-N -->`, `<!-- @da: DA-XXX -->`, or `<!-- @session: Q-NNN -->` comment.
3. **To edit a section,** use a `str_replace` keyed off the surrounding anchor tags. Example: replace text between `<!-- @anchor: queue -->` and `<!-- @end: queue -->`.
4. **To add a new rule, DA, or session,** append at the anchor's position, or insert after the preceding entry.
5. **Markdown table rows use pipes `|`** and dashes `--`. Headers and separator rows follow standard Markdown. Do not use plain text table format.
6. **Inline `<a id>` tags** (e.g., `<a id="r-example-1"></a>`) act as link targets. Place them immediately after the heading or at the start of a block. Lowercase the ID for the href.
7. **Raw HTML is allowed only for two purposes:** anchor comments (`<!-- @... -->`) and inline link-target tags (`<a id="..."></a>`). Use Markdown for everything else (tables, headings, lists, quotes, code).
8. **Avoid em-dashes (`—`) in headings.** Slug algorithms handle them inconsistently. Use colons, parentheses, or plain dashes inside headings; em-dashes are fine in body prose.

**Atomic-write semantics.** A "write" is one message containing all changes to all affected sections. Either every applicable update target executes in that message, or the agent reports the blocking issue without writing partial state.

**Cross-section contradiction check.** Before writing, list every section the change touches and confirm: (a) no existing rule contradicts a new decision; (b) no existing DA bans the chosen approach; (c) no prior session note already settled the question with different evidence. If any conflict is found, resolve in the same write or surface for user input via the blocked Turn 2 marker.

**Derived files (clean view + HTML).** A future utility can produce a "research-only" view by stripping everything between `<!-- @anchor: framework.core -->` and `<!-- @end: framework.reference -->`. The remaining file is a self-contained research artifact. Filename convention:

- `{{file_name}}_v{{version}}-source.md` — agent-edited. **Always returned by default at end of Turn 2.**
- `{{file_name}}_v{{version}}.md` — clean view. Returned on user request.
- `{{file_name}}_v{{version}}.html` — HTML rendering. Returned on user request.

If the agent has shell access AND `research-buddy` ≥ 2.0 is installed, it MAY run `research-buddy clean ...` and/or `research-buddy build ...` after the user asks for derived files. Otherwise it prints the build commands verbatim.

<!-- @end: framework.reference.editing -->

<!-- @anchor: framework.reference.turns -->
### Turn markers

Standard session:

| State | Banner | Tag |
|---|---|---|
| Turn 1 complete (research + brief printed) | `End of Turn 1 — awaiting second-opinion sources` | `<!-- research-buddy:turn=1:status=awaiting_second_opinions:topic={{Q-NNN}} -->` |
| Turn 2 complete (atomic write succeeded) | `End of Turn 2 — version {{version}} written` | `<!-- research-buddy:turn=2:status=complete:topic={{Q-NNN}}:version={{version}}:file={{file_name}}_v{{version}}-source.md -->` |
| Turn 2 blocked (unresolvable contradiction or missing user input) | `End of Turn 2 — blocked: {{reason}}` | `<!-- research-buddy:turn=2:status=blocked:topic={{Q-NNN}}:reason={{reason_token}} -->` |

Session zero:

| State | Banner | Tag |
|---|---|---|
| Turn 1 complete (welcome + questions printed) | `End of Session Zero Turn 1 — awaiting answers` | `<!-- research-buddy:turn=session_zero:status=awaiting_answers -->` |
| Turn 2 complete (v1.0 written) | `End of Session Zero — project initialized as {{file_name}} v1.0` | `<!-- research-buddy:turn=session_zero:status=complete:version=1.0:file={{file_name}}_v1.0-source.md -->` |

**KV value charset.** Each `key=value` pair after `status=` uses lowercase letters, digits, underscores, dots, and dashes. No spaces, no `:`, `=`, `>`, or other special characters. Filenames, version numbers, and `Q-NNN` IDs all fit. `reason` tokens use snake_case (e.g. `tier1_contradiction`, `missing_user_input`).

**Parsing recipe.** Strip the `<!-- ` prefix and ` -->` suffix; the remainder is `:`-separated. The first token is the literal `research-buddy`; subsequent tokens are `key=value` pairs. Substitute `{{version}}`, `{{file_name}}`, `{{Q-NNN}}`, `{{reason}}`, `{{reason_token}}` from frontmatter or context before emitting. Never leave `{{...}}` literals in the emitted tag.

<!-- @end: framework.reference.turns -->

<!-- @anchor: framework.reference.automation-hooks -->
### Automation hooks

The file is designed for script-based automation of the chat workflow. Three extraction points per turn:

1. **Turn marker** (end of every message) — wrapped in `<!-- research-buddy:turn=... -->`. The script extracts it to determine session state.
2. **Second-opinion brief** (Turn 1 only) — wrapped in `<!-- @brief-start -->` … `<!-- @brief-end -->`. The script extracts the brief verbatim and dispatches to other AI tools.
3. **Change summary** (Turn 2 only) — wrapped in `<!-- @summary-start -->` … `<!-- @summary-end -->`. The script displays this to the user as a changelog notification.

The new file artifact is delivered separately via the chat platform's file-attachment feature. For plain-text-only environments where files cannot be attached, the agent MAY inline the file content wrapped in `<!-- @file-start: {{filename}} -->` and `<!-- @file-end: {{filename}} -->`.

All extraction markers are HTML comments — invisible in rendered Markdown, ignored by Markdown renderers, parseable by any regex-capable script.

<!-- @end: framework.reference.automation-hooks -->

<!-- @anchor: framework.reference.versioning -->
### Versioning

Bump MINOR (1.0 → 1.1 → 1.2) on any content change. Format-only changes do not bump.

1. Frontmatter `version` field changes (e.g. `"1.0"` → `"1.1"`). Update the field value.
2. New entry inserted at the top of [Changelog](#changelog). The first entry in the changelog is implicitly the current one — no separate `current` flag is maintained.
3. Output filename `{{file_name}}_v{{version}}-source.md`.

`research_buddy_version` in the frontmatter records the framework version that wrote the file. Update it on every write to whichever framework version the agent operates under.

<!-- @end: framework.reference.versioning -->

<!-- @anchor: framework.reference.session-zero -->
### Session zero

Two turns, no confirmation between.

**Turn 1: welcome + batched questions.** Print the welcome and all initialization questions in a single message. Do not ask follow-ups.

Welcome (verbatim):

> Welcome to your first Research Buddy session.
>
> Every session produces a versioned Markdown file — your living research document and the source of truth.
>
> The framework will guide you through two structured turns. You will submit research topics. I'll gather the best evidence, vet external sources, and build a versioned artifact that grows throughout the project.

Questions (ask all five at once):

1. **Project title?** (Short title or code name.)
2. **Domain?** (One sentence describing the project — what it's about, what problem it solves.)
3. **Deliverable type?** One of: theory | software | physical_product | document | plan | other.
4. Timeline, deadline, or delivery milestones?
5. What language for this document? (Default: English.)

End with the session-zero Turn 1 marker.

**Turn 2: discovery + atomic write.** When the user replies:

1. **Fill in the YAML frontmatter** with the user's answers.
2. **Run the [queue insertion protocol](#queue-rules)** on any initial research topics the user provides (or surface them as discovery questions if needed).
3. **Run the cross-section contradiction check and the mechanical self-validation pass.** Cross-section check (semantic): (a) does any rule contradict a new decision? (b) does any DA already ban the chosen approach? (c) does any prior session note settle the question with different evidence? Mechanical self-validation: anchors intact, version bumped, filename matches, append-only sections preserved, cross-links resolve, queue/tracker IDs unique. Full checklist in [Self-validation](#self-validation). Any mechanical failure is blocking.
4. **Write directly. Do not confirm the structure first.** Defaults are correct enough; the user refines them in v1.1+.
5. Fill in the YAML frontmatter (`version: "1.0"`, `date`, `file_name`, `title`, `subtitle`, `project.*`), populate [Project Specification](#project-specification), seed the [queue](#open-research-queue), add a v1.0 entry to the [changelog](#changelog), add a v1.0 paragraph to the [reasoning journey](#reasoning-journey).
6. Output `{{file_name}}_v1.0-source.md`. Print the [change summary](#automation-hooks). Offer derived files. End with the session-zero-complete marker.

<!-- @end: framework.reference.session-zero -->

<!-- @anchor: framework.reference.queue-rules -->
### Queue rules

**Row order is priority.** The first row of the queue is always the most important pending topic. To raise an item's priority, move its row up. To lower it, move it down.

**Insertion protocol (when a user proposes a new topic).** Before adding a row to the queue:

1. **If the topic duplicates or is subsumed by any existing row**, do not add it; instead, cite the existing row.
2. **If any existing row covers the same scope or is closely related** (sub-questions of the same theme, overlapping research surface, same Tier-1 evidence base): **merge** instead of adding. Extend the existing row's Objective to absorb the new question. Keep the existing row's `Q-NNN` ID. Do not add a new row. Note the merge in the [Reasoning Journey](#reasoning-journey) at the next Turn 2 atomic write.
3. **Otherwise, insert at the priority-correct position.** Top if more important than everything pending; in the middle if it slots between existing items; at the bottom if least important. Assign the next available `Q-NNN` ID.

This protocol applies wherever the queue is touched. It is the agent's job to keep the queue free of redundant or near-duplicate items at all times.

**Done items leave the queue.** When a topic is researched (Turn 2 atomic write), remove its row from the queue and add a new row to the [Research Tracker](#research-tracker) with the finding and version.

**Reordering priorities.** If the user reprioritizes mid-session, move rows to reflect the new order and note the change in the Reasoning Journey.

**Empty queue.** When all rows are done, ask the user to choose: (1) add new topics; (2) fresh-eyes review (scan the whole project, propose gaps); (3) reopen a specific topic; (4) declare research complete.

<!-- @end: framework.reference.queue-rules -->

<!-- @anchor: framework.reference.brief -->
### Second-opinion brief template

Print this verbatim at the top of Turn 1, wrapped in `<!-- @brief-start -->` and `<!-- @brief-end -->` markers, ready for the user to copy. Replace placeholders with the current topic's specifics; keep the asks and excellence bar intact. No meta-commentary after the brief.

```text
I am designing a {{PROJECT_AND_BASIC_CHARACTERISTICS}}. I'm trying to decide {{RESEARCH_TOPIC_IN_CONTEXT}}.

I need you to do a deep research that allows you to answer these questions: {{LIST_OF_QUESTIONS_TO_BE_RESEARCHED_AND_ANSWERED}}.

Your research must be {{RESEARCH_EXCELLENCE_LEVEL_AND_STYLE_QUANTIFIED_AND_PROVED}}.

Accepted sources will be: {{TIER_1_AND_TIER_2_DEFINITIONS_FOR_THIS_DOMAIN}}.
Automatically rejected: {{TIER_REJECT_RULES}}.

Please cite all claims inline with Title, Author, Year, Venue, DOI/URL in the same sentence as the claim — not at the end and not via links to other parts of the answer. Distinguish what is validated vs. proposed/experimental.
```

<!-- @end: framework.reference.brief -->

<!-- @anchor: framework.reference.synthesis -->
### Synthesis matrix

Required when more than three sources are consulted on the same topic, or any time sources appear to disagree. Always required for quantitative thresholds.

Format: a table where each row is one concrete claim and each column is one Tier (Tier 1, Tier 2, Discovery, etc.). Cell contents: `SUPPORT`, `CONTRADICT`, `SILENT`, `UNVERIFIABLE`. 

The matrix lives in the relevant Session Notes block.

<!-- @end: framework.reference.synthesis -->

<!-- @anchor: framework.reference.validation -->
### Self-validation

Before declaring Turn 2 complete, the agent runs a self-validation pass over the new file. Two kinds of checks: **mechanical** (structural invariants — verifiable deterministically from the file alone) and **semantic** (judgement-based — depend on understanding the content). Mechanical checks are the bulk of validation by count and the cheapest by effort; doing them first catches most write errors before semantic review even starts.

A future `research-buddy validate <file>` command will run all mechanical checks deterministically. Until it ships, the agent runs them mentally against the new file before emitting the Turn 2 marker. Any mechanical failure is a blocking issue (Turn 2 step 5).

**Mechanical checks** (script-automatable):

- YAML frontmatter parses (valid YAML, required fields present).
- Anchor pairs intact: every `<!-- @anchor: X -->` has a matching `<!-- @end: X -->`.
- Markdown table format: all rows have the same column count; no malformed pipes.
- Version number bumped in frontmatter (and nowhere else).
- Filename uses the updated version.
- Queue and Tracker row IDs are unique and sequential (no gaps or duplicates).
- Rules, DAs, and session blocks each have an `<a id>` tag.
- The Turn 1 second-opinion brief (when present) is wrapped in `<!-- @brief-start -->` / `<!-- @brief-end -->`. The Turn 2 change summary (when present) is wrapped in `<!-- @summary-start -->` / `<!-- @summary-end -->`. The end-of-turn marker is the final two lines.
- No plain-text reference to `R-XXX-N`, `DA-XXX`, or `Q-NNN` appears outside a Markdown link `[...](#...)`, an HTML comment, or a fenced code block.

**Semantic checks** (always agent-driven; see [Common failure modes](#common-failure-modes) for the full inventory): source-tier discipline, cross-section contradiction check, no Discarded Alternative re-proposed, second opinions vetted before incorporation, findings compared against already-researched topics, queue insertion protocol applied, `VALIDATED` claims meet the project's validation gate, no fabricated second opinions.

<!-- @end: framework.reference.validation -->

<!-- @anchor: framework.reference.failure-modes -->
### Common failure modes

Each entry is tagged `[mechanical]` (a script can detect it), `[semantic]` (the agent must reason about it), or `[hybrid]` (mechanical detection is partial; semantic review for the rest).

- `[mechanical]` Frontmatter YAML is malformed or missing required fields.
- `[mechanical]` Anchor pairs do not match (open without close, or misnamed).
- `[mechanical]` Markdown table has inconsistent column count.
- `[mechanical]` Version in frontmatter and output filename do not match, or version was not bumped.
- `[mechanical]` Queue or Tracker row IDs are not unique, not sequential, or have gaps.
- `[mechanical]` A rule, DA, or session block is missing its `<a id>` tag.
- `[semantic]` Findings contradict a Tier-1-backed rule already adopted.
- `[semantic]` A rejected approach in Discarded Alternatives is re-proposed in new findings.
- `[semantic]` Second-opinion claims are not verified end-to-end (title, author, URL, content match).
- `[semantic]` A new finding overlaps with an already-researched topic but is not cross-checked for contradiction.
- `[semantic]` Marking a result `VALIDATED` before the project's validation gate is met.
- `[semantic]` Failing to compare new findings against already-researched topics.
- `[hybrid]` Language drift — content not in the file's declared `language.code`. Mechanical: language-detection library on prose. Semantic: code-switching, technical terms, proper nouns.
- `[semantic]` Pausing for confirmation on Turn 2 when no blocking issue actually exists. The default is **write**.
- `[mechanical]` Burying the second-opinion brief below findings on Turn 1, or omitting the `@brief-start` / `@brief-end` markers — the brief must be at the top, wrapped, so a script can extract and dispatch it.
- `[mechanical]` Omitting the `@summary-start` / `@summary-end` markers around the Turn 2 change summary — same automation reason.
- `[semantic]` Adding a queue item without running the [insertion protocol](#queue-rules) — leads to redundant or near-duplicate rows.
- `[mechanical]` Leaving completed rows in the Open Research Queue. Done rows move to Research Tracker; the queue holds only OPEN items.
- `[semantic]` Generating clean view or HTML by default at end of Turn 2 — wait for the user to ask, to keep context lean.
- `[mechanical]` Writing plain-text references to rules / DAs / sessions when a stable link target exists. Always link.

<!-- @end: framework.reference.failure-modes -->

<!-- @end: framework.reference -->

---

<!-- @anchor: project -->
## Project Specification

<!-- Filled in session zero. Modifications to project-specific values go here. Do not modify the Framework sections. -->

### Domain

- **Title:** {{title}}
- **Subtitle:** {{subtitle}}
- **Domain:** {{project.domain}}
- **Deliverable type:** {{project.deliverable_type}}
- **Final goal:** {{project.final_goal}}
- **Timing:** {{project.timing}}
- **Validation gate:** {{project.validation_gate}}

<!-- @anchor: project.tiers -->
### Source tiers

Specific venues per tier for this project. Examples by domain: ML → arXiv / NeurIPS / ICML / EMNLP / ACL / ICLR (T1). Medical → PubMed, Cochrane Reviews, NEJM, Lancet (T1). Patents → USPTO / EPO / WIPO (T1). Finance → JF, JFE, RFS (T1). Legal → primary case law and statutes (T1). Software / coding → official vendor docs and source repos (T1).

- **Tier 1:** {{project.source_tiers.tier1}}
- **Tier 2:** {{project.source_tiers.tier2}}
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

Organize alphabetically (R-ALPHA-1, R-BETA-2, etc.) and then numerically within each topic cluster.

**Block format** (one block per rule; copy this template when adding a new rule, lowercasing the ID for the `<a id>` value):

````
<!-- @rule: R-EXAMPLE-1 -->
<a id="r-example-1"></a>

```yaml rule
id: R-EXAMPLE-1
status: VALIDATED
force: MUST
tags: [tag1, tag2]
adopted_in: "v1.1"
last_verified: "2026-05-06"
evidence:
  tier1:
    - "{{Title}}, {{Author}}, {{Year}}, {{Venue}}, {{URL}}"
  tier2: []
# Optional: contradictions, supersedes, superseded_by
```

**R-EXAMPLE-1 [tag1] [tag2] VALIDATED MUST.** Imperative-form rule body in one or two short paragraphs. Cite Tier-1 sources inline. Avoid `MUST` / `ALWAYS` / `NEVER` shouting unless the rule truly admits no exception; explain reasoning instead.
````

<!-- @end: rules -->

---

<!-- @anchor: discarded -->
## Discarded Alternatives

Permanent record of rejected approaches. Never re-propose items listed here. Each entry has a stable `DA-{{TOPIC}}-{{N}}` label and an inline `<a id>` link target. Always check this section before proposing any approach.

**Block format** (one block per rejection; lowercase the ID for the `<a id>` value):

```
<!-- @da: DA-EXAMPLE-1 -->
<a id="da-example-1"></a>

**DA-EXAMPLE-1.** {{Short title of the rejected approach.}} Rationale: {{why it was rejected, with Tier-1 anchor where applicable}}. Rejected in: v1.X. Superseded by: {{R-XXX-N if applicable, else "—"}}.
```

<!-- @end: discarded -->

---

<!-- @anchor: sessions -->
## Session Notes

One subsection per researched topic. Each contains pre-registration, sources consulted, decisions adopted, rejected claims, and second-opinion evaluation. Each block has an inline `<a id>` link target for cross-linking from elsewhere in the document.

**Block format** (one block per session; lowercase the ID for the `<a id>` value):

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

### v1.0

- Research Buddy template initialized. Project setup completed in session zero.

<!-- @end: references -->

---

<!-- @anchor: changelog -->
## Changelog

Newest first. The first entry is implicitly the current version. Each entry: decisions adopted, rejected alternatives, contradiction-check result, second opinions reviewed (by label), sources used. Reference rules / DAs / sessions by their linked IDs.

### v1.0: Project initialized — {{date}}

{{What was set up: domain, tiers, initial queue, section structure, domain rules.}}

<!-- @end: changelog -->
