"""`init` command — scaffold a new documentation project (v2 MD default, --v1 JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from research_buddy.commands._shared import _load_starter_md_text, _load_starter_template
from research_buddy.fileio import atomic_write


def cmd_init(args: argparse.Namespace) -> int:
    """Scaffold a new documentation project.

    Default: v2 Markdown. Pass `--v1` for the legacy JSON form.
    """
    if getattr(args, "v1", False):
        return _init_v1(args)
    return _init_v2(args)


def _prepare_init_dirs(args: argparse.Namespace) -> tuple[Path, Path] | None:
    """Validate and create source/ + versions/ under the target directory.

    Returns (source_dir, versions_dir) on success, or None when the target
    already contains a populated source/ (in which case the helper has
    already printed the error and the caller should return 1).
    """
    target = Path(args.path).resolve()
    source_dir = target / "source"
    versions_dir = target / "versions"

    if source_dir.exists() and any(source_dir.iterdir()):
        print(f"Error: {source_dir} already contains files.", file=sys.stderr)
        return None

    source_dir.mkdir(parents=True, exist_ok=True)
    versions_dir.mkdir(parents=True, exist_ok=True)
    return source_dir, versions_dir


def _rel_to_cwd(p: Path) -> str:
    try:
        return str(p.relative_to(Path.cwd()))
    except ValueError:
        return str(p)


def _init_v1(args: argparse.Namespace) -> int:
    """Legacy JSON scaffolding (`--v1`)."""
    print(
        "Warning: v1 JSON format is deprecated and will be removed in v2.0. "
        "Use `research-buddy init` (without --v1) to create v2 Markdown projects.",
        file=sys.stderr,
    )
    dirs = _prepare_init_dirs(args)
    if dirs is None:
        return 1
    source_dir, _ = dirs

    try:
        doc = _load_starter_template()
    except Exception as e:
        print(f"Error loading starter template: {e}", file=sys.stderr)
        return 1

    if args.title:
        doc["meta"]["title"] = args.title
        # Keep the first section's title aligned with the project title while
        # preserving sibling order (Objective before Quick Links).
        overview_sections = doc["tabs"][0]["sections"]
        if overview_sections:
            old_title = next(iter(overview_sections))
            new_sections = {args.title: overview_sections.pop(old_title)}
            new_sections.update(overview_sections)
            doc["tabs"][0]["sections"] = new_sections
        doc["meta"]["title_page_section_title"] = args.title
    if args.subtitle:
        doc["meta"]["subtitle"] = args.subtitle
    if args.ver:
        doc["meta"]["version"] = args.ver

    doc["meta"]["date"] = datetime.now(tz=UTC).strftime("%B %Y")

    doc_path = source_dir / "research-document.json"
    atomic_write(doc_path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    target = Path(args.path).resolve()
    rb_ver = doc["meta"].get("research_buddy_version", "?")
    print(f"Created {_rel_to_cwd(target)}/")
    print(f"  source/research-document.json  (Research Buddy v{rb_ver} v1 JSON template)")
    print("  versions/")
    print()
    print("Next steps:")
    print(f"  1. Upload {_rel_to_cwd(doc_path)} to your AI assistant")
    print("  2. The agent will run session_zero and produce [meta.file_name]_v1.0.json")
    print("  3. research-buddy build [meta.file_name]_v1.0.json")
    print("  4. Open [meta.file_name].html in a browser")
    return 0


def _init_v2(args: argparse.Namespace) -> int:
    """v2 Markdown scaffolding (default)."""
    from research_buddy import __version__

    dirs = _prepare_init_dirs(args)
    if dirs is None:
        return 1
    source_dir, _ = dirs

    try:
        text = _load_starter_md_text()
    except Exception as e:
        print(f"Error loading starter.md: {e}", file=sys.stderr)
        return 1

    if args.title:
        text = _set_frontmatter_scalar(text, "title", args.title)
    if args.subtitle:
        text = _set_frontmatter_scalar(text, "subtitle", args.subtitle)

    doc_path = source_dir / "research-document.md"
    atomic_write(doc_path, text)

    target = Path(args.path).resolve()
    print(f"Created {_rel_to_cwd(target)}/")
    print(f"  source/research-document.md  (Research Buddy v{__version__} v2 Markdown template)")
    print("  versions/")
    print()
    print("Next steps:")
    print(f"  1. Upload {_rel_to_cwd(doc_path)} to your AI assistant")
    print("  2. The agent will run session_zero and produce [file_name]_v1.0-source.md")
    print("  3. research-buddy build source/[file_name]_v1.0-source.md")
    print("  4. Open [file_name].html in a browser")
    return 0


def _set_frontmatter_scalar(text: str, key: str, value: str) -> str:
    """Set a top-level frontmatter scalar to a double-quoted string value.

    Operates line-based to preserve YAML comments and surrounding formatting.
    Only mutates the first occurrence of `^{key}:` between the leading and
    closing `---` delimiters; no-op when the frontmatter or key is absent.

    `value` is escaped for YAML's double-quoted form (backslash and
    double-quote get backslash-escaped) so titles like `My "Awesome"
    Project` round-trip safely.

    Precondition: the matched line's existing value is unquoted scalar
    (e.g. `null`) — we use a naive ` #` split to detect any trailing
    comment, which would mis-fire on an existing quoted value containing
    `#`. This holds for `init`'s actual call sites (always operating on
    the fresh starter's `null` lines).
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return text
    fm_end = -1
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            fm_end = i
            break
    if fm_end < 0:
        return text

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    prefix = f"{key}:"
    for i in range(1, fm_end):
        line = lines[i]
        if not line.startswith(prefix):
            continue
        after_colon = line.split(":", 1)[1]
        comment = ""
        if " #" in after_colon:
            _, comment_body = after_colon.split(" #", 1)
            comment = "  # " + comment_body.lstrip()
        lines[i] = f'{key}: "{escaped}"{comment}'.rstrip()
        break

    out = "\n".join(lines)
    if text.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out
