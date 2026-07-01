# Research Buddy v2.2.0

<img src="https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/images/research-buddy.png" alt="Research Buddy" width="200">

A structured AI research collaborator for any domain.

## Format

Research Buddy documents are **v2 Markdown**: YAML frontmatter + a Markdown body
with HTML-comment anchors (`<!-- @anchor: ... -->`, `<!-- @rule: ... -->`,
`<!-- @da: ... -->`). The source of truth is `*_v*-source.md` (agent-edited,
carries the full framework); the reader-facing artifacts are the clean view
`*_v*.md` (framework stripped) and the rendered single-file HTML. Each top-level
`## H2` becomes a tab.

> **Upgrading from v1 JSON?** Legacy v1 JSON support was removed in **v2.0**.
> Convert an existing v1 document with `research-buddy migrate-v1-to-v2 old.json`
> — it writes a v2 `*-source.md` you can then `build`. This is the only command
> that still reads JSON.

## How it works

The AI agent reads the framework embedded in your research document and behaves as a Research Buddy for the full lifetime of the project. Every session produces an updated, versioned source file — the source of truth — and a rendered HTML document for reading.

**Session zero**: run `research-buddy init my-project/` to scaffold `source/research-document.md`. Upload that file to an AI assistant. The agent introduces itself, asks questions to understand the project, does discovery research, and proposes the initial structure — sections, source tiers, queue items, and methodology rules tailored to your domain. Output: `{file_name}_v1.0-source.md`. Run `research-buddy build my-project/source/{file_name}_v1.0-source.md` to generate HTML.

**Subsequent sessions**: upload the latest `*-source.md`, say *"Continue research"* — the agent picks up exactly where you left off and works through the queue one topic at a time in exactly 2 turns.

## Install

### For users (pip)

```bash
pip install research-buddy
```

### For development

```bash
uv sync --extra dev
# or:
pip install -e ".[dev]"
```

## For AI Agents or AI users

If you are an AI agent or a user of a chatbot looking for the initial research template:

- **Direct download**: [starter.md](https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/starter.md)
- **Package path**: `research_buddy.starter.md` (when installed via pip)
- **Source path**: `src/research_buddy/starter.md` (in this repository)

Download this file and attach it into an AI chatbot session to start researching. The AI agent will know what to do.

### Generating HTML

After each research session, to give the user a readable HTML document:

```bash
pip install research-buddy
research-buddy build my-project/source/my-project_v1.0-source.md
```

The output will be `[file_name].html` in the project directory.

### Workflow

1. **Session start**: User uploads their `*-source.md` file. If new, ask them to run `research-buddy init <project-name>` first to get the starter template.
2. **Session end**: After making changes, run `research-buddy build <source-file>` to generate HTML. Tell the user the HTML is ready and they can download it.
3. **Next session**: Ask the user to upload the latest `*-source.md` file and say "Continue research".

The source file is always the source of truth — never the HTML.

## Quick start

```bash
# Scaffold a new project
research-buddy init my-project/

# Upload my-project/source/research-document.md to your AI assistant
# The agent runs session_zero and produces {file_name}_v1.0-source.md

# Build HTML from the versioned output
research-buddy build my-project/source/my-project_v1.0-source.md

# Open the result
open my-project.html
```

## Research protocol

Every session follows a strict, high-integrity 2-turn workflow:

1. **Turn 1: Research & Brief**
   - Agent reads the in-document framework, detects session state, and emits a second-opinion brief before touching any research tool. (`research-buddy turn1 <file>` pre-fills the brief from frontmatter + the top queue row.)
   - Agent performs discovery research using domain-appropriate Tier 1 sources with inline citations, then **STOPS** and waits for the user to provide results from other researchers (other AI agents, human experts, etc.).
2. **Turn 2: Vet & Write**
   - User submits findings from other researchers.
   - Agent vets each finding, resolves pre-registered hypotheses, then performs an **atomic write** to the versioned source file `*_vX.Y-source.md`, bumping the version.
   - User runs `research-buddy build <source-file>` to generate HTML.
   - New research topics are queued for the next session, not shoehorned into the current one.

**Failure modes are explicit**: the in-document framework lists failure modes that agents use to self-check before and after every action.

## File naming

The tool uses the `file_name` field from your document to name outputs.

| File                          | Purpose                                                        |
| ----------------------------- | -------------------------------------------------------------- |
| `source/research-document.md` | Unversioned starter — uploaded to the agent for session zero  |
| `[file_name]_v1.0-source.md`  | First versioned source, produced by session zero               |
| `[file_name]_v1.1-source.md`  | After first research session                                   |
| `[file_name]_vX.Y.md`         | Clean view (framework stripped) — shareable artifact           |
| `[file_name]_vX.Y.html`       | Versioned HTML build                                           |
| `[file_name].html`            | Latest stable HTML build                                       |

## Commands

### `research-buddy init <dir>`

Scaffold a new project: creates `source/research-document.md` (the bundled v2
starter, frontmatter patched with `--title`/`--subtitle` if provided) and
`versions/`.

```
research-buddy init my-project/ [--title "Project Name"] [--subtitle "..."]
```

### `research-buddy build <path...>`

Build a single-file HTML page from one or more v2 Markdown source files (tab
bar, sidebar nav, theme toggle, syntax highlighting).

```
research-buddy build my-research_v1.0-source.md
research-buddy build my-research_v1.0-source.md --output master.html
research-buddy build my-research_v1.0-source.md --no-versioning
```

The build strips the framework block by default (the framework is for the agent
reading the source, not for HTML readers) and **sanitizes** all agent-authored
HTML (see [Security & trust model](#security--trust-model)). The render aborts
without writing HTML if the document has validation errors.

### `research-buddy validate <path...>`

Run the v2 mechanical validator (frontmatter, anchor pairing, link resolution,
ID uniqueness, dangerous-HTML warnings).

```
research-buddy validate my-research_v1.0-source.md
research-buddy validate my-research_v1.1-source.md --prior my-research_v1.0-source.md
```

The optional `--prior` flag compares against an earlier version of the same file
and enforces append-only invariants: anchors, Discarded Alternatives,
References, and Changelog entries must never disappear.

### `research-buddy clean <path...>`

Generate the shareable clean view from a v2 source file: strips the framework
block (`<!-- @anchor: framework.core -->` … `<!-- @end: framework.reference -->`)
and regenerates the title block from the YAML frontmatter. Output:
`{file_name}_v{version}.md` alongside the source.

```
research-buddy clean my-research_v1.0-source.md
research-buddy clean my-research_v1.0-source.md -o /tmp/out.md
```

Refuses to run on a starter file (`project.domain` is null in the frontmatter) —
there's nothing to clean until session zero fills in the project specification.

### `research-buddy migrate-v1-to-v2 <path...>`

One-way migration from a legacy v1 JSON document to a v2 Markdown source file —
the only command that still reads JSON. Maps `meta.*` +
`agent_guidelines.project_specific.*` to YAML frontmatter; injects the v2
framework block from the bundled `starter.md`; promotes research-tab sections to
top-level H2s; converts verdict blocks to `@rule` / `@da` blocks with stable IDs.

```
research-buddy migrate-v1-to-v2 my-research_v3.0.json     # writes my-research_v3.0-source.md
research-buddy migrate-v1-to-v2 old.json -o new-source.md
research-buddy migrate-v1-to-v2 old.json --force          # overwrite existing output
```

Refuses to overwrite an existing output unless `--force` is passed. After
migration, run `research-buddy validate <output>.md` to confirm the result.

### `research-buddy upgrade <path...>`

Re-sync a v2 Markdown source against the installed `starter.md`. Replaces the
framework block (everything between `<!-- @anchor: framework.core -->` and
`<!-- @end: framework.reference -->`) with the installed starter's block,
preserves all project-owned content (frontmatter values, project specification,
queue, tracker, rules, DAs, sessions, journey, references, changelog), bumps
`research_buddy_version`, renames legacy `format_version` → `doc_format_version`,
and inserts missing `project.source_tiers` / `project.domain_rules` frontmatter
fields with null values.

```
research-buddy upgrade my-project/source/foo_v1.0-source.md            # dry-run
research-buddy upgrade my-project/source/foo_v1.0-source.md --apply    # write + validate
research-buddy upgrade ... --apply --no-validate                       # skip post-write validation
```

Exit codes: `0` clean (no changes or applied), `1` dry-run found changes, `2`
error (bad path, validation failed, starter missing, malformed framework block).

## Project layout

```
my-project/
├── source/
│   └── research-document.md       # Starter (agent uploads this for session_zero)
├── versions/                      # Versioned HTML builds
│   └── [file_name]_v1.0.html
├── [file_name].html               # Latest stable build (copy of most recent version)
└── theme.css                      # Optional CSS overrides
```

## Multi-language support

The document language is set in session_zero based on the user's preference and recorded in frontmatter. `language` accepts a string (`"Spanish"`) or an object (`{code: es, label: Español}`). It drives two things:

- The HTML `lang` attribute (set automatically).
- **Localized section headings.** The framework names its user-facing sections in English ("Open Research Queue", "References", …) because their slugs are load-bearing cross-link targets — translating them in the source would break every `[Queue](#open-research-queue)` link. So when `language.code` is a shipped language (currently **Spanish**), the HTML build *displays* those headings in that language while keeping the English slugs/ids, so nothing breaks. Add or override labels — and enable languages not shipped built-in — with an optional `section_labels:` frontmatter mapping (English heading → label):

  ```yaml
  section_labels:
    Open Research Queue: Cola de tareas
  ```

  Localization is HTML-render-only; the clean-view Markdown keeps English headings (there a heading's slug *is* its text, so display and link target can't diverge). The framework prose itself stays English and is stripped from the clean view / HTML.

Research *content* (findings, decisions, status text) is authored in the document language by the agent — there is no fixed status column, so the agent writes status text (and `rb-ok`/`rb-flag` chips) directly in the document language.

## Security & trust model

A v2 document is **Markdown authored by an LLM** and rendered to a single-file HTML page you open in a browser. The renderer intentionally lets raw HTML through (so the framework's comment anchors, inline SVG illustrations, and status chips work). That means a prompt-injected or careless agent emitting `<script>`, an `onerror=` handler, or a `javascript:` link is part of the threat model. Research Buddy defends in two layers:

- **`validate` warns.** `research-buddy validate <file>.md` flags `<script>`, inline `on*=` event handlers, and `javascript:` URIs in the body (`unsafe-html-script` / `-event-handler` / `-js-uri`). These are warnings, not errors — a document may legitimately *discuss* such an example inside a code block.
- **`build` sanitizes.** When rendering HTML, every agent-authored fragment (each tab's body, frontmatter banners, tab labels, and the document title) is run through a sanitizer ([`nh3`](https://nh3.readthedocs.io/), the Rust *ammonia* bindings) with an allowlist matching the framework's element catalog (see `src/research_buddy/starter.md`). Active content — `<script>` and its contents, inline event handlers, `javascript:` / `data:` URIs, `<iframe>` / `<object>` / `<foreignObject>`, and anything outside the allowlist — is stripped, while prose, tables, callouts, verdicts, cards, status chips, and **inline SVG illustrations** are preserved. SVG specifically is sanitized as untrusted (its `<script>`, event handlers, `<animate>`, and `<foreignObject>` are removed) rather than passed through.

The page's own chrome (syntax highlighting, the tab/theme toggle script) is generated by the tool, not by the agent, and is not affected. Theme CSS supplied via `theme_css` is inlined but has its `</style>` neutralized so it cannot break out of the `<style>` element.

This is defense-in-depth for the *rendered HTML*; the source `.md` is still yours to trust. If you build a document from an untrusted source, the sanitizer is what stands between that source and script execution in your browser.

## Version compatibility (tool ↔ document)

Research Buddy uses **MAJOR.MINOR.PATCH** semver. Every v2 document records the
tool version that produced it in `research_buddy_version` (YAML frontmatter).

The field is checked only for *presence* (it is required) — there is no active
MAJOR/MINOR comparison gate. The agent updates it to the current tool version on
each Turn 2 atomic write, so it stays in sync automatically. Run
`research-buddy upgrade <file>.md --apply` to refresh the framework block and
frontmatter when you upgrade the CLI.

## Development

```bash
make sync           # Install dev dependencies
make lint           # ruff + mypy + version-sync check
make format         # Auto-fix + format
make test           # Run full test suite
make update-skills  # Pull latest shared Claude skills
```

## Examples

The `starter-example/` directory contains `starter-md.html` — a pre-built HTML
output from the bundled `starter.md` (framework stripped to match the reader
view). Regenerate with:

```bash
make regen-examples   # (alias: make regen-md-example)
```

## License

MIT
