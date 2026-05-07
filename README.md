# Research Buddy v1.6.0

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

The AI agent reads `agent_guidelines` embedded in the JSON and behaves as a Research Buddy for the full lifetime of the project. Every session produces an updated, versioned JSON file — the source of truth — and optionally a rendered HTML document for reading.

**Session zero** (first session with a new document): the agent introduces itself, asks 5 questions to understand the project, does discovery research, and proposes the initial structure — tabs, source tiers, queue items, and methodology rules tailored to your domain. Output: `[file_name]_v1.0.json`.

**Subsequent sessions**: upload the latest JSON, say *"Continue research"* — the agent picks up exactly where you left off and works through the queue one topic at a time in exactly 2 turns.

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

If you are an AI agent or a user of a chatbot looking for the initial research template:

- **Direct download**: [starter.json](https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/starter.json)
- **Package path**: `research_buddy.starter.json` (when installed via pip)
- **Source path**: `src/research_buddy/starter.json` (in this repository)

Download this file and attach it into an AI chatbot session to start researching. The AI agent will know what to do.

### Generating HTML

After each research session, to give the user a readable HTML document:

```bash
pip install research-buddy
research-buddy build your-project.json
```

The output will be `your-project.html` in the same directory.

### Workflow

1. **Session start**: User uploads their JSON file. If new, ask them to run `research-buddy init <project-name>` first to get the starter template.
2. **Session end**: After making changes, run `research-buddy build <json-file>` to generate HTML. Tell the user the HTML is ready and they can download it.
3. **Next session**: Ask the user to upload the latest JSON file and say "Continue research".

The JSON file is always the source of truth — never the HTML.

## Quick start

```bash
# Scaffold a new project
research-buddy init my-project/

# Upload my-project/source/research-document.json to your AI assistant
# The agent runs session_zero and produces [file_name]_v1.0.json

# Build HTML from the versioned output
research-buddy build my-project_v1.0.json

# Or point at the project directory — it finds the latest version automatically
research-buddy build my-project/

# Watch for changes
research-buddy build my-project/ --watch

# Open the result
open [file_name].html
```

## Research protocol

Every session follows a strict, high-integrity 2-turn workflow:

1. **Turn 1: Research & External Prompt**
   - Agent performs discovery research using domain-appropriate Tier 1 sources with inline citations.
   - Agent prints findings, proposed decisions, and a **prompt for other researchers**.
   - **CRITICAL**: The agent then STOPS and waits for the user to provide results from other researchers (other AI agents, human experts, etc.).
2. **Turn 2: Review & Finalize**
   - User submits findings from other researchers.
   - Agent evaluates, labels (`Gemini-1`, `Human-1`, etc.), and compares them with its own research.
   - Agent performs an **atomic write** to the JSON file, bumps the version, and generates the final HTML (e.g., `my-research_v2.3.html` and `my-research.html`).
   - Any requests to add new research topics during these turns are integrated into the final JSON.

**Failure modes are explicit**: the document includes a failure_modes list that agents use to self-check before and after every action.

## File naming

The script uses `meta.file_name` from your JSON to name the outputs.

| File                         | Purpose                                           |
| ---------------------------- | ------------------------------------------------- |
| `research-document.json`     | Unversioned template — never modified after init |
| `[file_name]_v1.0.json`      | First project file, produced by session_zero      |
| `[file_name]_v1.1.json`      | After first research session                      |
| `[file_name]_vX.Y.html`      | Versioned HTML build                              |
| `[file_name].html`           | Latest stable HTML build                          |

## Batch Processing

You can process multiple JSON files in order. This is useful for projects with many versions:

```bash
# Processes files in the given order. The final [file_name].html 
# will be generated from the last file in the list.
research-buddy build v1.0.json v1.1.json v1.2.json
```

## Commands

### `research-buddy init <dir>`

Scaffold a new project. Creates `source/research-document.json` (Research Buddy v1.0 template) and `versions/`.

```
research-buddy init my-project/ [--title "Project Name"] [--subtitle "..."]
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

The document language is set in session_zero based on the user's preference. `meta.language` accepts a string (`"English"`) or an object (`{"code": "es", "label": "Español"}`). The HTML `lang` attribute is set automatically. `agent_guidelines` always stays in English.

UI labels (`"OPEN"`, `"✦ Researched"`, `"Next Topic"`, etc.) are stored in `meta.ui_strings` and translated by the agent in session_zero — no hard-coded strings in document content.

## Document format

The JSON schema is bundled with the package. For reference, see
[`src/research_buddy/schema.json`](./src/research_buddy/schema.json) in the
repository, or the matching path inside the installed wheel
(`research_buddy/schema.json`).

### Block types

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

### Schema compatibility

`meta.research_buddy_version` is required in all documents. The validator warns if it is missing. When this version changes, schema or build script behaviour may change — always use the template that matches your installed version.

## Version compatibility (tool ↔ document)

Research Buddy uses **MAJOR.MINOR.PATCH** semver. Every `research-buddy build`
and `research-buddy validate` compares the installed CLI version against
`meta.research_buddy_version` and reacts like this:

| Comparison                                  | Severity | What happens                                                                                                                                                                                                                    |
| ------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Exact match                                 | silent   | Nothing to worry about.                                                                                                                                                                                                         |
| Only PATCH differs (e.g. 1.0.3 vs 1.0)      | silent   | Patches are strictly backwards-compatible. Treated as equivalent.                                                                                                                                                               |
| Tool MINOR **newer** than doc (same MAJOR)  | silent   | **No action required.** Doc is fully compatible. The agent will bump `meta.research_buddy_version` on the next write. Nothing is printed; exit code stays 0.                                                                    |
| Tool MINOR **older** than doc (same MAJOR)  | warning  | Doc may use features your tool does not render correctly. Run `pip install --upgrade research-buddy`.                                                                                                                           |
| MAJOR differs                               | error    | Schema is not guaranteed to match. Either install the matching major (`pip install 'research-buddy==1.*'`) or start an AI session and say *"Migrate to research-buddy vX.Y"* so the agent updates the document structure. |

**Algorithmic rule:** for compatibility, the validator compares `MAJOR.MINOR`
only. Patch-level differences are ignored — `1.0.3` and `1.0` behave the same.

### What if my document is on an older version?

If you're upgrading the CLI to a newer minor (e.g. tool `1.1.0`, doc `1.0.3`)
there is nothing to do: your build continues to produce HTML as before. The
agent bumps `meta.research_buddy_version` the next time it writes to the
document.

If you're moving across a major boundary, the CLI will tell you, point at
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
