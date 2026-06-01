"""`bump` command — mechanical Turn-2 edits for one researched queue item.

`research-buddy bump <source.md> <Q-NNN>` produces the next version of a v2
source file with all the boilerplate done (frontmatter version/date, queue→
tracker move, session-notes skeleton, changelog + references stubs) and
`{{placeholders}}` left for the agent to fill. Dry-run by default; `--apply`
writes `{file_name}_v{version}-source.md` atomically and validates it against
the input as `--prior`.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from research_buddy.bump import BumpError, bump_md_text, next_minor_version
from research_buddy.clean_md import parse_frontmatter
from research_buddy.validator_md import validate_md


def cmd_bump(args: argparse.Namespace) -> int:
    """Perform the mechanical Turn-2 edits for one queue item."""
    path = Path(args.path).resolve()
    queue_id = args.queue_id.strip().upper()

    if path.suffix != ".md":
        print(f"Error: `bump` only processes v2 Markdown files; got {path.name}", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"Error: {path} not found", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)
    if fm is None:
        print(f"Error: {path.name} has missing or invalid YAML frontmatter", file=sys.stderr)
        return 2
    if fm.get("doc_format_version", fm.get("format_version")) != 2:
        print(f"Error: {path.name} is not a v2 Markdown document", file=sys.stderr)
        return 2
    if (fm.get("project") or {}).get("domain") is None:
        print(
            f"Error: {path.name} is a starter file (project.domain is null); "
            "run session zero before bumping",
            file=sys.stderr,
        )
        return 2

    version = fm.get("version")
    file_name = fm.get("file_name")
    if not version or not file_name:
        print(
            f"Error: {path.name} frontmatter is missing `version` and/or `file_name`",
            file=sys.stderr,
        )
        return 2

    try:
        new_version = next_minor_version(str(version))
        date = datetime.date.today().isoformat()
        new_text, topic, changes = bump_md_text(text, queue_id, new_version, date)
    except BumpError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    out_path = path.with_name(f"{file_name}_v{new_version}-source.md")

    print(f"── {path.name} → {out_path.name} ──")
    print(f"  topic: {topic}")
    for line in changes:
        print(f"  {line}")

    if not args.apply:
        print("  (dry-run — pass --apply to write the new version)")
        return 0

    if out_path.exists() and not args.force:
        print(
            f"  Error: {out_path.name} already exists (pass --force to overwrite)",
            file=sys.stderr,
        )
        return 2

    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(out_path)
    print(f"  → wrote {out_path}")

    if args.no_validate:
        return 0

    issues = validate_md(out_path, prior=path)
    errors = [i for i in issues if i.severity == "error"]
    if issues:
        print(f"  ⚠  {len(errors)} error(s), {len(issues) - len(errors)} warning(s) after bump:")
        for issue in issues:
            print(f"     {issue.format(out_path.name)}")
    return 2 if errors else 0
