"""Targeted tests that kill mutmut survivors in `research_buddy.table_layout`.

Step #7b of the mutation-survivor cleanup roadmap. Each class targets
a specific function and pins behavior the existing test suite left
open for mutmut to flip undetected.

Buckets:
    - `profile_column`: exact p50 / p90 indexing, has_spaces threshold
      arithmetic, is_token boundary conditions on p90 and max_len.
    - `profile_table`: ragged-row padding semantics.
    - `_aggregate`: per-field max / any / all aggregation across a group.
    - `_layout_from_profiles`: single-profile and all-token early returns,
      weight floor, raw/scaled scaling, redistribution loop (positive and
      negative diff branches).
    - `compute_layouts`: signature-group iteration progression.

The 10 accepted equivalents not covered here are documented in
`status/next-session.md` for step #7b.
"""

from __future__ import annotations

from research_buddy.table_layout import (
    ColumnProfile,
    _aggregate,
    _layout_from_profiles,
    compute_layouts,
    profile_column,
    profile_table,
)


def _non_token(p90: int) -> ColumnProfile:
    """Synthetic non-token column profile (has_spaces=True forces non-token
    regardless of p90), used to feed `_layout_from_profiles` directly."""
    return ColumnProfile(p50=p90, p90=p90, max_len=p90, has_spaces=True, is_token=False)


def _token(p90: int = 4) -> ColumnProfile:
    """Synthetic token column profile."""
    return ColumnProfile(p50=p90, p90=p90, max_len=p90, has_spaces=False, is_token=True)


class TestProfileColumnPercentiles:
    """Exact-value assertions on p50 / p90 indexing."""

    def test_p50_uses_floor_division_by_two(self) -> None:
        # n=4, lengths sorted = [1, 2, 3, 4]; n//2 = 2 → p50 = lengths[2] = 3.
        # Kills profile_column#22 (n//2 → n//3 ⇒ p50 = lengths[1] = 2).
        assert profile_column(["a", "ab", "abc", "abcd"]).p50 == 3

    def test_p90_uses_ceil_of_zero_point_nine_n_minus_one(self) -> None:
        # n=10, lengths sorted = [1..10]. ceil(0.9 * 10) - 1 = 8 → p90 = 9.
        # Kills:
        #   - profile_column#31 (0.9 * n → 0.9 / n ⇒ ceil(0.09) - 1 = 0,
        #     p90 = lengths[0] = 1).
        #   - profile_column#33 (-1 → -2 ⇒ p90 = lengths[7] = 8).
        cells = [
            "a", "ab", "abc", "abcd", "abcde",
            "abcdef", "abcdefg", "abcdefgh", "abcdefghi", "abcdefghij",
        ]  # fmt: skip
        assert profile_column(cells).p90 == 9


class TestProfileColumnSpacesCount:
    """Pin n_with_spaces accumulator + has_spaces threshold inclusivity."""

    def test_n_with_spaces_counts_one_per_match_not_two(self) -> None:
        # 1 of 4 cells has a space. Original n_with_spaces = 1, so
        # has_spaces = 1*2 >= 4 → False.
        # Kills profile_column#39 (`sum(1 …)` → `sum(2 …)` ⇒ n_with_spaces
        # doubles to 2, has_spaces = 2*2 >= 4 → True).
        assert profile_column(["a b", "x", "y", "z"]).has_spaces is False

    def test_has_spaces_threshold_uses_times_two_not_times_three(self) -> None:
        # 1 of 3 cells has a space. Original: 1*2 >= 3 → False.
        # Kills profile_column#44 (`*2` → `*3` ⇒ 1*3 >= 3 → True).
        assert profile_column(["a b", "x", "y"]).has_spaces is False

    def test_has_spaces_threshold_is_inclusive_at_exact_half(self) -> None:
        # 2 of 4 cells have spaces. Original: 2*2 >= 4 → True (inclusive).
        # Kills profile_column#45 (`>= n` → `> n` ⇒ 4 > 4 → False).
        assert profile_column(["a b", "c d", "x", "y"]).has_spaces is True


class TestProfileColumnTokenBoundary:
    """`is_token` checks p90 <= 16 AND max_len <= 16 — both inclusive."""

    def test_is_token_true_when_p90_and_max_len_equal_threshold(self) -> None:
        # 10 cells all length 16, no spaces. p90 = max_len = 16. Original:
        # 16 <= 16 → True. Kills profile_column#50 (p90 < 16) — the test
        # also kills #51 (max_len < 16), but the dedicated max_len test
        # below pins the boundary in isolation.
        assert profile_column(["a" * 16] * 10).is_token is True

    def test_is_token_true_when_only_max_len_equals_threshold(self) -> None:
        # 9 single-char cells + 1 length-16 cell → p90 = 1, max_len = 16.
        # Original is_token = True (max_len 16 <= 16). Kills
        # profile_column#51 (max_len < 16 → 16 < 16 False ⇒ is_token False).
        assert profile_column(["a"] * 9 + ["b" * 16]).is_token is True


class TestProfileTableRagged:
    """Ragged rows: missing cells are padded with empty strings, not 'XXXX',
    and the comparator is strict `<` so a 0-width row stays out-of-range."""

    def test_short_row_padded_with_empty_string(self) -> None:
        # ncols = max(1, 0) = 1. For j=0:
        #   - Row 0 (len=1): r[0] = "a".
        #   - Row 1 (len=0): "" (because 0 < 0 is False).
        # profile_column(["a", ""]) → lengths=[0,1] → p90 = lengths[1] = 1.
        # Kills:
        #   - profile_table#7 (j < len(r) → j <= len(r)): on row 1,
        #     0 <= 0 True ⇒ r[0] on [] raises IndexError.
        #   - profile_table#8 (else "" → else "XXXX"): cells become
        #     ["a", "XXXX"] ⇒ lengths=[1,4] ⇒ p90 = 4.
        profiles = profile_table([["a"], []])
        assert len(profiles) == 1
        assert profiles[0].p90 == 1


class TestAggregateGroup:
    """`_aggregate` reduces a group of profile vectors to one — per-field max
    on p50 / p90 / max_len, any() on has_spaces, all() on is_token. Each
    field is asserted on its own to kill the corresponding `None`-mutant."""

    @staticmethod
    def _p(**overrides: object) -> ColumnProfile:
        base: dict[str, object] = dict(p50=5, p90=10, max_len=10, has_spaces=False, is_token=False)
        base.update(overrides)
        return ColumnProfile(**base)  # type: ignore[arg-type]

    def test_p50_aggregated_as_max(self) -> None:
        # Kills _aggregate#6 (p50=None).
        agg = _aggregate([[self._p(p50=5)], [self._p(p50=10)]])
        assert agg[0].p50 == 10

    def test_max_len_aggregated_as_max(self) -> None:
        # Kills _aggregate#8 (max_len=None).
        agg = _aggregate([[self._p(max_len=3)], [self._p(max_len=7)]])
        assert agg[0].max_len == 7

    def test_has_spaces_aggregated_as_any(self) -> None:
        # Kills _aggregate#9 (has_spaces=None).
        agg = _aggregate([[self._p(has_spaces=False)], [self._p(has_spaces=True)]])
        assert agg[0].has_spaces is True

    def test_is_token_aggregated_as_all(self) -> None:
        # Kills _aggregate#10 (is_token=None). One True + one False → False.
        agg = _aggregate([[self._p(is_token=True)], [self._p(is_token=False)]])
        assert agg[0].is_token is False


class TestLayoutFromProfilesEarlyReturns:
    """Single-profile and all-token early-return branches."""

    def test_single_non_token_profile_falls_through_to_full_width(self) -> None:
        # n=1, non-token. Original: skip `if n == 0:` and fall through →
        # the lone column gets 100% width.
        # Kills _layout_from_profiles#3 (n == 0 → n == 1 ⇒ early return
        # with col_widths={}).
        layout = _layout_from_profiles([_non_token(10)])
        assert layout.col_widths == {0: "100%"}

    def test_all_token_columns_return_pixel_widths_and_use_fixed_true(self) -> None:
        # nontoken_idx is empty → the line-138 early return fires.
        # Kills:
        #   - _layout_from_profiles#22 (col_widths=None at this return).
        #   - _layout_from_profiles#24 (use_fixed=None at this return).
        layout = _layout_from_profiles([_token(), _token()])
        assert layout.col_widths == {0: "110px", 1: "110px"}
        assert layout.use_fixed is True
        assert layout.nowrap == (True, True)


class TestLayoutFromProfilesWeights:
    """Weight floor (`max(1, p90)`) and raw/scaled arithmetic."""

    def test_weights_floor_at_one_not_two(self) -> None:
        # Two non-token cols, p90=1 and p90=5. Original weights=[1, 5];
        # final widths = {0:'25%', 1:'75%'}. Mutant #33 weights=[2, 5]
        # ⇒ {0:'36%', 1:'64%'}.
        layout = _layout_from_profiles([_non_token(1), _non_token(5)])
        assert layout.col_widths == {0: "25%", 1: "75%"}

    def test_raw_two_column_clamp_path_pins_scaling_constants(self) -> None:
        # Two non-token cols, p90=2 and p90=3:
        #   raw=[40, 60] → clamp=[40, 50] (right col hits MAX_PCT=50)
        #   → sum 90 → scaled=[44.44, 55.56] → rounded={0:'44%', 1:'56%'}.
        # Kills:
        #   - _layout_from_profiles#37 (raw = w * 100 * total: all clamp
        #     to 50 ⇒ {0:'50%', 1:'50%'}).
        #   - _layout_from_profiles#38 (raw = w / 100 / total: all tiny,
        #     clamp to MIN_PCT=12 ⇒ {0:'50%', 1:'50%'} after renormalize).
        #   - _layout_from_profiles#39 (100 → 101 in raw shifts clamp
        #     boundary ⇒ {0:'45%', 1:'55%'}).
        #   - _layout_from_profiles#55 (scaled = x / 100 / s: tiny ⇒
        #     diff=100, redistributes to {0:'50%', 1:'50%'}).
        layout = _layout_from_profiles([_non_token(2), _non_token(3)])
        assert layout.col_widths == {0: "44%", 1: "56%"}


class TestLayoutFromProfilesRedistribution:
    """`if diff != 0:` redistributes the rounding remainder. Two cases
    (positive diff and negative diff) together cover every mutation on
    the sorted-by-fractional-remainder block."""

    def test_positive_diff_adds_one_to_largest_remainder(self) -> None:
        # Three non-token cols, p90=[3, 6, 10]:
        #   raw≈[15.79, 31.58, 52.63] → clamp [15.79, 31.58, 50]
        #   → s≈97.37 → scaled≈[16.21, 32.43, 51.35]
        #   → rounded=[16, 32, 51] sum=99 ⇒ diff=1.
        #   Fractional remainders [0.21, 0.43, 0.35]: sorted desc
        #   (reverse=True) → [1, 2, 0]; step=1; rounded[1]+=1 → [16,33,51].
        # Kills (positive-diff branches of):
        #   #56 (scaled * 101 ⇒ {16,32,52}), #63 (skip redistribute ⇒
        #   {16,32,51}), #64 (skip when diff==1), #67 (key=None), #70 (no
        #   key), #71 (no reverse=), #74 (key uses +), #76 (reverse=diff>1
        #   ⇒ ascending), #78 (step=2), #80 (step=-1 when diff==1), #85
        #   (= step instead of +=), #86 (-= step).
        layout = _layout_from_profiles([_non_token(3), _non_token(6), _non_token(10)])
        assert layout.col_widths == {0: "16%", 1: "33%", 2: "51%"}

    def test_negative_diff_subtracts_one_from_smallest_remainder(self) -> None:
        # Three non-token cols, p90=[3, 5, 12]:
        #   raw=[15, 25, 60] → clamp [15, 25, 50] → s=90
        #   → scaled≈[16.67, 27.78, 55.56]
        #   → rounded=[17, 28, 56] sum=101 ⇒ diff=-1.
        #   Fractional remainders [-0.33, -0.22, -0.44]: sorted asc
        #   (reverse=False) → [2, 0, 1]; step=-1; rounded[2]-=1 → [17,28,55].
        # Kills (negative-diff branches of):
        #   #81 (step=+1 when diff<0 ⇒ rounded[2]+=1 ⇒ {17,28,57}),
        #   #82 (step=-2 ⇒ {17,28,54}). The other redistribute mutants
        #   are already killed by the positive-diff test above; the
        #   negative case is the only branch that exercises the `else -1`
        #   half of the conditional.
        layout = _layout_from_profiles([_non_token(3), _non_token(5), _non_token(12)])
        assert layout.col_widths == {0: "17%", 1: "28%", 2: "55%"}


class TestComputeLayoutsGrouping:
    """`compute_layouts` iterates over signature groups; the singleton
    branch uses `continue`, the group branch calls `_aggregate` +
    `_layout_from_profiles` and assigns the shared layout to every index."""

    def test_distinct_singletons_all_get_real_layouts(self) -> None:
        # Two tables, distinct signatures, both singletons.
        # Kills compute_layouts#19 (continue → break ⇒ after processing
        # the first singleton the loop exits, leaving layouts[1] None ⇒
        # the `is not None` fallback fires with col_widths={}).
        long_prose = [["word " * 30]]  # 1 non-token col
        all_tokens = [["a", "b"]]  # 2 token cols
        layouts = compute_layouts([long_prose, all_tokens])
        assert layouts[0].col_widths == {0: "100%"}
        assert layouts[1].col_widths == {0: "110px", 1: "110px"}

    def test_grouped_tables_share_a_real_layout_not_the_none_fallback(self) -> None:
        # Two tables with identical signatures: col 0 token, col 1 prose.
        # Original: _aggregate runs, shared = _layout_from_profiles(agg),
        # layouts[0] = layouts[1] = shared with col_widths populated.
        # Kills:
        #   - compute_layouts#22 (shared = None ⇒ both layouts fall to
        #     the `is not None` fallback ⇒ col_widths={}).
        #   - compute_layouts#24 (layouts[i] = None ⇒ same effect).
        # The existing `test_grouped_tables_share_one_layout` only asserts
        # `layouts[0] == layouts[1]`, which is true under either branch;
        # we assert specific col_widths to pin the real-layout output.
        small = [["x", "short prose"], ["y", "tiny words"]]
        big = [["x", "longer prose"], ["y", "more words here"]]
        layouts = compute_layouts([small, big])
        assert layouts[0].col_widths == {0: "110px", 1: "100%"}
        assert layouts[0] == layouts[1]
        assert layouts[0].use_fixed is True
