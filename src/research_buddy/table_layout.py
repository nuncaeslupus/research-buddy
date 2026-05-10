"""Content-based adaptive column widths for HTML tables.

Replaces the English-keyword-based heuristic that lived in `build.py` (matching
phrases like "build", "test condition", "rejected" in headers) with a
deterministic, language-independent algorithm:

1. **Column profile** — p50/p90/max length per column, plus has-spaces and
   is-token flags derived from cell content alone (never headers).
2. **Signature** — bucketed p90 + token flag per column. Tables sharing the
   same signature within one document get a unified width vector so visually
   similar tables align across the document.
3. **Width vector** — token columns get a fixed pixel width (and the `nw`
   nowrap class); the remainder distribute 100% proportionally to p90 with
   a 12-50% floor/ceiling.

Inputs are plain `list[list[str]]`; the module does not depend on
markdown-it / Jinja / build internals so both the v1 (JSON) and v2
(Markdown) pipelines can share it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# A column whose p90 is short and whose cells contain no spaces gets a fixed
# px width and the nowrap class — same UX as v1's `t-fixed` + `nw`.
TOKEN_COL_PX = 110
TOKEN_P90_THRESHOLD = 16

# Bucket boundaries used to compute table signatures for grouping.
BUCKET_NANO = 6
BUCKET_SHORT = 16
BUCKET_MEDIUM = 40

# Floor / ceiling for non-token column widths (percentages summing to 100).
MIN_PCT = 12
MAX_PCT = 50


@dataclass(frozen=True)
class ColumnProfile:
    p50: int
    p90: int
    max_len: int
    has_spaces: bool
    is_token: bool

    @property
    def bucket(self) -> str:
        if self.p90 <= BUCKET_NANO:
            return "nano"
        if self.p90 <= BUCKET_SHORT:
            return "short"
        if self.p90 <= BUCKET_MEDIUM:
            return "medium"
        return "long"


@dataclass(frozen=True)
class TableLayout:
    """Per-table layout: column widths, per-column nowrap flags, t-fixed flag."""

    col_widths: dict[int, str]
    nowrap: tuple[bool, ...]
    use_fixed: bool


Signature = tuple[tuple[str, bool], ...]


def profile_column(cells: Sequence[str]) -> ColumnProfile:
    if not cells:
        return ColumnProfile(0, 0, 0, has_spaces=False, is_token=False)
    lengths = sorted(len(c) for c in cells)
    n = len(lengths)
    p50 = lengths[n // 2]
    p90 = lengths[max(0, math.ceil(0.9 * n) - 1)]
    max_len = lengths[-1]
    n_with_spaces = sum(1 for c in cells if " " in c.strip())
    has_spaces = n_with_spaces * 2 >= n
    is_token = (not has_spaces) and p90 <= TOKEN_P90_THRESHOLD and max_len <= TOKEN_P90_THRESHOLD
    return ColumnProfile(p50, p90, max_len, has_spaces=has_spaces, is_token=is_token)


def profile_table(rows: Sequence[Sequence[str]]) -> list[ColumnProfile]:
    if not rows:
        return []
    ncols = max(len(r) for r in rows)
    profiles: list[ColumnProfile] = []
    for j in range(ncols):
        cells = [r[j] if j < len(r) else "" for r in rows]
        profiles.append(profile_column(cells))
    return profiles


def signature(profiles: Sequence[ColumnProfile]) -> Signature:
    return tuple((p.bucket, p.is_token) for p in profiles)


def _aggregate(group: Sequence[Sequence[ColumnProfile]]) -> list[ColumnProfile]:
    """Combine profile vectors from a signature group: per column take max p90,
    keep is_token (the signature already enforces agreement on it)."""
    ncols = len(group[0])
    agg: list[ColumnProfile] = []
    for j in range(ncols):
        members = [g[j] for g in group]
        agg.append(
            ColumnProfile(
                p50=max(m.p50 for m in members),
                p90=max(m.p90 for m in members),
                max_len=max(m.max_len for m in members),
                has_spaces=any(m.has_spaces for m in members),
                is_token=all(m.is_token for m in members),
            )
        )
    return agg


def _layout_from_profiles(profiles: Sequence[ColumnProfile]) -> TableLayout:
    n = len(profiles)
    if n == 0:
        return TableLayout(col_widths={}, nowrap=(), use_fixed=False)

    nowrap = tuple(p.is_token for p in profiles)
    use_fixed = any(nowrap)

    col_widths: dict[int, str] = {}
    for i, p in enumerate(profiles):
        if p.is_token:
            col_widths[i] = f"{TOKEN_COL_PX}px"

    nontoken_idx = [i for i in range(n) if not profiles[i].is_token]
    if not nontoken_idx:
        return TableLayout(col_widths=col_widths, nowrap=nowrap, use_fixed=use_fixed)

    weights = [max(1, profiles[i].p90) for i in nontoken_idx]
    total = sum(weights)
    raw = [w * 100.0 / total for w in weights]

    # Floor / ceiling with renormalization. One pass is enough for our size
    # range — clamp pushes mass around but doesn't iterate; the renormalize
    # afterwards rescales whatever's left.
    clamped = [max(MIN_PCT, min(MAX_PCT, x)) for x in raw]
    s = sum(clamped) or 1.0
    scaled = [x * 100.0 / s for x in clamped]

    rounded = [round(x) for x in scaled]
    diff = 100 - sum(rounded)
    if diff != 0:
        # Distribute leftover by largest fractional remainder.
        order = sorted(
            range(len(scaled)),
            key=lambda k: scaled[k] - rounded[k],
            reverse=diff > 0,
        )
        step = 1 if diff > 0 else -1
        for k in range(abs(diff)):
            rounded[order[k % len(order)]] += step

    for j, idx in enumerate(nontoken_idx):
        col_widths[idx] = f"{rounded[j]}%"

    return TableLayout(col_widths=col_widths, nowrap=nowrap, use_fixed=use_fixed)


def compute_layouts(tables: Sequence[Sequence[Sequence[str]]]) -> list[TableLayout]:
    """Compute per-table layouts. Tables sharing a signature share one width
    vector (computed from per-column max-of-p90 across the group).

    `tables` is a list of tables in render order; each table is a list of
    rows; each row is a list of cell strings. Empty tables yield an empty
    layout. Output order matches input order.
    """
    profiles = [profile_table(t) for t in tables]
    sig_to_indices: dict[Signature, list[int]] = {}
    for i, prof in enumerate(profiles):
        sig_to_indices.setdefault(signature(prof), []).append(i)

    layouts: list[TableLayout | None] = [None] * len(tables)
    for indices in sig_to_indices.values():
        if len(indices) == 1:
            layouts[indices[0]] = _layout_from_profiles(profiles[indices[0]])
            continue
        agg = _aggregate([profiles[i] for i in indices])
        shared = _layout_from_profiles(agg)
        for i in indices:
            layouts[i] = shared

    return [layout if layout is not None else TableLayout({}, (), False) for layout in layouts]
