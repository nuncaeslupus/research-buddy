"""`init` command — scaffold a new v2 Markdown documentation project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research_buddy.commands._shared import _load_starter_md_text
from research_buddy.fileio import atomic_write


def cmd_init(args: argparse.Namespace) -> int:
    """Scaffold a new v2 Markdown documentation project."""
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


def _init_v2(args: argparse.Namespace) -> int:
    """v2 Markdown scaffolding."""
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
