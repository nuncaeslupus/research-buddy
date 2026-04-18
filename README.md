# Research Buddy v1.0.3

<img src="https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/images/research-buddy.png" alt="Research Buddy" width="200">

A structured AI research collaborator for any domain.

## How it works

The AI agent reads `agent_guidelines` embedded in the JSON and behaves as a Research Buddy for the full lifetime of the project. Every session produces an updated, versioned JSON file — the source of truth — and optionally a rendered HTML document for reading.

**Session zero** (first session with a new document): the agent introduces itself, asks 5 questions to understand the project, does discovery research, and proposes the initial structure — tabs, source tiers, queue items, and methodology rules tailored to your domain. Output: `[file_name]_v1.0.json`.

**Subsequent sessions**: upload the latest JSON, say *"Continue research"* — the agent picks up exactly where you left off and works through the queue one topic at a time in exactly 2 turns.

## Install

### For users (pip)

```bash
pip install research-buddy
```

### For development

```bash
uv sync
# or:
pip install -e .
```

For PDF export (optional):

```bash
pip install weasyprint
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

Build HTML from document JSON(s). Accepts files, directories, or both.

```
research-buddy build my-project/                    # latest version in source/
research-buddy build my-research_v1.5.json          # specific file
research-buddy build a.json b.json                  # batch process IN ORDER
research-buddy build my-project/ --watch            # rebuild on change
research-buddy build my-project/ --pdf              # + PDF export (requires weasyprint)
research-buddy build my-project/ --output master.html # custom output name/path
research-buddy build my-project/ --validate-only    # check only, no HTML output
```

### `research-buddy validate <path...>`

Validate JSON schema + semantic rules (reference ordering, required fields, language format, `research_buddy_version` presence).

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

The JSON schema is bundled with the package. For reference, see `src/research_buddy/schema.json` or install the package and run `research-buddy validate --help`.

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

## Development

```bash
make sync      # Install dev dependencies
make lint      # ruff + mypy
make format    # Auto-fix + format
make test      # Run full test suite
```

## Examples

The `starter-example/` directory contains a pre-built HTML output from the starter template. Regenerate it with:

```bash
pip install research-buddy
research-buddy build --help
```

## License

MIT
