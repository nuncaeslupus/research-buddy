"""`build` command — render HTML from v1 JSON or v2 Markdown source files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from research_buddy.build import build_html
from research_buddy.build_md import build_md_html
from research_buddy.clean_md import parse_frontmatter as parse_md_frontmatter
from research_buddy.commands._shared import _resolve_source
from research_buddy.fileio import FileReadError, read_text_or_error
from research_buddy.validator import validate
from research_buddy.validator_md import validate_md


def perform_build(
    json_path: Path,
    project_root: Path,
    theme: str | None = None,
    output: str | None = None,
    pdf: bool = False,
    no_versioning: bool = False,
) -> int:
    """Run a single build pass."""
    print(f"Reading {json_path.name}…")
    try:
        with json_path.open(encoding="utf-8") as f:
            doc = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(
            f"Error: {json_path.name} is not valid JSON or has invalid encoding: {e}",
            file=sys.stderr,
        )
        return 1

    issues = validate(doc)
    if issues:
        print(f"\n⚠  {len(issues)} issue(s) found in {json_path.name}:")
        for issue in issues:
            print(f"   {issue}")
        print()

    # load optional theme CSS
    theme_css = None
    theme_path = Path(theme) if theme else project_root / "theme.css"
    if theme_path.is_file():
        try:
            theme_css = read_text_or_error(theme_path)
        except FileReadError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(f"Using theme: {theme_path.name}")

    print("Building HTML…")
    html = build_html(doc, theme_css=theme_css)

    # output paths
    meta = doc.get("meta", {})
    base_name = meta.get("file_name")
    if not base_name:
        # fallback: strip version/ext from filename (supports _v1.0, _v1.0.3, etc.)
        base_name = re.sub(r"_v\d+(\.\d+)*$", "", json_path.stem)

    stable_path = Path(output).resolve() if output else project_root / f"{base_name}.html"

    if not no_versioning:
        versions_dir = project_root / "versions"
        versions_dir.mkdir(exist_ok=True)

        version = meta.get("version", "1.0")
        versioned_name = f"{base_name}_v{version}.html"
        versioned_path = versions_dir / versioned_name

        with versioned_path.open("w", encoding="utf-8") as f:
            f.write(html)

        # copy to stable path
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(versioned_path, stable_path)
        print(f"Written → versions/{versioned_name}")
    else:
        # Just write to stable path
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        with stable_path.open("w", encoding="utf-8") as f:
            f.write(html)

    size_kb = len(html.encode()) / 1024
    print(f"Written → {stable_path} ({size_kb:.0f} KB)")

    if pdf:
        try:
            from weasyprint import HTML  # type: ignore[import-untyped]
        except ImportError:
            print(
                "Error: weasyprint not installed. "
                "Run 'pip install \"research-buddy[pdf]\"' to enable PDF export.",
                file=sys.stderr,
            )
            return 1

        pdf_path = stable_path.with_suffix(".pdf")
        print(f"Generating PDF → {pdf_path.name}…")
        try:
            HTML(string=html).write_pdf(pdf_path)
            print(f"Written → {pdf_path}")
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return 1

    return 1 if issues else 0


def perform_build_md(
    md_path: Path,
    project_root: Path,
    theme: str | None = None,
    output: str | None = None,
    no_versioning: bool = False,
) -> int:
    """Build HTML from a v2 Markdown source file."""
    print(f"Reading {md_path.name}…")
    try:
        text = read_text_or_error(md_path)
    except FileReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    md_issues = validate_md(md_path)
    errors = [i for i in md_issues if i.severity == "error"]
    if md_issues:
        sev_counts = (
            f"{len(errors)} error(s), "
            f"{sum(1 for i in md_issues if i.severity == 'warning')} warning(s)"
        )
        print(f"\n⚠  {sev_counts} in {md_path.name}:")
        for issue in md_issues:
            line_str = f" (line {issue.line})" if issue.line else ""
            print(f"   [{issue.severity.upper()}] {issue.code}: {issue.message}{line_str}")
        print()

    fm, _ = parse_md_frontmatter(text)
    fm = fm or {}

    # Theme cascade (highest priority first):
    # 1. Explicit `--theme PATH` CLI flag
    # 2. Frontmatter `theme_css` field (project-relative)
    # 3. Conventional `theme.css` next to the project root
    theme_css = None
    if theme:
        theme_path = Path(theme)
    elif fm.get("theme_css"):
        theme_path = (md_path.parent / str(fm["theme_css"])).resolve()
        if not theme_path.exists():
            theme_path = (project_root / str(fm["theme_css"])).resolve()
    else:
        theme_path = project_root / "theme.css"
    if theme_path.is_file():
        try:
            theme_css = read_text_or_error(theme_path)
        except FileReadError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(f"Using theme: {theme_path.name}")

    # Don't render a document the validator rejects — a broken anchor, dangling
    # cross-link, or unclosed fence produces corrupt HTML. Warnings don't block.
    if errors:
        print(
            f"Aborting: {len(errors)} validation error(s) — fix them (or build the "
            "prior version) before rendering.",
            file=sys.stderr,
        )
        return 1

    print("Building HTML…")
    html = build_md_html(text, theme_css=theme_css)

    base_name = fm.get("file_name") or re.sub(r"_v\d+(?:[._]\d+)*(?:-source)?$", "", md_path.stem)
    stable_path = Path(output).resolve() if output else project_root / f"{base_name}.html"

    if not no_versioning:
        versions_dir = project_root / "versions"
        versions_dir.mkdir(exist_ok=True)
        version = fm.get("version", "1.0")
        versioned_name = f"{base_name}_v{version}.html"
        versioned_path = versions_dir / versioned_name
        versioned_path.write_text(html, encoding="utf-8")
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(versioned_path, stable_path)
        print(f"Written → versions/{versioned_name}")
    else:
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        stable_path.write_text(html, encoding="utf-8")

    size_kb = len(html.encode()) / 1024
    print(f"Written → {stable_path} ({size_kb:.0f} KB)")
    return 1 if errors else 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build HTML from document JSON or Markdown file(s)."""
    paths = [Path(p).resolve() for p in args.paths]

    # Single-file MD dispatch — short-circuits the JSON resolver. MD files
    # don't have project source/ + versions/ scaffolding requirements.
    md_paths = [p for p in paths if p.suffix == ".md"]
    if md_paths and any(p.suffix != ".md" for p in paths):
        print(
            "Error: cannot mix .json and .md inputs in a single `build` invocation.",
            file=sys.stderr,
        )
        return 1
    if md_paths:
        if args.watch:
            print("Error: --watch is not supported for .md inputs.", file=sys.stderr)
            return 1
        if args.pdf:
            print("Error: --pdf is not yet supported for .md inputs.", file=sys.stderr)
            return 1
        exit_code = 0
        for md_path in md_paths:
            if not md_path.is_file():
                print(f"Error: {md_path} not found.", file=sys.stderr)
                exit_code = 1
                continue
            project_root = md_path.parent
            rc = perform_build_md(
                md_path, project_root, args.theme, args.output, args.no_versioning
            )
            if rc != 0:
                exit_code = rc
        return exit_code

    if args.watch:
        if len(paths) > 1:
            print("Error: --watch only supports a single path.", file=sys.stderr)
            return 1
        path = paths[0]
        res = _resolve_source(path)
        if not res:
            print(f"Error: no versioned document (*_v*.json) found for {path}", file=sys.stderr)
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
                            perform_build(
                                jp, pr, args.theme, args.output, args.pdf, args.no_versioning
                            )
                    except Exception as e:
                        print(f"Build failed: {e}")

        # Initial build
        perform_build(
            json_path, project_root, args.theme, args.output, args.pdf, args.no_versioning
        )

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

                def _version_key(p: Path) -> tuple[int, ...]:
                    # Match the _vMAJOR.MINOR(.PATCH…) suffix so project names that
                    # contain digits (e.g. "2024_report_v1.0.3.json") still sort by
                    # version. Mirrors perform_build's multi-component fallback.
                    m = re.search(r"_v(\d+(?:[_.]\d+)*)\.json$", p.name)
                    return tuple(int(x) for x in re.split(r"[_.]", m.group(1))) if m else (0,)

                json_files = sorted(
                    [
                        p
                        for p in source_dir.glob("*.json")
                        if re.search(r"_v\d+(?:[_.]\d+)*\.json$", p.name)
                    ],
                    key=_version_key,
                )
                if not json_files:
                    print(
                        f"Error: no versioned documents (*_v*.json) found in {source_dir}",
                        file=sys.stderr,
                    )
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
                    print(
                        f"Error: no versioned document (*_v*.json) found for {path}",
                        file=sys.stderr,
                    )
                    exit_code = 1
        else:
            print(f"Error: {path} does not exist.", file=sys.stderr)
            exit_code = 1

    # Build them all
    for json_path, project_root in to_build:
        if args.validate_only:
            print(f"Validating {json_path.name}…")
            try:
                with json_path.open(encoding="utf-8") as f:
                    doc = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(
                    f"Error: {json_path.name} is not valid JSON or has invalid encoding: {e}",
                    file=sys.stderr,
                )
                exit_code = 1
                continue
            issues = validate(doc)
            if issues:
                print(f"\n⚠  {len(issues)} issue(s) in {json_path.name}:")
                for issue in issues:
                    print(f"   {issue}")
                exit_code = 1
            else:
                print(f"✔  {json_path.name}: No issues found.")
        else:
            rc = perform_build(
                json_path, project_root, args.theme, args.output, args.pdf, args.no_versioning
            )
            if rc != 0:
                exit_code = rc

    return exit_code
