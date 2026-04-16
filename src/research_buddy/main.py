"""CLI entry point — research-docs build|init|validate."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

import argcomplete

from research_buddy.build import build_html, find_latest_json


def _resolve_source(path: Path) -> tuple[Path, Path] | None:
    """Given a path (file or dir), return (json_path, project_root).

    Project root is the directory containing source/ and versions/.
    Returns None if no document_v*.json is found.
    """
    if path.is_file():
        # Any .json file: project root is parent, or grandparent if inside source/
        if path.parent.name == "source":
            return path, path.parent.parent
        return path, path.parent

    # directory: look for source/ subdir
    source_dir = path / "source" if (path / "source").is_dir() else path
    latest = find_latest_json(source_dir)
    if not latest:
        return None
    project_root = path if (path / "source").is_dir() else path.parent
    return latest, project_root


def perform_build(
    json_path: Path,
    project_root: Path,
    theme: str | None = None,
    output: str | None = None,
    pdf: bool = False,
) -> int:
    """Run a single build pass."""
    print(f"Reading {json_path.name}\u2026")
    with open(json_path, encoding="utf-8") as f:
        doc = json.load(f)

    # validate first
    from research_buddy.validator import validate

    issues = validate(doc)
    if issues:
        print(f"\n\u26a0  {len(issues)} issue(s) found in {json_path.name}:")
        for issue in issues:
            print(f"   {issue}")
        print()

    # load optional theme CSS
    theme_css = None
    theme_path = Path(theme) if theme else project_root / "theme.css"
    if theme_path.exists():
        theme_css = theme_path.read_text(encoding="utf-8")
        print(f"Using theme: {theme_path.name}")

    print("Building HTML\u2026")
    html = build_html(doc, theme_css=theme_css)

    # output paths
    versions_dir = project_root / "versions"
    versions_dir.mkdir(exist_ok=True)

    m = re.search(r"v(\d+)[_.](\d+)", json_path.name)
    if m:
        versioned_name = f"v{m.group(1)}.{m.group(2)}.html"
    else:
        versioned_name = "output.html"

    versioned_path = versions_dir / versioned_name
    output_name = output or "docs.html"
    stable_path = project_root / output_name

    with open(versioned_path, "w", encoding="utf-8") as f:
        f.write(html)
    shutil.copy2(versioned_path, stable_path)

    size_kb = len(html.encode()) / 1024
    print(f"Written \u2192 versions/{versioned_name}  ({size_kb:.0f} KB)")
    print(f"Copied  \u2192 {output_name}")

    if pdf:
        try:
            from weasyprint import HTML  # type: ignore[import-untyped]
        except ImportError:
            print("Error: weasyprint not installed. Run 'pip install weasyprint'.", file=sys.stderr)
            return 1

        pdf_name = output_name.replace(".html", ".pdf")
        if pdf_name == output_name:
            pdf_name += ".pdf"
        pdf_path = project_root / pdf_name
        print(f"Generating PDF \u2192 {pdf_name}\u2026")
        try:
            # WeasyPrint needs the base_url to find assets if they were external,
            # but here they are inlined in the HTML by build_html.
            HTML(string=html).write_pdf(pdf_path)
            print(f"Written \u2192 {pdf_name}")
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return 1

    return 1 if issues else 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build HTML from document JSON(s)."""
    paths = [Path(p).resolve() for p in args.paths]

    if args.watch:
        if len(paths) > 1:
            print("Error: --watch only supports a single path.", file=sys.stderr)
            return 1
        path = paths[0]
        res = _resolve_source(path)
        if not res:
            print(f"Error: no document_v*.json found for {path}", file=sys.stderr)
            return 1
        json_path, project_root = res

        try:
            from watchdog.events import FileSystemEvent, FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            print("Error: watchdog not installed. Run 'pip install watchdog'.", file=sys.stderr)
            return 1

        class BuildHandler(FileSystemEventHandler):
            def on_modified(self, event: FileSystemEvent) -> None:
                src_path = str(event.src_path)
                if src_path.endswith(".json") or src_path.endswith(".css"):
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"\n[{ts}] Change detected. Rebuilding...")
                    try:
                        res = _resolve_source(path)
                        if res:
                            jp, pr = res
                            perform_build(jp, pr, args.theme, args.output, args.pdf)
                    except Exception as e:
                        print(f"Build failed: {e}")

        # Initial build
        perform_build(json_path, project_root, args.theme, args.output, args.pdf)

        print(f"\nWatching {path} for changes... (Ctrl+C to stop)")
        observer = Observer()
        observer.schedule(BuildHandler(), str(path), recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
        return 0

    exit_code = 0
    # Collect all JSON files to build
    to_build: list[tuple[Path, Path]] = []
    for path in paths:
        if path.is_file():
            res = _resolve_source(path)
            if res:
                to_build.append(res)
            else:
                print(f"Error: {path} is not a valid document JSON.", file=sys.stderr)
                exit_code = 1
        elif path.is_dir():
            if args.all:
                source_dir = path / "source" if (path / "source").is_dir() else path
                json_files = sorted(
                    list(source_dir.glob("document_v*.json")),
                    key=lambda p: tuple(int(x) for x in re.findall(r"\d+", p.name)),
                )
                if not json_files:
                    print(f"Error: no document_v*.json found in {source_dir}", file=sys.stderr)
                    exit_code = 1
                else:
                    project_root = path if (path / "source").is_dir() else path.parent
                    for jf in json_files:
                        to_build.append((jf, project_root))
            else:
                res = _resolve_source(path)
                if res:
                    to_build.append(res)
                else:
                    print(f"Error: no document_v*.json found for {path}", file=sys.stderr)
                    exit_code = 1
        else:
            print(f"Error: path not found: {path}", file=sys.stderr)
            exit_code = 1

    # Deduplicate while preserving order
    seen = set()
    unique_to_build = []
    for jp, pr in to_build:
        if jp not in seen:
            unique_to_build.append((jp, pr))
            seen.add(jp)

    if not unique_to_build:
        return exit_code

    if len(unique_to_build) > 1:
        print(f"\u26a0  Warning: Building {len(unique_to_build)} files.")

    if args.validate_only:
        from research_buddy.validator import validate

    for json_path, project_root in unique_to_build:
        if args.validate_only:
            print(f"Validating {json_path.name}\u2026")
            with open(json_path, encoding="utf-8") as f:
                doc = json.load(f)
            issues = validate(doc)
            if issues:
                print(f"\n\u26a0  {len(issues)} issue(s) found in {json_path.name}:")
                for issue in issues:
                    print(f"   {issue}")
                exit_code = 1
        else:
            res_code = perform_build(json_path, project_root, args.theme, args.output, args.pdf)
            if res_code != 0:
                exit_code = res_code

    return exit_code


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate document(s) without building."""
    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        res = _resolve_source(path)
        if not res:
            print(f"Error: no document_v*.json found for {path}", file=sys.stderr)
            exit_code = 1
            continue
        json_path, _root = res

        print(f"Validating {json_path.name}\u2026")
        with open(json_path, encoding="utf-8") as f:
            doc = json.load(f)

        from research_buddy.validator import validate

        issues = validate(doc)
        if issues:
            print(f"\n\u26a0  {len(issues)} issue(s) in {json_path.name}:")
            for issue in issues:
                print(f"   {issue}")
            exit_code = 1
        else:
            print(f"\u2714  {json_path.name}: No issues found.")

    return exit_code


def _load_starter_template() -> dict[str, Any]:
    """Load the starter template from package assets."""
    ref = resources.files("research_buddy") / "starter.json"
    with ref.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


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

    # Load template
    try:
        doc = _load_starter_template()
    except Exception as e:
        print(f"Error loading starter template: {e}", file=sys.stderr)
        return 1

    # Fill in metadata from args if provided
    if args.title:
        doc["meta"]["title"] = args.title
        # Also update the first section title of the first tab to match the project title
        # We must preserve the dictionary order (Objective before Quick Links)
        overview_sections = doc["tabs"][0]["sections"]
        if overview_sections:
            old_title = next(iter(overview_sections))
            # Rebuild the dict to keep order
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
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    print(f"Created {_rel(target)}/")
    rb_ver = doc["meta"].get("research_buddy_version", "?")
    print(f"  source/research-document.json  (Research Buddy v{rb_ver} template)")
    print("  versions/")
    print()
    print("Next steps:")
    print(f"  1. Upload {_rel(doc_path)} to your AI assistant")
    print("  2. The agent will run session_zero and produce [project_name]_v1.0.json")
    print("  3. research-buddy build [project_name]_v1.0.json")
    print("  4. Open docs.html in a browser")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="research-buddy",
        description="Generate high-fidelity research documentation from structured JSON.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Build HTML from document JSON")
    p_build.add_argument(
        "paths", nargs="+", help="JSON file(s) or directory(ies) containing source/"
    )
    p_build.add_argument("--all", action="store_true", help="Build all JSON files in the directory")
    p_build.add_argument("--theme", help="CSS file with style overrides")
    p_build.add_argument(
        "--output", default="docs.html", help="Output filename (default: docs.html)"
    )
    p_build.add_argument("--validate-only", action="store_true", help="Validate without building")
    p_build.add_argument(
        "--watch", action="store_true", help="Watch for changes and rebuild automatically"
    )
    p_build.add_argument("--pdf", action="store_true", help="Generate PDF export")

    # validate
    p_val = sub.add_parser("validate", help="Validate document without building")
    p_val.add_argument("paths", nargs="+", help="JSON file(s) or directory(ies) containing source/")

    # init
    p_init = sub.add_parser("init", help="Scaffold a new documentation project")
    p_init.add_argument("path", help="Target directory")
    p_init.add_argument("--title", help="Project title")
    p_init.add_argument("--subtitle", help="Project subtitle")
    p_init.add_argument("--ver", default="1.0", help="Initial version (default: 1.0)")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    handlers = {"build": cmd_build, "validate": cmd_validate, "init": cmd_init}
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
