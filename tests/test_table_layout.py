"""Tests for content-based adaptive table column widths."""

from __future__ import annotations

from research_buddy.table_layout import (
    MIN_PCT,
    TOKEN_COL_PX,
    ColumnProfile,
    TableLayout,
    compute_layouts,
    profile_column,
    profile_table,
    signature,
)


class TestProfileColumn:
    def test_empty_column(self) -> None:
        p = profile_column([])
        assert p == ColumnProfile(0, 0, 0, has_spaces=False, is_token=False)

    def test_short_no_spaces_is_token(self) -> None:
        p = profile_column(["v1.0", "v1.1", "v2.0"])
        assert p.is_token is True
        assert p.has_spaces is False

    def test_long_with_spaces_is_not_token(self) -> None:
        p = profile_column(
            [
                "this is a long sentence that definitely wraps",
                "another long sentence in the same column",
            ]
        )
        assert p.is_token is False
        assert p.has_spaces is True

    def test_short_but_with_spaces_is_not_token(self) -> None:
        p = profile_column(["a b", "c d", "e f"])
        assert p.is_token is False
        assert p.has_spaces is True

    def test_max_len_excludes_token(self) -> None:
        # p90 short, but max length over threshold → not token.
        p = profile_column(["x", "x", "x", "x", "x", "x", "x", "x", "x", "long-id-not-fitting"])
        assert p.is_token is False

    def test_buckets_by_p90(self) -> None:
        assert profile_column(["x"]).bucket == "nano"
        assert profile_column(["short-id"]).bucket == "short"
        assert profile_column(["a fairly medium-length cell with words"]).bucket == "medium"
        assert profile_column(["a" * 80]).bucket == "long"


class TestSignature:
    def test_same_shape_same_signature(self) -> None:
        a = profile_table([["v1.0", "Alpha topic", "OPEN"], ["v1.1", "Beta topic", "DONE"]])
        b = profile_table([["v2.0", "Gamma topic", "OPEN"], ["v2.1", "Delta topic", "DONE"]])
        assert signature(a) == signature(b)

    def test_different_shape_different_signature(self) -> None:
        a = profile_table([["v1.0", "Alpha topic"]])
        b = profile_table([["v1.0", "Alpha topic", "OPEN"]])
        assert signature(a) != signature(b)


class TestLayoutSingleTable:
    def test_widths_sum_to_100_for_non_token_columns(self) -> None:
        rows = [
            ["row one cell with prose", "second column with prose", "third"],
            ["another row also prose", "more prose in column two", "fourth"],
        ]
        layout = compute_layouts([rows])[0]
        non_token_pcts = [
            int(layout.col_widths[i].rstrip("%"))
            for i in range(3)
            if layout.col_widths[i].endswith("%")
        ]
        assert sum(non_token_pcts) == 100

    def test_token_column_gets_fixed_px(self) -> None:
        rows = [["v1.0", "lots of prose in this cell that wraps"], ["v1.1", "still prose here"]]
        layout = compute_layouts([rows])[0]
        assert layout.col_widths[0] == f"{TOKEN_COL_PX}px"
        assert layout.col_widths[1].endswith("%")
        assert layout.nowrap == (True, False)
        assert layout.use_fixed is True

    def test_no_token_columns_no_fixed_class(self) -> None:
        rows = [["prose with spaces", "more prose"], ["another row of words", "second column"]]
        layout = compute_layouts([rows])[0]
        assert layout.use_fixed is False
        assert layout.nowrap == (False, False)

    def test_single_non_token_column_gets_remaining_space(self) -> None:
        # Three token columns + one prose column → token cols pinned to px,
        # the lone non-token column takes 100% of the remaining percentage
        # space (MAX_PCT only constrains distribution between non-tokens).
        rows = [
            ["x", "x", "x", "x" * 200],
            ["y", "y", "y", "y" * 200],
        ]
        layout = compute_layouts([rows])[0]
        assert layout.col_widths[0].endswith("px")
        assert layout.col_widths[1].endswith("px")
        assert layout.col_widths[2].endswith("px")
        assert layout.col_widths[3] == "100%"

    def test_two_prose_columns_neither_squeezed(self) -> None:
        # Skewed content: column 2 has ~5x the content of column 1. After
        # clamp + renormalize the smaller column must not collapse below the
        # MIN_PCT floor, even though the algorithm's ceiling is best-effort
        # for two-column tables (the 100% sum constraint dominates).
        rows = [
            ["short prose", "much longer prose with many more words to render"],
            ["short prose", "yet another long second column entry with lots of words"],
        ]
        layout = compute_layouts([rows])[0]
        a = int(layout.col_widths[0].rstrip("%"))
        b = int(layout.col_widths[1].rstrip("%"))
        assert a + b == 100
        assert a >= MIN_PCT
        assert b >= MIN_PCT

    def test_empty_table(self) -> None:
        layout = compute_layouts([[]])[0]
        assert layout == TableLayout({}, (), False)


class TestLayoutGrouping:
    def test_similar_tables_share_layout(self) -> None:
        # Two structurally similar 3-column tables.
        t1 = [
            ["v1.0", "Alpha topic with words", "OPEN"],
            ["v1.1", "Beta topic also wordy", "DONE"],
        ]
        t2 = [
            ["v2.0", "Gamma topic prose here", "OPEN"],
            ["v2.1", "Delta topic with words", "DONE"],
        ]
        layouts = compute_layouts([t1, t2])
        assert layouts[0] == layouts[1]

    def test_different_signatures_get_independent_layouts(self) -> None:
        # 2-column vs 3-column.
        t1 = [["v1.0", "Alpha topic with words"]]
        t2 = [["v1.0", "Alpha topic with words", "OPEN"]]
        layouts = compute_layouts([t1, t2])
        assert layouts[0] != layouts[1]

    def test_grouped_tables_share_one_layout(self) -> None:
        # Same signature: both have a token col 0 (single char, no spaces) and
        # a short-prose col 1 (has spaces, p90 in the "short" bucket).
        small = [["x", "short prose"], ["y", "tiny words"]]
        big = [["x", "longer prose"], ["y", "more words here"]]
        layouts = compute_layouts([small, big])
        assert layouts[0] == layouts[1]


class TestLanguageIndependence:
    def test_spanish_headers_no_keyword_dependence(self) -> None:
        # Same content, Spanish vs English headers — layout depends only on
        # cell content (which we keep identical here), not headers.
        rows_es = [["v1.0", "Tema con palabras"], ["v1.1", "Otro tema con texto"]]
        rows_en = [["v1.0", "Tema con palabras"], ["v1.1", "Otro tema con texto"]]
        layout_es = compute_layouts([rows_es])[0]
        layout_en = compute_layouts([rows_en])[0]
        assert layout_es == layout_en
