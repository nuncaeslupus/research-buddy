# Research Buddy: AI-Agent Research Collaborator

A framework for conducting and documenting rigorous research using one or multiple AI agents. Research Buddy generates high-fidelity, single-file HTML documentation from structured JSON while enforcing a strict research protocol to ensure source integrity, cross-section consistency, and empirical validation.

## Why Research Buddy?

- **Agent-First Architecture:** Designed for one or multiple agents (Claude, GPT, Gemini) to collaboratively author and maintain complex technical documentation.
- **Rigorous Protocol:** The starter template includes a multi-step research workflow (second-opinions, tier-1 sourcing, contradiction checks) that agents must follow.
- **High-Fidelity Output:** Professional tabbed layout with recursive sidebar navigation, semantic unique IDs, and interactive UI components.
- **Single-File Delivery:** Generates a standalone HTML (or PDF) that contains all styles and scripts for easy sharing.

## Install

```bash
uv sync           # or: pip install -e .
```

For PDF export, install `weasyprint`:
```bash
pip install weasyprint
```

## Quick start

```bash
# Scaffold a new project
research-buddy init docs/ --title "Project Name"

# Edit the source JSON (Agents follow the embedded protocol)
$EDITOR docs/source/document_v1.0.json

# Build (supports multiple projects at once)
research-buddy build docs/

# Watch for changes and rebuild automatically
research-buddy build docs/ --watch

# Open the result
open docs/docs.html
```

## The Research Protocol

Research Buddy isn't just a builder; it's a methodology. The `init` template enforces:
1. **Second-Opinion Gates:** Agents must draft and wait for confirmation of second-opinion prompts before proceeding.
2. **Tiered Sourcing:** Strict hierarchy of evidence (Tier 1: Peer-reviewed/arXiv; Tier 2: Docs/Textbooks). No blogs or forums.
3. **Cross-Section Contradiction Checks:** Every decision must be verified against all other sections it interacts with before updating.
4. **Empirical Validation:** Decisions are tagged by their validation status (theoretical vs. empirically validated).

## Commands

### `research-buddy init <dir> [--title T] [--subtitle S] [--ver V]`

Scaffold a new project with the rigorous research protocol embedded in the starter template.

### `research-buddy build <path...> [--all] [--watch] [--pdf] [--theme F] [--output N]`

Build HTML from document JSON(s). Accepts multiple files or directories.

- `<path...>` — One or more JSON files or project directories.
- `--all` — If a directory is provided, build all `document_v*.json` files found in `source/`.
- `--watch` — Watch for changes and rebuild automatically (single path only).
- `--pdf` — Generate a PDF export alongside the HTML (requires `weasyprint`).
- `--theme theme.css` — Inject custom CSS after the default stylesheet.
- `--output docs.html` — Stable output filename (default: `docs.html`).
- `--validate-only` — Run validation checks without generating HTML.

### `research-buddy validate <path...>`

Run JSON Schema + semantic validation on one or more documents.

Checks for:
- Structural correctness and schema compliance.
- Chronological ordering of references.
- Completeness of meta fields and required protocol steps.

## Project Layout

After `research-buddy init docs/`, your directory looks like:

```
docs/
├── source/
│   └── document_v1.0.json    # The "source of truth" (edited by agents)
├── versions/                  # Historical, versioned HTML builds
│   └── v1.0.html
├── docs.html                  # The "latest" stable build
└── theme.css                  # Optional: Project-specific CSS overrides
```

## Document Format

See `schemas/document.schema.json` for the full JSON Schema.

### Block Types

| Type | Description | Key fields |
|------|-------------|------------|
| `p` | Paragraph | `md` |
| `h3` | Heading level 3 | `md`, `id`, `badge` |
| `h4` | Heading level 4 | `md`, `id` |
| `heading` | Generic heading | `content`, `level` (3\|4), `id` |
| `code` | Code block | `text`, `lang` |
| `callout` | Callout box | `md`, `variant`, `title` |
| `verdict` | Verdict badge | `md`, `badge`, `label` |
| `table` | Data table | `headers`, `rows` |
| `ul` / `ol` | Lists | `items` |
| `card_grid` | Card layout | `cards`, `cols` |
| `phase_cards` | Phase cards | `cards` |
| `usage_banner` | Usage box | `title`, `items` |
| `references` | Versioned refs | `items` (text, version, date) |

## Development

```bash
make sync      # Install dev dependencies
make lint      # ruff + mypy
make format    # Auto-fix + format
make test      # Run tests (includes example regeneration)
```

## License

MIT
