# CLAUDE.md

Short project map for future sessions. If something below is wrong, trust the code, fix this file.

## Read first: `status/`

At the start of every session, read both files in `status/` for context:

- `status/plan.md` — improvement roadmap (numbered steps, in order, with
  shipped items checked off) plus a "Future improvements" backlog. Slow-
  changing, strategic. Check here to see what the next step is and why the
  ordering was chosen.
- `status/next-session.md` — append-only session log. Each entry: what was
  done, next steps, blockers. Tactical, updated at the end of each session.
  Check here for the most recent context (PR numbers, decisions, stale
  items flagged in earlier sessions).

Update `next-session.md` at the end of a session when meaningful work shipped
or the next steps changed. Update `plan.md` only when the roadmap itself
changes (step completed, new step inserted, ordering revised).

## What this repo is

`research-buddy` — a CLI that turns a versioned research document
(v2 Markdown or v1 JSON) into a single-file HTML page (optional PDF
via `weasyprint` for v1). Installed as a package; the CLI entry point
is `research_buddy.main:main`. Agents (humans or LLMs) edit the source
file; this tool renders it. The source file is the source of truth.

**v2 Markdown** is the recommended format for new projects (default
since 1.5). YAML frontmatter + Markdown body with HTML-comment anchors.
Source is `*_v*-source.md` (full framework, agent-edited); the clean
view `*_v*.md` (framework stripped) and HTML are derived.

**v1 JSON** is supported for existing projects but on a deprecation
path. Existing JSON projects can migrate via
`research-buddy migrate-v1-to-v2`.

## Layout

```
src/research_buddy/
  main.py              # argparse CLI: build | validate | clean | migrate-v1-to-v2 | init | upgrade
  build.py             # v1 JSON → HTML (block renderers, table widths, lang resolution)
  build_md.py          # v2 MD  → HTML (reuses v1 chrome via base.html.j2)
  upgrade.py           # v1 template refresh: re-sync agent_guidelines from starter.json
  upgrade_md.py        # v2 framework refresh: re-sync framework block + frontmatter from starter.md
  validator.py         # v1 jsonschema + reference ordering + doc/tool version compat
  validator_md.py      # v2 mechanical validator (frontmatter, anchors, links, IDs, prior diff)
  clean_md.py          # v2 source MD → clean MD (strip framework, regen title)
  migrate_v1_to_v2.py  # v1 JSON  → v2 MD source
  schema.json          # v1 Draft 2020-12 schema, bundled in the wheel
  starter.json         # v1 session-zero template, bundled in the wheel
  starter.md           # v2 session-zero template, bundled in the wheel
  css/ js/ lib/ images/  # assets inlined into the generated HTML
scripts/
  sync_version.py        # Source of truth = pyproject.toml; rewrites the other files
  check_version_sync.py  # Read-only: fails if anything drifted. Used by CI.
tests/            # pytest; classes, TDD ceremony enforced
starter-example/  # starter.html (v1) + starter-md.html (v2)
Makefile          # make sync | lint | format | test | regen-example | regen-md-example | regen-examples | build | publish | version-sync | check-version-sync
```

## Commands (prefer Make)

| Command                  | What it does                                                                |
| ------------------------ | --------------------------------------------------------------------------- |
| `make sync`              | `uv sync --extra dev` — install dev deps (includes weasyprint)              |
| `make test`              | `pytest tests/ -v` — full suite                                             |
| `make lint`              | `ruff check` + `ruff format --check` + `mypy` (mirrors CI)                  |
| `make format`            | `ruff check --fix --unsafe-fixes` + `ruff format`                           |
| `make regen-example`     | Rebuild `starter-example/starter.html` from `starter.json` (v1)             |
| `make regen-md-example`  | Rebuild `starter-example/starter-md.html` from `starter.md` (v2)            |
| `make regen-examples`    | Both of the above                                                           |
| `make version-sync`      | Propagate `pyproject.toml` version into the four downstream files          |
| `make check-version-sync`| CI gate: fails if any of the five version strings have drifted              |
| `make build`             | Produce wheel + sdist in `dist/`                                            |
| `make publish`           | `build` then `twine upload` (requires PyPI creds)                           |
| `make update-skills`     | `git subtree pull` latest shared skills from the `shared-skills` remote     |

Don't call `ruff` / `mypy` / `pytest` directly unless debugging — Make targets
keep things consistent with CI.

## Pre-commit hooks

After a fresh clone, install the git hooks once:

```
uv run pre-commit install
```

From then on every `git commit` runs `ruff check`, `ruff format --check`,
`mypy`, and `make check-version-sync` — the same four steps as the CI lint
job. Config lives in `.pre-commit-config.yaml`; all hooks invoke tools via
`uv run` so their versions come from `uv.lock` (no drift vs. CI).

To run the full battery on-demand: `uv run pre-commit run --all-files`.

## Versions

Five places hold the version, one source of truth:

- `pyproject.toml` — canonical (`version = "…"`)
- `src/research_buddy/__init__.py` — `__version__ = "…"` (rewritten by `sync_version.py`)
- `src/research_buddy/starter.json` — `meta.research_buddy_version` (same)
- `src/research_buddy/starter.md` — `research_buddy_version` in YAML frontmatter (same)
- `README.md` — `# Research Buddy v…` heading (same)

Workflow on a bump: edit `pyproject.toml`, run `make version-sync`, commit. CI's
`make check-version-sync` catches drift; `tests/test_version_sync.py` is the
local belt-and-suspenders.

Runtime compatibility rules (see README "Version compatibility"):
- MAJOR differs → error-level warning.
- Same MAJOR, tool MINOR older than doc → warning to upgrade.
- Same MAJOR, tool MINOR newer than doc → info note.
- PATCH-only difference → silent (1.0.3 ≡ 1.0 for the algorithm).

Implemented in `validator._check_version_compatibility`; tests in
`tests/test_schema.py::TestVersionCompatibility`.

## Tests

Plain pytest, class-based for grouping but no inheritance magic. Two shared
fixtures live in `tests/conftest.py`:

- `starter_doc` → fresh `dict` from the bundled `starter.json` (use for unit tests)
- `tmp_project` → scaffolded project dir with a `source/test-project_v1.0.json`
  (use for CLI integration tests)

Tests that compare versions read `from research_buddy import __version__` — do
not hard-code `"1.0.3"`, it will silently rot. New version-related assertions
should use `_parse_semver` from `validator.py` when they need to synthesise
"same-major-but-different-minor" style inputs.

## 2-turn agent workflow (what the tool supports)

1. User runs `research-buddy init my-project/` → produces `source/research-document.json`.
2. User uploads that JSON to an LLM chatbot.
3. Agent runs session_zero (uses `agent_guidelines` inside the JSON), returns
   `[meta.file_name]_v1.0.json`.
4. User saves that JSON, runs `research-buddy build my-project/` →
   produces `versions/[file_name]_v1.0.html` + stable `[file_name].html`.
5. Subsequent sessions: upload latest JSON, say "Continue research". Agent does
   one research topic per session in exactly two turns, then writes a new
   versioned JSON + HTML.

## Optional extras

- `pip install "research-buddy[pdf]"` — enables `--pdf` (adds `weasyprint`,
  which has heavy system deps; explicitly optional).
- `pip install -e ".[dev]"` — dev tooling + weasyprint for local testing.

## Non-obvious things

- **`build` dispatches on file extension.** `.json` → v1 pipeline
  (`build.py`); `.md` → v2 pipeline (`build_md.py`). Mixing the two
  in a single invocation is rejected. `--watch` and `--pdf` are v1
  only. `build_md_html` strips the framework block by default
  (matches the JSON pipeline's reader-facing semantics); pass
  `keep_framework=True` programmatically to keep it.
- **v2 anchors are load-bearing.** `<!-- @anchor: X -->` ↔
  `<!-- @end: X -->` and `<!-- @rule: R-XXX-N -->` ↔
  `<a id="r-xxx-n"></a>` are the anchor system the validator
  protects. `validate --prior` enforces append-only invariants
  (anchors / DAs / changelog / references never disappear). Renaming
  an anchor is a breaking change.
- **`doc_format_version` vs `research_buddy_version`.** The frontmatter
  field `doc_format_version: 2` is the *format generation* — it bumps
  when v2 itself changes shape (rare). `research_buddy_version` is the
  *tool version* and tracks `pyproject.toml`. The legacy `format_version`
  key is still accepted by `validator_md.py` and `clean_md.py` but emits
  a `deprecated-format-version-key` warning; `research-buddy upgrade
  <file>.md --apply` renames it (and refreshes the framework block
  + adds missing `project.source_tiers` / `project.domain_rules`
  frontmatter fields) on existing v2 docs.
- **`*.md` ships in the wheel.** `[tool.setuptools.package-data]`
  globs include `*.md` so `starter.md` is available via
  `importlib.resources` after `pip install`. Without this glob,
  `migrate-v1-to-v2` would fail at runtime (it loads the v2 framework
  block from the bundled starter).
- `build.py` has English-centric heuristics in `_table_col_widths` (hand-tuned
  column widths for specific header patterns) and `r_code` (Python auto-detect
  when `lang` is missing). Good enough for the starter, intentionally left as-is.
- `r_svg` renders the caller-provided HTML **verbatim**. SVG blocks are trusted;
  the agent is instructed in `starter.json.agent_guidelines` not to embed JS.
- `meta.language` accepts both a string ("English") and an object
  (`{"code": "en", "label": "English"}`). The string form is mapped to a BCP-47
  code via `_LANGUAGE_NAME_TO_CODE` in `build.py`; unknown names fall back to the
  first token truncated to 10 chars.
- CI (`.github/workflows/ci.yml`) runs lint on 3.12 only, tests on 3.11 + 3.12.
  `make check-version-sync` is part of the lint job.
- `tmp/`, `.vscode/`, `dist/` are gitignored. `starter-example/` is committed
  so users can view the example without installing the package.
- `.claude/skills/` is imported from a shared repo via `git subtree` from
  `https://github.com/nuncaeslupus/my-skills.git`. `make update-skills` pulls
  the latest. Project-specific skills can be dropped alongside the shared ones
  — subtree won't touch them.
