"""Starter marker hygiene (roadmap #12).

Every live `<!-- @end: <id> -->` marker must be the *only* occurrence of the
string `@end: <id>` in the bundled starter — no prose mention or template
example may repeat the literal, so an agent grepping for an insertion point
gets exactly one hit instead of "found multiple times".
"""

from __future__ import annotations

import re

from research_buddy.commands._shared import _load_starter_md_text

_END_MARKER = re.compile(r"^\s*<!-- @end:\s*(\S+)\s*-->\s*$")


def test_each_end_marker_id_is_unique_in_starter() -> None:
    text = _load_starter_md_text()
    marker_ids = [m.group(1) for line in text.splitlines() if (m := _END_MARKER.match(line))]
    assert marker_ids, "no @end markers found in starter"
    for anchor_id in marker_ids:
        # Exact marker (trailing ` -->`) so a prefix sub-anchor like
        # `framework.reference.editing` isn't conflated with `framework.reference`.
        occurrences = text.count(f"@end: {anchor_id} -->")
        assert occurrences == 1, (
            f"`@end: {anchor_id}` appears {occurrences} times in starter.md — "
            "a duplicate (prose mention or example) will collide with the live "
            "marker when an agent greps for the insertion point"
        )
