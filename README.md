# Research Buddy

Generate high-fidelity research documentation from structured JSON. Tabbed layout with recursive sidebar navigation, semantic unique IDs, and professional UI optimization.

## Install

```bash
uv sync           # or: pip install -e .
```

## Quick start

```bash
# Scaffold a new project
research-buddy init docs/

# Edit the source JSON
$EDITOR docs/source/document_v1.0.json

# Build
research-buddy build docs/

# Open
open docs/docs.html
```

## Project layout

After `research-buddy init docs/`, your directory looks like:

```
docs/
├── source/
│   └── document_v1.0.json    # Your content (edit this)
├── versions/                  # Generated versioned HTML
│   └── v1.0.html
├── docs.html                  # Generated (latest version)
└── theme.css                  # Optional: CSS overrides
```

## Commands

### `research-buddy init <dir>`

Create the directory structure and a starter `document_v1.0.json`.

### `research-buddy build <path> [--theme FILE] [--output NAME]`

Build HTML from the latest JSON in `<path>/source/` (or from a specific JSON file).

- `--theme theme.css` — Inject custom CSS after the default stylesheet
- `--output NAME` — Output filename (default: `docs.html`)
- `--validate-only` — Check for errors without generating HTML

### `research-buddy validate <path>`

Run JSON Schema + semantic validation without building.

Checks for:
- Structural correctness (required fields, valid block types)
- Chronological ordering of references
- Completeness of meta fields

Note: Duplicate HTML IDs are now handled automatically by the build engine via unique namespacing.

## Document format

See `schemas/document.schema.json` for the full JSON Schema.

### Top-level structure

Research Buddy uses a semantic, nested hierarchy where titles are functional keys:

```json
{
  "meta": {
    "version": "1.0",
    "date": "April 2026",
    "title": "Research Buddy Project",
    "subtitle": "Technical Analysis \u00b7 Design"
  },
  "agent_guidelines": {
    "structure_map": "Tabs > Sections > Subsections",
    "widget_library": "Available blocks: p, h3, h4, code, table, etc."
  },
  "tabs": [
    {
      "id": "research",
      "label": "Research",
      "sections": {
        "Theoretical Foundations": {
          "subtitle": "Core Logic",
          "blocks": [{"type": "p", "md": "Content here..."}],
          "subsections": {
            "Specific Technique": {
              "blocks": [{"type": "code", "text": "def fix()..."}]
            }
          }
        }
      }
    }
  ]
}
```

### Block types

| Type | Description | Key fields |
|------|-------------|------------|
| `p` | Paragraph | `md` |
| `h3` | Heading level 3 | `md`, `id`, `badge` |
| `h4` | Heading level 4 | `md`, `id` |
| `heading` | Generic heading | `content`, `level` (3\|4), `id` |
| `paragraph` | Generic paragraph | `content` |
| `code` | Code block | `text`, `lang` |
| `callout` | Callout box | `md`, `variant`, `title` |
| `verdict` | Verdict badge | `md`, `badge`, `label` |
| `table` | Data table | `headers`, `rows` |
| `ul` / `ol` | Lists | `items` |
| `svg` | SVG diagram | `html` |
| `card_grid` | Card layout | `cards`, `cols` |
| `phase_cards` | Phase cards | `cards` |
| `usage_banner` | Usage box | `title`, `items` |

### Custom themes

Create a `theme.css` file in your project root (or pass `--theme`). It's injected after the default styles, so you can override CSS variables:

```css
:root {
  --bg:    #ffffff;
  --text:  #1a1a1a;
  --blue:  #0066cc;
  --font:  'Inter', sans-serif;
}
```

## Agent-friendly workflow

The JSON document format is designed to be authored and maintained by AI agents (Claude, GPT, etc.). A typical workflow:

1. **Agent writes content** — the agent fills in sections, blocks, and changelog entries in the JSON
2. **Tool validates** — `research-buddy validate` catches structural errors before building
3. **Tool builds** — `research-buddy build` generates the HTML
4. **Human reviews** — open the single-file HTML in a browser

The JSON Schema at `schemas/document.schema.json` can be referenced by agents for correct structure. The `$schema` field can be added to your document for editor autocompletion.

## Development

```bash
make sync      # Install dev dependencies
make lint      # ruff + mypy
make format    # Auto-fix + format
make test      # Run tests
```

## License

MIT
