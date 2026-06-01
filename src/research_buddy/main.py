"""CLI entry point for research-buddy.

The implementation lives in `research_buddy.cli` (argparse wiring + dispatch)
and `research_buddy.commands.*` (one module per subcommand). This module is a
thin façade: it exposes `main` for the `research-buddy` console script and
re-exports the command handlers and helpers so existing imports
(`from research_buddy.main import cmd_build`, …) keep working.

Canonical locations:
  - parser + dispatch ............ research_buddy.cli
  - build / perform_build* ....... research_buddy.commands.build
  - validate ..................... research_buddy.commands.validate
  - clean ........................ research_buddy.commands.clean
  - migrate-v1-to-v2 ............. research_buddy.commands.migrate
  - init / _set_frontmatter_* .... research_buddy.commands.init
  - upgrade ...................... research_buddy.commands.upgrade
  - shared helpers ............... research_buddy.commands._shared
"""

from __future__ import annotations

from research_buddy.cli import build_parser, main
from research_buddy.commands._shared import (
    _load_starter_md_text,
    _load_starter_template,
    _resolve_source,
)
from research_buddy.commands.build import cmd_build, perform_build, perform_build_md
from research_buddy.commands.bump import cmd_bump
from research_buddy.commands.clean import cmd_clean
from research_buddy.commands.diff_summary import cmd_diff_summary
from research_buddy.commands.init import (
    _init_v1,
    _init_v2,
    _prepare_init_dirs,
    _rel_to_cwd,
    _set_frontmatter_scalar,
    cmd_init,
)
from research_buddy.commands.locate import cmd_locate
from research_buddy.commands.migrate import cmd_migrate
from research_buddy.commands.upgrade import _upgrade_md_file, cmd_upgrade
from research_buddy.commands.validate import cmd_validate

__all__ = [
    "_init_v1",
    "_init_v2",
    "_load_starter_md_text",
    "_load_starter_template",
    "_prepare_init_dirs",
    "_rel_to_cwd",
    "_resolve_source",
    "_set_frontmatter_scalar",
    "_upgrade_md_file",
    "build_parser",
    "cmd_build",
    "cmd_bump",
    "cmd_clean",
    "cmd_diff_summary",
    "cmd_init",
    "cmd_locate",
    "cmd_migrate",
    "cmd_upgrade",
    "cmd_validate",
    "main",
    "perform_build",
    "perform_build_md",
]


if __name__ == "__main__":
    main()
