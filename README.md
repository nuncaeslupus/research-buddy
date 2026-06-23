# Research Buddy v1.18.0

<img src="https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/images/research-buddy.png" alt="Research Buddy" width="200">

A structured AI research collaborator for any domain.

## Format: v2 Markdown (recommended) and v1 JSON (legacy)

**v2 Markdown is the recommended format for new projects** as of 1.5.
v1 JSON remains supported for existing projects but is on a deprecation
path; new features land on v2 first.

- **v2 Markdown** (default for new work): YAML frontmatter + Markdown
  body with HTML-comment anchors (`<!-- @anchor: ... -->`,
  `<!-- @rule: ... -->`, `<!-- @da: ... -->`). Source of truth =
  `*_v*-source.md` (agent-edited, full framework). The reader-facing
  artifact is the clean view `*_v*.md` (framework stripped) or the
  rendered HTML. Each top-level `## H2` becomes a tab.
- **v1 JSON** (legacy): structured JSON with rich block types
  (callouts, verdicts, fixed-width tables). Source of truth =
  `*_v*.json`. Continue using for projects already on v1; migrate to
  v2 with `research-buddy migrate-v1-to-v2`.

`build`, `validate`, and `upgrade` dispatch on file extension.
`migrate-v1-to-v2` and `clean` operate on v2 only.

## How it works

The AI agent reads the framework embedded in your research document and behaves as a Research Buddy for the full lifetime of the project. Every session produces an updated, versioned source file — the source of truth — and a rendered HTML document for reading.

**Session zero** (v2 Markdown flow — recommended): run `research-buddy init my-project/` to scaffold `source/research-document.md`. Upload that file to an AI assistant. The agent introduces itself, asks questions to understand the project, does discovery research, and proposes the initial structure — sections, source tiers, queue items, and methodology rules tailored to your domain. Output: `{file_name}_v1.0-source.md`. Run `research-buddy build my-project/source/{file_name}_v1.0-source.md` to generate HTML.

**Subsequent sessions**: upload the latest `*-source.md`, say *"Continue research"* — the agent picks up exactly where you left off and works through the queue one topic at a time in exactly 2 turns.

The two-turn protocol (research turn + vet/write turn) applies to both formats. **Legacy v1 JSON flow**: use `research-buddy init my-project/ --v1`; the agent produces versioned `.json` files instead of `.md` sources.

## Install

### For users (pip)

```bash
pip install research-buddy
```

PDF export is an optional extra (weasyprint is a large install with system-level
dependencies, so it's not pulled in by default):

```bash
pip install "research-buddy[pdf]"
```

### For development

```bash
uv sync --extra dev
# or:
pip install -e ".[dev]"
```

## For AI Agents or AI users

If you are an AI agent or a user of a chatbot looking for the initial research template (v2 Markdown, recommended):

- **Direct download**: [starter.md](https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/starter.md)
- **Package path**: `research_buddy.starter.md` (when installed via pip)
- **Source path**: `src/research_buddy/starter.md` (in this repository)

Download this file and attach it into an AI chatbot session to start researching. The AI agent will know what to do.

For the legacy v1 JSON template:

- **Direct download**: [starter.json](https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/starter.json)
- **Package path**: `research_buddy.starter.json` (when installed via pip)
- **Source path**: `src/research_buddy/starter.json` (in this repository)

### Generating HTML

After each research session, to give the user a readable HTML document:

```bash
pip install research-buddy
research-buddy build my-project/source/my-project_v1.0-source.md
```

The output will be `[file_name].html` in the project directory.

### Workflow

1. **Session start**: User uploads their `*-source.md` file (v2) or `.json` file (v1 legacy). If new, ask them to run `research-buddy init <project-name>` first to get the starter template.
2. **Session end**: After making changes, run `research-buddy build <source-file>` to generate HTML. Tell the user the HTML is ready and they can download it.
3. **Next session**: Ask the user to upload the latest `*-source.md` (v2) or `.json` (v1) file and say "Continue research".

The source file is always the source of truth — never the HTML.

## Quick start

```bash
# Scaffold a new project — v2 Markdown by default
research-buddy init my-project/

# Upload my-project/source/research-document.md to your AI assistant
# The agent runs session_zero and produces {file_name}_v1.0-source.md

# Build HTML from the versioned output
research-buddy build my-project/source/my-project_v1.0-source.md

# Or point at the project directory — it finds the latest version automatically
research-buddy build my-project/

# Open the result
open my-project.html
```

For an existing v1 JSON project, pass `--v1` to `init` and use the v1
flow (versioned `.json` files, `--watch`/`--pdf` available on `build`).

## Research protocol

Every session follows a strict, high-integrity 2-turn workflow:

1. **Turn 1: Research & Brief**
   - Agent reads the in-document framework, detects session state, and emits a second-opinion brief before touching any research tool. (`research-buddy turn1 <file>` pre-fills the brief from frontmatter + the top queue row.)
   - Agent performs discovery research using domain-appropriate Tier 1 sources with inline citations, then **STOPS** and waits for the user to provide results from other researchers (other AI agents, human experts, etc.).
2. **Turn 2: Vet & Write**
   - User submits findings from other researchers.
   - Agent vets each finding, resolves pre-registered hypotheses, then performs an **atomic write** to the versioned source file — `*_vX.Y-source.md` for v2 Markdown (recommended), or `*_vX.Y.json` for v1 legacy — bumping the version.
   - User runs `research-buddy build <source-file>` to generate HTML.
   - New research topics are queued for the next session, not shoehorned into the current one.

**Failure modes are explicit**: the in-document framework lists failure modes that agents use to self-check before and after every action.

## File naming

The tool uses the `file_name` field from your document to name outputs.

### v2 Markdown (recommended)

| File                              | Purpose                                                        |
| --------------------------------- | -------------------------------------------------------------- |
| `source/research-document.md`     | Unversioned starter — uploaded to the agent for session zero  |
| `[file_name]_v1.0-source.md`     | First versioned source, produced by session zero               |
| `[file_name]_v1.1-source.md`     | After first research session                                   |
| `[file_name]_v1.0.md`            | Clean view (framework stripped) — shareable artifact           |
| `[file_name]_vX.Y.html`          | Versioned HTML build                                           |
| `[file_name].html`               | Latest stable HTML build                                       |

### v1 JSON (legacy)

| File                             | Purpose                                                       |
| -------------------------------- | ------------------------------------------------------------- |
| `source/research-document.json`  | Unversioned template — never modified after init              |
| `[file_name]_v1.0.json`          | First project file, produced by session zero                  |
| `[file_name]_v1.1.json`          | After first research session                                  |
| `[file_name]_vX.Y.html`          | Versioned HTML build                                          |
| `[file_name].html`               | Latest stable HTML build                                      |

## Batch Processing (v1 JSON only)

You can process multiple v1 JSON files in order. This is useful for replaying the full version history of a legacy project:

```bash
# Processes files in the given order. The final [file_name].html 
# will be generated from the last file in the list.
research-buddy build v1.0.json v1.1.json v1.2.json
```

## Commands

### `research-buddy init <dir>`

Scaffold a new project. Defaults to the recommended **v2 Markdown** form:
creates `source/research-document.md` (the bundled v2 starter, frontmatter
patched with `--title`/`--subtitle` if provided) and `versions/`. Pass
`--v1` to scaffold a legacy v1 JSON project instead (`source/research-document.json`).

```
research-buddy init my-project/ [--title "Project Name"] [--subtitle "..."]
research-buddy init legacy-project/ --v1 --title "..."   # legacy JSON
```

### `research-buddy build <path...>`

Build HTML from document JSON(s) or Markdown file(s). Accepts files,
directories, or both. Dispatches on file extension: `.json` → v1
pipeline, `.md` → v2 pipeline (same single-file chrome — tab bar,
sidebar nav, theme toggle, hljs).

```
research-buddy build my-project/                    # latest version in source/
research-buddy build my-research_v1.5.json          # v1 JSON
research-buddy build my-research_v1.0-source.md     # v2 Markdown
research-buddy build a.json b.json                  # batch JSON IN ORDER
research-buddy build my-project/ --watch            # rebuild on change (.json only)
research-buddy build my-project/ --pdf              # + PDF (v1 only, requires weasyprint)
research-buddy build my-project/ --output master.html
research-buddy build my-project/ --validate-only    # v1 only
```

Mixing `.json` and `.md` inputs in a single invocation is rejected;
`--watch` and `--pdf` are not yet supported for `.md` inputs. The MD
build strips the framework block by default (matches the JSON build's
"reader-facing" semantics — the framework is for the agent reading the
source, not for HTML readers).

### `research-buddy validate <path...>`

Validate JSON or Markdown documents. Dispatches on extension: `.md` →
v2 mechanical validator (frontmatter, anchor pairing, link resolution,
ID uniqueness); everything else → v1 JSON validator (schema +
reference ordering + version compat).

```
research-buddy validate my-research_v1.0-source.md
research-buddy validate my-research_v1.1-source.md --prior my-research_v1.0-source.md
```

The optional `--prior` flag (v2 only) compares against an earlier
version of the same file and enforces append-only invariants:
anchors, Discarded Alternatives, References, and Changelog entries
must never disappear.

### `research-buddy clean <path...>` (v2)

Generate the shareable clean view from a v2 source file: strips the
framework block (`<!-- @anchor: framework.core -->` …
`<!-- @end: framework.reference -->`) and regenerates the title block
from the YAML frontmatter. Output: `{file_name}_v{version}.md`
alongside the source.

```
research-buddy clean my-research_v1.0-source.md
research-buddy clean my-research_v1.0-source.md -o /tmp/out.md
```

Refuses to run on a starter file (`project.domain` is null in the
frontmatter) — there's nothing to clean until session zero fills in
the project specification.

### `research-buddy migrate-v1-to-v2 <path...>` (v2)

One-way migration from a v1 JSON document to a v2 Markdown source
file. Maps `meta.*` + `agent_guidelines.project_specific.*` to YAML
frontmatter; replaces the old framework with the v2 framework block
copied from the bundled `starter.md`; promotes research-tab sections
to top-level H2s; converts verdict blocks to `@rule` / `@da` blocks
with stable IDs.

```
research-buddy migrate-v1-to-v2 my-research_v3.0.json     # writes my-research_v3.0-source.md
research-buddy migrate-v1-to-v2 old.json -o new-source.md
research-buddy migrate-v1-to-v2 old.json --force          # overwrite existing output
```

Refuses to overwrite an existing output unless `--force` is passed.
After migration, run `research-buddy validate <output>.md` to confirm
the result.

### `research-buddy upgrade <path...>`

Re-sync a project source against the installed starter template. Dispatches on file extension:

- `.json` → v1 path. Replaces `agent_guidelines.framework` and `agent_guidelines.session_protocol` wholesale, preserves `session_zero.note` so initialized projects do not re-run session zero, leaves `agent_guidelines.project_specific` untouched, and bumps `meta.research_buddy_version`. Appends a dated entry to `meta.format_note` only when something actually changed.
- `.md` → v2 path. Replaces the framework block (everything between `<!-- @anchor: framework.core -->` and `<!-- @end: framework.reference -->`) with the installed `starter.md`'s block, preserves all project-owned content (frontmatter values, project specification, queue, tracker, rules, DAs, sessions, journey, references, changelog), bumps `research_buddy_version`, renames legacy `format_version` → `doc_format_version`, and inserts missing `project.source_tiers` / `project.domain_rules` frontmatter fields with null values.

```
research-buddy upgrade my-project/                                     # v1 dry-run
research-buddy upgrade my-project/ --apply                             # v1 write + validate
research-buddy upgrade my-project/source/foo_v1.0-source.md            # v2 dry-run
research-buddy upgrade my-project/source/foo_v1.0-source.md --apply    # v2 write + validate
research-buddy upgrade ... --apply --no-validate                       # skip post-write validation
```

Exit codes: `0` clean (no changes or applied), `1` dry-run found changes, `2` error (bad path, validation failed, starter missing, malformed framework block).

## Project layout

```
my-project/
├── source/
│   └── research-document.json    # Template (agent uploads this for session_zero)
├── versions/                     # Versioned HTML builds
│   └── v1.0.html
├── [file_name].html              # Latest stable build (copy of most recent version)
└── theme.css                     # Optional CSS overrides
```

## Multi-language support

The document language is set in session_zero based on the user's preference and recorded in frontmatter. `language` accepts a string (`"Spanish"`) or an object (`{code: es, label: Español}`). It drives two things:

- The HTML `lang` attribute (set automatically).
- **Localized section headings (v2 HTML).** The framework names its user-facing sections in English ("Open Research Queue", "References", …) because their slugs are load-bearing cross-link targets — translating them in the source would break every `[Queue](#open-research-queue)` link. So when `language.code` is a shipped language (currently **Spanish**), the HTML build *displays* those headings in that language while keeping the English slugs/ids, so nothing breaks. Add or override labels — and enable languages not shipped built-in — with an optional `section_labels:` frontmatter mapping (English heading → label):

  ```yaml
  section_labels:
    Open Research Queue: Cola de tareas
  ```

  Localization is HTML-render-only; the clean-view Markdown keeps English headings (there a heading's slug *is* its text, so display and link target can't diverge). The framework prose itself stays English and is stripped from the clean view / HTML.

Research *content* (findings, decisions, status text) is authored in the document language by the agent. The legacy v1 `meta.ui_strings` field is carried forward on migration but is **not** rendered in v2 — there is no fixed status column, so the agent writes status text (and `rb-ok`/`rb-flag` chips) directly in the document language.

## Document format (v1 JSON)

This section applies to the legacy **v1 JSON** format. v2 Markdown documents
use standard Markdown + YAML frontmatter; see `src/research_buddy/starter.md`
for the canonical v2 structure.

The v1 JSON schema is bundled with the package. For reference, see
[`src/research_buddy/schema.json`](./src/research_buddy/schema.json) in the
repository, or the matching path inside the installed wheel
(`research_buddy/schema.json`).

### Block types (v1 JSON)

| Type             | Key fields                                                       |
| ---------------- | ---------------------------------------------------------------- |
| `p`            | `md`                                                           |
| `h3`, `h4`   | `md`, `id`, `badge`                                        |
| `code`         | `text`, `lang`                                               |
| `callout`      | `md`, `variant` (blue\|green\|amber\|red\|purple), `title` |
| `verdict`      | `badge` (adopt\|reject\|defer\|pending), `label`, `md`     |
| `table`        | `headers[]`, `rows[][]`                                      |
| `ul`, `ol`   | `items[]`                                                      |
| `card_grid`    | `cols` (2\|3), `cards[{title, md}]`                          |
| `phase_cards`  | `cards[{phase, title, items[]}]`                               |
| `usage_banner` | `title`, `items[]`                                           |
| `references`   | `items[{version, date, text}]`                                 |
| `svg`          | `html` (raw SVG string)                                        |

### Schema compatibility (v1 JSON)

`meta.research_buddy_version` is required in all v1 documents. The validator
warns if it is missing. When this version changes, schema or build script
behaviour may change — always use the template that matches your installed
version.

## Version compatibility (tool ↔ document)

Research Buddy uses **MAJOR.MINOR.PATCH** semver. Both formats record the tool
version that produced them:

- **v2 Markdown**: `research_buddy_version` in YAML frontmatter.
- **v1 JSON** (legacy): `meta.research_buddy_version`.

### v1 JSON: active version check

Every `research-buddy build` and `research-buddy validate` on a v1 JSON document
actively compares the installed CLI version against the version in the document:

| Comparison                                  | Severity | What happens                                                                                                                                                                                  |
| ------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Exact match                                 | silent   | Nothing to worry about.                                                                                                                                                                       |
| Only PATCH differs (e.g. 1.0.3 vs 1.0)      | silent   | Patches are strictly backwards-compatible. Treated as equivalent.                                                                                                                             |
| Tool MINOR **newer** than doc (same MAJOR)  | silent   | **No action required.** Doc is fully compatible. The agent bumps `meta.research_buddy_version` on the next write.                                                                             |
| Tool MINOR **older** than doc (same MAJOR)  | warning  | Doc may use features your tool does not render correctly. Run `pip install --upgrade research-buddy`.                                                                                         |
| MAJOR differs                               | error    | Schema is not guaranteed to match. Either install the matching major (`pip install 'research-buddy==1.*'`) or start an AI session and say *"Migrate to research-buddy vX.Y"* so the agent updates the document structure. |

**Algorithmic rule:** the validator compares `MAJOR.MINOR` only. Patch-level
differences are ignored — `1.0.3` and `1.0` behave the same.

### v2 Markdown: agent-managed version

In v2 Markdown, `research_buddy_version` is checked only for *presence* (the
field is required). No active MAJOR/MINOR comparison gate exists. The agent
updates the field to the current tool version on each Turn 2 atomic write, so
it stays in sync automatically. Run `research-buddy upgrade <file>.md --apply`
to refresh the framework block and frontmatter when you upgrade the CLI.

### What if my document is on an older version?

If you're upgrading the CLI to a newer minor (e.g. tool `1.1.0`, doc `1.0.3`)
there is nothing to do: your build continues to produce HTML as before.

If you're moving across a major boundary, the v1 CLI will tell you, point at
CHANGELOG.md, and give you a copy-pasteable command to pin the matching major
(if you want to keep your current doc as-is) or an instruction to hand to the
agent (if you want to migrate).

## Development

```bash
make sync           # Install dev dependencies
make lint           # ruff + mypy
make format         # Auto-fix + format
make test           # Run full test suite
make update-skills  # Pull latest shared Claude skills
```

## Examples

The `starter-example/` directory contains pre-built HTML outputs from
the bundled starters:

- `starter.html` — built from `starter.json` (v1 JSON pipeline).
- `starter-md.html` — built from `starter.md` (v2 Markdown pipeline,
  framework stripped to match the v1 reader view).

Regenerate with:

```bash
make regen-example      # v1 only
make regen-md-example   # v2 only
make regen-examples     # both
```

## License

MIT
