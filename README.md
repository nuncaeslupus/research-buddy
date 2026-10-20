# Research Buddy v2.2.1

[![PyPI](https://img.shields.io/pypi/v/research-buddy)](https://pypi.org/project/research-buddy/)
[![CI](https://github.com/nuncaeslupus/research-buddy/actions/workflows/ci.yml/badge.svg)](https://github.com/nuncaeslupus/research-buddy/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/nuncaeslupus/research-buddy/blob/main/LICENSE)

<p align="center">
  <img src="https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/docs/hero.png" width="100%" alt="Research Buddy: a versioned source document with its frontmatter, queue, rules and devil's-advocate anchors; one queue topic per session in two turns, a brief and discovery that stops for your results, then the next version written and validated append-only; and the rendered single-file HTML with tabs and a tracker of settled and in-progress topics">
</p>

**A structured AI research collaborator for any domain, carried inside a single versioned Markdown file.**

Long research with a chatbot drifts: context is lost between sessions, settled
questions get reopened, and sources go unchecked. Research Buddy puts the method
in the document itself. You upload one `*-source.md` file to any AI assistant; the
framework embedded in it makes the agent work one queued topic per session, in two
turns, with tiered sources and append-only history. The `research-buddy` CLI
scaffolds, validates and versions that file and renders it to a single-file HTML page.

## Quick start

```bash
pip install research-buddy
research-buddy init my-project/
```

Upload `my-project/source/research-document.md` to your AI assistant. It runs
session zero (asks about your project, proposes sections, source tiers, rules and a
research queue) and returns `{file_name}_v1.0-source.md`. Save it in
`my-project/source/`, then:

```bash
research-buddy build my-project/source/my-project_v1.0-source.md
```

That writes `my-project.html` next to the source, plus a per-version copy in
`versions/`. In later sessions, upload the latest `*-source.md` and say
*"Continue research"*.

No install needed to start: the template is also a
[direct download](https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/starter.md).

## Example

A `heat-pumps_v1.0-source.md` after session zero, whose top queue row is
`Q-001 | Radiator sizing | Can existing radiators deliver design heat load at 45 C flow?`.

Turn 1 starts from a brief pre-filled from the frontmatter and that row:

```
$ research-buddy turn1 heat-pumps_v1.0-source.md
pre-filled from the top queue row Q-001 (Radiator sizing).
...
<!-- @brief-start -->
I am working on a Retrofitting heat pumps into pre-1950 houses (deliverable: plan;
goal: A go/no-go decision and sizing plan for one house). I'm trying to decide
Radiator sizing.

I need you to do a deep research that allows you to answer these questions: Can
existing radiators deliver design heat load at 45 C flow?.
...
Accepted sources will be: Tier 1 (primary, supports VALIDATED): Peer-reviewed
building-physics journals; national energy agencies. Tier 2 (official secondary):
Manufacturer datasheets; installer handbooks.
...
<!-- @brief-end -->
```

Turn 2 writes the next version. The mechanical edits are one command, and the
result is checked against the append-only rules:

```
$ research-buddy bump heat-pumps_v1.0-source.md Q-001 --apply
── heat-pumps_v1.0-source.md → heat-pumps_v1.1-source.md ──
  topic: Radiator sizing
  queue: removed row Q-001 (Radiator sizing)
  tracker: appended row Q-001 (v1.1)
  sessions: inserted skeleton for Q-001
  changelog: prepended v1.1 entry
  references: prepended v1.1 subsection
  frontmatter: version → 1.1, date → 2026-10-20
  → wrote heat-pumps_v1.1-source.md

$ research-buddy diff-summary heat-pumps_v1.0-source.md heat-pumps_v1.1-source.md
<!-- @summary-start -->
{{Narrative — 1-3 plain-language sentences on what this version accomplished. ...}}

- Version: v1.0 → v1.1
- Queue: Q-001 → tracker.
- Session notes: +Q-001.
- Append-only invariant: PASS
<!-- @summary-end -->

$ research-buddy build heat-pumps_v1.1-source.md
Reading heat-pumps_v1.1-source.md…
Building HTML…
Written → versions/heat-pumps_v1.1.html
Written → heat-pumps.html (207 KB)
```

`starter-example/starter-md.html` is a pre-built render of the bundled template.

## Use with AI agents

There is no MCP server. Agents use Research Buddy in these ways:

- **Chat assistants (no shell).** Attach the `*-source.md` file. The framework at
  the top of the document is the agent's instructions: session zero, the two-turn
  protocol, source tiers, failure modes. The starter is
  [`starter.md`](https://raw.githubusercontent.com/nuncaeslupus/research-buddy/main/src/research_buddy/starter.md)
  (also `research_buddy/starter.md` in the installed package).
- **Agents with a shell** (Claude Code, Codex, etc.) drive the CLI for the
  mechanical steps and keep the judgement for themselves:

  | Step | Command |
  |---|---|
  | Turn 1 brief skeleton | `research-buddy turn1 <source>` |
  | Where to insert a rule, DA or entry | `research-buddy locate <source> <anchor>` |
  | Turn 2 queue-to-tracker move, stubs, version bump | `research-buddy bump <source> <Q-id> --apply` |
  | Turn 2 change summary | `research-buddy diff-summary <old> <new>` |
  | Check before handing back | `research-buddy validate <new> --prior <old>` |
  | Render for the user | `research-buddy build <source>` |

  Exit codes are scriptable: `validate` returns `1` on errors (`2` if the `--prior`
  file is missing); `diff-summary` returns `1` on an append-only violation;
  `upgrade` returns `1` when a dry run finds changes and `2` on error. Slots the
  agent must fill are left as `{{...}}` placeholders.

## How it works

- **One file is the source of truth.** `*_vX.Y-source.md` is YAML frontmatter plus
  a Markdown body with HTML-comment anchors (`<!-- @anchor: ... -->`,
  `<!-- @rule: ... -->`, `<!-- @da: ... -->`). The clean view `*_vX.Y.md` and the
  HTML are derived. Each top-level `## H2` becomes a tab.
- **Two turns per session.** Turn 1: brief, then discovery with inline Tier 1
  citations, then **stop** for results from other researchers (other AIs, human
  experts). Turn 2: vet each finding, resolve pre-registered hypotheses, write the
  next version atomically. New topics go to the queue, not into the current session.
- **Append-only history.** Tracker rows, discarded alternatives, references and
  changelog entries never disappear; `validate --prior` enforces it.
- **Every session is a new file**: `_v1.0`, `_v1.1`, ... The HTML build keeps a
  copy per version in `versions/`.

## Commands

| Command | What it does |
|---|---|
| `init <dir> [--title] [--subtitle]` | Scaffold `source/research-document.md` and `versions/` |
| `build <source...> [--output] [--theme] [--no-versioning]` | Render single-file HTML (tabs, sidebar, theme toggle). Strips the framework, sanitizes agent HTML, aborts on validation errors |
| `validate <source...> [--prior <old>]` | Frontmatter, anchor pairing, links, ID uniqueness, unsafe-HTML warnings; with `--prior`, append-only checks |
| `clean <source...> [-o]` | Write the shareable clean view `{file_name}_v{version}.md` |
| `turn1 <source>` | Print the Turn 1 brief skeleton |
| `bump <source> <Q-id> [--apply] [--force] [--no-validate]` | Turn 2 mechanical edits into a new versioned file (dry run without `--apply`) |
| `locate <source> <anchor> [--context N]` | Line of the live `@end` marker, fence-aware |
| `diff-summary <old> <new>` | Mechanical part of the Turn 2 `@summary` block |
| `upgrade <source...> [--apply] [--no-validate]` | Refresh the framework block and frontmatter from the installed starter (dry run without `--apply`) |
| `migrate-v1-to-v2 <json...> [-o] [--force]` | Convert a legacy v1 JSON document (current releases no longer read v1) |

Run `research-buddy <command> --help` for full options.

**Language.** `language` in the frontmatter (`"Spanish"` or `{code: es, label: Español}`)
sets the HTML `lang` and, for shipped languages (currently Spanish), displays the
framework's section headings translated while keeping English slugs so links still
resolve. Override or add labels with a `section_labels:` mapping:

```yaml
section_labels:
  Open Research Queue: Cola de tareas
```

**Versions.** Each document records `research_buddy_version` in its frontmatter.
After upgrading the CLI, run `research-buddy upgrade <file> --apply`.

## Security

Documents are Markdown written by an LLM and rendered to HTML you open in a
browser, so injected `<script>`, `on*=` handlers and `javascript:` links are in
scope.

- `validate` warns on them (`unsafe-html-script`, `-event-handler`, `-js-uri`).
- `build` runs every agent-authored fragment through [`nh3`](https://nh3.readthedocs.io/)
  with an allowlist matching the framework's elements. Scripts, event handlers,
  `javascript:`/`data:` URIs, `<iframe>`, `<object>` and `<foreignObject>` are removed;
  prose, tables, callouts, status chips and inline SVG (itself sanitized) are kept.
- A `theme_css` file is inlined with `</style>` neutralized.

This protects the rendered HTML; the source file is still yours to trust.

## Limitations

- It does not call any AI model or search engine. The research is done by the
  assistant you upload the file to; the CLI only handles the file.
- The HTML is output only; the `*-source.md` is the one file to edit and upload.

## Development

```bash
make sync                  # install dev dependencies (uv)
make lint                  # ruff + mypy + version-sync check
make test                  # test suite
make test-cov              # suite + coverage gate (what CI runs)
make check-examples-sync   # starter-example/*.html is up to date
make regen-examples        # regenerate it
```

The version lives in `pyproject.toml`; `make version-sync` propagates it, including
to this README's heading.

## Related projects

- [claude-arsenal](https://github.com/nuncaeslupus/claude-arsenal) — spec-driven Claude Code workflow and gated task queue.
- [drawspec](https://github.com/nuncaeslupus/drawspec) — declarative diagram spec → clean SVG/PNG/text, writable by LLMs; MCP server included.
- [doc-control](https://github.com/nuncaeslupus/doc-control) — lets AI agents edit Word documents as tracked changes.
- [literary-critic](https://github.com/nuncaeslupus/literary-critic) — LLM manuscript analysis the way a professional editor would.
- [integral-job-search](https://github.com/nuncaeslupus/integral-job-search) — candidate-centred job search run in Claude Code.

## License

MIT
