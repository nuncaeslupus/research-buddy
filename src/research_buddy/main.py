"""CLI entry point — research-docs build|init|validate|upgrade|clean|migrate-v1-to-v2.

`build`, `validate`, and `upgrade` dispatch on file extension. `.md` paths use
the v2 Markdown pipeline (`build_md`, `validator_md`, `upgrade_md`); other
paths use the v1 JSON pipeline. `validate --prior FILE` enables diff-based
checks (anchor preservation + append-only invariants) on `.md` files.

`init` defaults to v2 Markdown scaffolding; pass `--v1` for the legacy JSON
form. `clean` and `migrate-v1-to-v2` are v2-only by definition.
"""

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
from research_buddy.build_md import build_md_html
from research_buddy.clean_md import clean_md
from research_buddy.clean_md import parse_frontmatter as parse_md_frontmatter
from research_buddy.migrate_v1_to_v2 import (
    derive_output_path as derive_md_output_path,
)
from research_buddy.migrate_v1_to_v2 import (
    migrate as migrate_v1_to_v2,
)
from research_buddy.upgrade import docs_equivalent, stamp_format_note, upgrade_doc
from research_buddy.upgrade_md import UpgradeError, upgrade_md
from research_buddy.validator import validate
from research_buddy.validator_md import validate_md


def _resolve_source(path: Path) -> tuple[Path, Path] | None:
    """Given a path (file or dir), return (json_path, project_root).

    Project root is the directory containing source/ and versions/.
    Returns None if no versioned document (*_v*.json) is found.
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
    no_versioning: bool = False,
) -> int:
    """Run a single build pass."""
    print(f"Reading {json_path.name}\u2026")
    with json_path.open(encoding="utf-8") as f:
        doc = json.load(f)

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
        print(f"Written \u2192 versions/{versioned_name}")
    else:
        # Just write to stable path
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        with stable_path.open("w", encoding="utf-8") as f:
            f.write(html)

    size_kb = len(html.encode()) / 1024
    print(f"Written \u2192 {stable_path} ({size_kb:.0f} KB)")

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
        print(f"Generating PDF \u2192 {pdf_path.name}\u2026")
        try:
            HTML(string=html).write_pdf(pdf_path)
            print(f"Written \u2192 {pdf_path}")
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
    text = md_path.read_text(encoding="utf-8")

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
    if theme_path.exists():
        theme_css = theme_path.read_text(encoding="utf-8")
        print(f"Using theme: {theme_path.name}")

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

                def _version_key(p: Path) -> tuple[int, int]:
                    # Match only the _vMAJOR.MINOR suffix so project names that contain
                    # digits (e.g. "2024_report_v1.0.json") still sort by version.
                    m = re.search(r"_v(\d+)[_.](\d+)\.json$", p.name)
                    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

                json_files = sorted(
                    [
                        p
                        for p in source_dir.glob("*.json")
                        if re.search(r"_v\d+[_.]\d+\.json$", p.name)
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
            print(f"Validating {json_path.name}\u2026")
            with json_path.open(encoding="utf-8") as f:
                doc = json.load(f)
            issues = validate(doc)
            if issues:
                print(f"\n\u26a0  {len(issues)} issue(s) in {json_path.name}:")
                for issue in issues:
                    print(f"   {issue}")
                exit_code = 1
            else:
                print(f"\u2714  {json_path.name}: No issues found.")
        else:
            rc = perform_build(
                json_path, project_root, args.theme, args.output, args.pdf, args.no_versioning
            )
            if rc != 0:
                exit_code = rc

    return exit_code


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate document(s) without building.

    Dispatches on file extension: .md → v2 Markdown validator; all other paths
    → v1 JSON validator (existing behavior). The --prior flag enables diff-based
    checks for .md files; it is silently ignored when validating .json files.
    """
    exit_code = 0
    prior_path: Path | None = None
    if getattr(args, "prior", None):
        prior_path = Path(args.prior).resolve()
        if not prior_path.is_file():
            print(f"Error: --prior {prior_path} not found.", file=sys.stderr)
            return 2

    for p in args.paths:
        path = Path(p).resolve()

        # ── v2 Markdown ─────────────────────────────────────────────────────
        if path.suffix == ".md":
            if not path.is_file():
                print(f"Error: {path} not found.", file=sys.stderr)
                exit_code = 1
                continue

            print(f"Validating {path.name}\u2026")
            md_issues = validate_md(path, prior=prior_path)
            errors = [i for i in md_issues if i.severity == "error"]
            warnings = [i for i in md_issues if i.severity == "warning"]
            infos = [i for i in md_issues if i.severity == "info"]

            if not md_issues:
                print(f"\u2714  {path.name}: No issues found.")
            else:
                summary_parts = [f"{len(errors)} error(s)"]
                if warnings:
                    summary_parts.append(f"{len(warnings)} warning(s)")
                if infos:
                    summary_parts.append(f"{len(infos)} info")
                print(f"\n\u26a0  {', '.join(summary_parts)} in {path.name}:")
                for md_issue in md_issues:
                    line_str = f" (line {md_issue.line})" if md_issue.line else ""
                    sev = md_issue.severity.upper()
                    print(f"   [{sev}] {md_issue.code}: {md_issue.message}{line_str}")
                if errors:
                    exit_code = 1
            continue

        # ── v1 JSON ─────────────────────────────────────────────────────────
        res = _resolve_source(path)
        if not res:
            print(f"Error: no versioned document (*_v*.json) found for {path}", file=sys.stderr)
            exit_code = 1
            continue
        json_path, _root = res

        print(f"Validating {json_path.name}\u2026")
        with json_path.open(encoding="utf-8") as f:
            doc = json.load(f)

        issues = validate(doc)
        if issues:
            print(f"\n\u26a0  {len(issues)} issue(s) in {json_path.name}:")
            for issue in issues:
                print(f"   {issue}")
            exit_code = 1
        else:
            print(f"\u2714  {json_path.name}: No issues found.")

    return exit_code


def cmd_migrate(args: argparse.Namespace) -> int:
    """Migrate v1 JSON document(s) to v2 Markdown."""
    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix != ".json":
            print(
                f"Error: `migrate-v1-to-v2` only processes .json files; got {path.name}",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        if not path.is_file():
            print(f"Error: {path} not found.", file=sys.stderr)
            exit_code = 1
            continue

        try:
            with path.open(encoding="utf-8") as f:
                doc = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: {path.name} is not valid JSON: {e}", file=sys.stderr)
            exit_code = 2
            continue

        # Resolve output path: -o wins; otherwise derive from doc + input dir
        out = Path(args.output).resolve() if args.output else derive_md_output_path(path, doc)

        if out.exists() and not args.force:
            print(
                f"Error: {out} already exists. Use --force to overwrite, or specify -o.",
                file=sys.stderr,
            )
            exit_code = 2
            continue

        try:
            text = migrate_v1_to_v2(doc)
            out.write_text(text, encoding="utf-8")
        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}", file=sys.stderr)
            exit_code = 2
            continue

        src_size = path.stat().st_size
        out_size = out.stat().st_size
        print(f"\u2714  {path.name} \u2192 {out.name} ({src_size:,} \u2192 {out_size:,} bytes)")
        print(f"   Next: research-buddy validate {out.name}")
    return exit_code


def cmd_clean(args: argparse.Namespace) -> int:
    """Generate clean-view .md from v2 source file(s)."""
    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix != ".md":
            print(
                f"Error: `clean` only processes v2 Markdown files; got {path.name}",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        if not path.is_file():
            print(f"Error: {path} not found.", file=sys.stderr)
            exit_code = 1
            continue

        try:
            out = clean_md(path, Path(args.output).resolve() if args.output else None)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            exit_code = 2
            continue

        src_size = path.stat().st_size
        out_size = out.stat().st_size
        pct = (1 - out_size / src_size) * 100 if src_size else 0
        print(
            f"\u2714  {path.name} \u2192 {out.name} "
            f"({src_size:,} \u2192 {out_size:,} bytes, {pct:.0f}% smaller)"
        )
    return exit_code


def _load_starter_template() -> dict[str, Any]:
    """Load the starter template from package assets."""
    ref = resources.files("research_buddy") / "starter.json"
    with ref.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _load_starter_md_text() -> str:
    """Load the v2 starter Markdown text from package assets."""
    ref = resources.files("research_buddy") / "starter.md"
    with ref.open("r", encoding="utf-8") as f:
        return f.read()


def _upgrade_md_file(path: Path, args: argparse.Namespace) -> int:
    """Upgrade a single v2 Markdown source file. Returns exit code (0/1/2)."""
    from research_buddy import __version__

    try:
        starter_text = _load_starter_md_text()
    except Exception as e:
        print(f"Error loading starter.md: {e}", file=sys.stderr)
        return 2

    if not path.exists():
        print(f"Error: {path} does not exist", file=sys.stderr)
        return 2

    print(f"── {path.name} ──")
    source_text = path.read_text(encoding="utf-8")

    try:
        upgraded, changes = upgrade_md(source_text, starter_text, __version__)
    except UpgradeError as e:
        print(f"  Error: {e}", file=sys.stderr)
        return 2

    if not changes:
        print("  Already in sync with starter.md.")
        print()
        return 0

    for line in changes:
        print(f"  {line}")

    if not args.apply:
        print("  (dry-run — pass --apply to write)")
        print()
        return 1

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(upgraded, encoding="utf-8")
    tmp.replace(path)
    print(f"  → wrote {path}")

    exit_code = 0
    if not args.no_validate:
        issues = validate_md(path)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            print(f"  ⚠  {len(errors)} validation error(s) after upgrade:")
            for issue in errors:
                print(f"     {issue}")
            exit_code = 2
    print()
    return exit_code


def cmd_upgrade(args: argparse.Namespace) -> int:
    """Refresh project source(s) against the installed starter template.

    Dispatches on file extension: `.md` paths use the v2 Markdown upgrade
    (framework block + frontmatter migration); other paths use the v1 JSON
    upgrade (agent_guidelines refresh + key reordering).
    """
    from research_buddy import __version__

    try:
        starter = _load_starter_template()
    except Exception as e:
        print(f"Error loading starter template: {e}", file=sys.stderr)
        return 2

    exit_code = 0
    for p in args.paths:
        path = Path(p).resolve()
        if path.suffix == ".md":
            exit_code = max(exit_code, _upgrade_md_file(path, args))
            continue

        res = _resolve_source(path)
        if not res:
            print(
                f"Error: no versioned document (*_v*.json) found for {path}",
                file=sys.stderr,
            )
            exit_code = 2
            continue
        json_path, _root = res

        print(f"── {json_path.name} ──")
        with json_path.open(encoding="utf-8") as f:
            doc = json.load(f)

        upgraded, changes, key_diffs = upgrade_doc(doc, starter, __version__)

        if docs_equivalent(doc, upgraded):
            print("  Already in sync with starter.json.")
            print()
            continue

        for line in changes:
            print(f"  {line}")

        diff_lines = [
            f"    {label}: {', '.join(keys)}" for label, keys in key_diffs.items() if keys
        ]
        if diff_lines:
            print("  Framework / session_protocol key changes:")
            for line in diff_lines:
                print(line)

        if not args.apply:
            print("  (dry-run — pass --apply to write)")
            print()
            exit_code = 1
            continue

        stamp_format_note(upgraded, __version__)
        tmp = json_path.with_suffix(json_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(upgraded, f, indent=2, ensure_ascii=False)
            f.write("\n")
        tmp.replace(json_path)
        print(f"  → wrote {json_path}")

        if not args.no_validate:
            issues = validate(upgraded)
            if issues:
                print(f"  \u26a0  {len(issues)} issue(s) after upgrade:")
                for issue in issues:
                    print(f"     {issue}")
                exit_code = 2
        print()

    return exit_code


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
    with doc_path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

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
    doc_path.write_text(text, encoding="utf-8")

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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="research-buddy",
        description=(
            "Generate high-fidelity research documentation from structured JSON or Markdown."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="Build HTML from document JSON(s) in order")
    p_build.add_argument(
        "paths",
        nargs="+",
        help="JSON file(s) or directory(ies) containing source/. Processed IN ORDER.",
    )
    p_build.add_argument("--all", action="store_true", help="Build all JSON files in the directory")
    p_build.add_argument("--theme", help="CSS file with style overrides")
    p_build.add_argument(
        "--output", help="Output filename or path (default: {meta.file_name}.html)"
    )
    p_build.add_argument("--validate-only", action="store_true", help="Validate without building")
    p_build.add_argument(
        "--no-versioning", action="store_true", help="Skip creating versioned HTML in versions/"
    )
    p_build.add_argument(
        "--watch", action="store_true", help="Watch for changes and rebuild automatically"
    )
    p_build.add_argument("--pdf", action="store_true", help="Generate PDF export")

    # validate
    p_val = sub.add_parser(
        "validate",
        help="Validate document without building (supports .json and .md)",
    )
    p_val.add_argument(
        "paths",
        nargs="+",
        help="File(s) or directory(ies) to validate. .md files use the v2 validator; "
        "everything else uses the v1 JSON validator.",
    )
    p_val.add_argument(
        "--prior",
        default=None,
        help="Optional prior version of the same .md file (enables anchor-preservation "
        "and append-only checks). Ignored for .json files.",
    )

    # clean
    p_clean = sub.add_parser(
        "clean",
        help="Generate clean-view .md from a v2 source file (strips framework block)",
    )
    p_clean.add_argument(
        "paths",
        nargs="+",
        help="One or more *_v*-source.md files to clean",
    )
    p_clean.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path (default: {file_name}_v{version}.md alongside source). "
        "Only meaningful when a single file is passed.",
    )

    # migrate-v1-to-v2
    p_mig = sub.add_parser(
        "migrate-v1-to-v2",
        help="Migrate a v1 JSON research document to v2 Markdown",
    )
    p_mig.add_argument(
        "paths",
        nargs="+",
        help="One or more v1 .json files to migrate",
    )
    p_mig.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output .md path (default: {file_name}_v{version}-source.md alongside input). "
        "Only meaningful when a single file is passed.",
    )
    p_mig.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )

    # init
    p_init = sub.add_parser(
        "init",
        help="Scaffold a new documentation project (v2 Markdown by default; --v1 for legacy JSON)",
    )
    p_init.add_argument("path", help="Target directory")
    p_init.add_argument("--title", help="Project title")
    p_init.add_argument("--subtitle", help="Project subtitle")
    p_init.add_argument(
        "--ver",
        default="1.0",
        help="Initial version (default: 1.0). Applied to v1 JSON only; v2 starts null.",
    )
    p_init.add_argument(
        "--v1",
        action="store_true",
        help="Scaffold a legacy v1 JSON project instead of the default v2 Markdown",
    )

    # upgrade
    p_up = sub.add_parser(
        "upgrade",
        help=(
            "Refresh project source(s) against the installed starter template. "
            ".json → v1 agent_guidelines refresh; .md → v2 framework block + "
            "frontmatter migration."
        ),
    )
    p_up.add_argument(
        "paths",
        nargs="+",
        help=(
            "Path(s) to upgrade. JSON file or directory containing source/ for "
            "v1; .md source file for v2."
        ),
    )
    p_up.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk (default is dry-run)",
    )
    p_up.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip `research-buddy validate` after applying",
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    handlers = {
        "build": cmd_build,
        "validate": cmd_validate,
        "clean": cmd_clean,
        "migrate-v1-to-v2": cmd_migrate,
        "init": cmd_init,
        "upgrade": cmd_upgrade,
    }
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
