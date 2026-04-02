"""CLI entry point — research-docs build|init|validate."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from research_docs.build import build_html, find_latest_json


def _resolve_source(path: Path) -> tuple[Path, Path]:
    """Given a path (file or dir), return (json_path, project_root).

    Project root is the directory containing source/ and versions/.
    """
    if path.is_file():
        # source/document_v1.0.json -> project root is source/..
        if path.parent.name == "source":
            return path, path.parent.parent
        return path, path.parent

    # directory: look for source/ subdir
    source_dir = path / "source" if (path / "source").is_dir() else path
    latest = find_latest_json(source_dir)
    if not latest:
        print(f"Error: no document_v*.json found in {source_dir}", file=sys.stderr)
        sys.exit(1)
    project_root = path if (path / "source").is_dir() else path.parent
    return latest, project_root


def cmd_build(args: argparse.Namespace) -> int:
    """Build HTML from a document JSON."""
    path = Path(args.path).resolve()
    json_path, project_root = _resolve_source(path)

    print(f"Reading {json_path.name}\u2026")
    with open(json_path, encoding="utf-8") as f:
        doc = json.load(f)

    # validate first
    from research_docs.schema import validate

    issues = validate(doc)
    if issues:
        print(f"\n\u26a0  {len(issues)} issue(s) found:")
        for issue in issues:
            print(f"   {issue}")
        print()

    if args.validate_only:
        return 1 if issues else 0

    # load optional theme CSS
    theme_css = None
    theme_path = Path(args.theme) if args.theme else project_root / "theme.css"
    if theme_path.exists():
        theme_css = theme_path.read_text(encoding="utf-8")
        print(f"Using theme: {theme_path.name}")

    print("Building HTML\u2026")
    html = build_html(doc, theme_css=theme_css)

    # output paths
    versions_dir = project_root / "versions"
    versions_dir.mkdir(exist_ok=True)

    import re

    m = re.search(r"v(\d+)[_.](\d+)", json_path.name)
    if m:
        versioned_name = f"v{m.group(1)}.{m.group(2)}.html"
    else:
        versioned_name = "output.html"

    versioned_path = versions_dir / versioned_name
    output_name = args.output or "docs.html"
    stable_path = project_root / output_name

    with open(versioned_path, "w", encoding="utf-8") as f:
        f.write(html)
    shutil.copy2(versioned_path, stable_path)

    size_kb = len(html.encode()) / 1024
    print(f"Written \u2192 versions/{versioned_name}  ({size_kb:.0f} KB)")
    print(f"Copied  \u2192 {output_name}")

    return 1 if issues else 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a document without building."""
    path = Path(args.path).resolve()
    json_path, _root = _resolve_source(path)

    print(f"Validating {json_path.name}\u2026")
    with open(json_path, encoding="utf-8") as f:
        doc = json.load(f)

    from research_docs.schema import validate

    issues = validate(doc)
    if issues:
        print(f"\n\u26a0  {len(issues)} issue(s):")
        for issue in issues:
            print(f"   {issue}")
        return 1

    print("\u2714  No issues found.")
    return 0


STARTER_DOCUMENT = {
    "meta": {
        "version": "1.0",
        "date": "",
        "title": "My Research Document",
        "subtitle": "Research \u00b7 Analysis \u00b7 Implementation",
        "title_page_section": "ov-intro",
    },
    "tabs": [
        {
            "id": "overview",
            "label": "Overview",
            "nav": [
                {
                    "label": "Overview",
                    "items": [{"href": "ov-intro", "label": "Introduction"}],
                }
            ],
            "sections": ["ov-intro"],
        },
        {
            "id": "content",
            "label": "Content",
            "nav": [
                {
                    "label": "Sections",
                    "items": [{"href": "s1", "label": "1. First Section"}],
                }
            ],
            "sections": ["s1"],
        },
        {
            "id": "changelog",
            "label": "Changelog",
        },
    ],
    "sections": {
        "ov-intro": {
            "blocks": [
                {
                    "type": "p",
                    "md": (
                        "Welcome to your research document."
                        " Edit `source/document_v1.0.json` to add content."
                    ),
                },
                {
                    "type": "callout",
                    "variant": "blue",
                    "title": "Getting Started",
                    "md": (
                        "Add sections to `sections`, reference them in"
                        " `tabs[].sections`, and add nav links in `tabs[].nav`."
                    ),
                },
            ]
        },
        "s1": {
            "title": "1. First Section",
            "blocks": [
                {
                    "type": "h3",
                    "id": "s1-1",
                    "md": "1.1 Subsection Example",
                },
                {
                    "type": "p",
                    "md": "This is a paragraph with **bold**, *italic*, and `inline code`.",
                },
                {
                    "type": "table",
                    "headers": ["Column A", "Column B", "Column C"],
                    "rows": [
                        ["Row 1", "Data", "Value"],
                        ["Row 2", "Data", "Value"],
                    ],
                },
                {
                    "type": "code",
                    "lang": "python",
                    "text": "def hello():\n    print('Hello from research-docs!')",
                },
            ],
        },
    },
    "changelog": {
        "entries": [
            {
                "id": "cl-v10",
                "version": "v1.0",
                "current": True,
                "paragraphs": ["Initial document."],
            }
        ],
        "protocol_blocks": [],
    },
}


def cmd_init(args: argparse.Namespace) -> int:
    """Scaffold a new documentation project."""
    target = Path(args.path).resolve()

    source_dir = target / "source"
    versions_dir = target / "versions"

    if source_dir.exists() and any(source_dir.iterdir()):
        print(f"Error: {source_dir} already contains files.", file=sys.stderr)
        return 1

    source_dir.mkdir(parents=True, exist_ok=True)
    versions_dir.mkdir(parents=True, exist_ok=True)

    # fill in date
    doc = json.loads(json.dumps(STARTER_DOCUMENT))
    doc["meta"]["date"] = datetime.now(tz=UTC).strftime("%B %Y")

    doc_path = source_dir / "document_v1.0.json"
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    print(f"Created {_rel(target)}/")
    print("  source/document_v1.0.json")
    print("  versions/")
    print()
    print("Next steps:")
    print(f"  1. Edit {_rel(doc_path)}")
    print(f"  2. research-docs build {_rel(target)}")
    print("  3. Open docs.html in a browser")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="research-docs",
        description="Generate single-file HTML documentation from structured JSON.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Build HTML from document JSON")
    p_build.add_argument("path", help="JSON file or directory containing source/")
    p_build.add_argument("--theme", help="CSS file with style overrides")
    p_build.add_argument(
        "--output", default="docs.html", help="Output filename (default: docs.html)"
    )
    p_build.add_argument(
        "--validate-only", action="store_true", help="Validate without building"
    )

    # validate
    p_val = sub.add_parser("validate", help="Validate document without building")
    p_val.add_argument("path", help="JSON file or directory containing source/")

    # init
    p_init = sub.add_parser("init", help="Scaffold a new documentation project")
    p_init.add_argument("path", help="Target directory")

    args = parser.parse_args()
    handlers = {"build": cmd_build, "validate": cmd_validate, "init": cmd_init}
    sys.exit(handlers[args.command](args))
