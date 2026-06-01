"""CLI wiring — argparse parser construction and dispatch.

`build`, `validate`, and `upgrade` dispatch on file extension. `.md` paths use
the v2 Markdown pipeline (`build_md`, `validator_md`, `upgrade_md`); other
paths use the v1 JSON pipeline. `validate --prior FILE` enables diff-based
checks (anchor preservation + append-only invariants) on `.md` files.

`init` defaults to v2 Markdown scaffolding; pass `--v1` for the legacy JSON
form. `clean` and `migrate-v1-to-v2` are v2-only by definition.
"""

from __future__ import annotations

import argparse
import sys

import argcomplete

from research_buddy.commands.build import cmd_build
from research_buddy.commands.bump import cmd_bump
from research_buddy.commands.clean import cmd_clean
from research_buddy.commands.init import cmd_init
from research_buddy.commands.migrate import cmd_migrate
from research_buddy.commands.upgrade import cmd_upgrade
from research_buddy.commands.validate import cmd_validate


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the research-buddy CLI."""
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

    # bump
    p_bump = sub.add_parser(
        "bump",
        help=(
            "Perform the mechanical Turn-2 edits for one researched queue item "
            "(version/date, queue→tracker, session/changelog/references stubs)"
        ),
    )
    p_bump.add_argument("path", help="Path to the *_v*-source.md file to bump")
    p_bump.add_argument("queue_id", help="Queue item ID to close, e.g. Q-003")
    p_bump.add_argument(
        "--apply",
        action="store_true",
        help="Write the new {file_name}_v{version}-source.md (default is dry-run)",
    )
    p_bump.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )
    p_bump.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip `research-buddy validate` after applying",
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

    return parser


def main() -> None:
    parser = build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    handlers = {
        "build": cmd_build,
        "validate": cmd_validate,
        "clean": cmd_clean,
        "bump": cmd_bump,
        "migrate-v1-to-v2": cmd_migrate,
        "init": cmd_init,
        "upgrade": cmd_upgrade,
    }
    sys.exit(handlers[args.command](args))
