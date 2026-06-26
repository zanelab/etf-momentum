"""Tests for app.factors.momentum — 12-1 momentum factor pure functions."""

from decimal import Decimal

import pytest

from app.factors import (
    compute_momentum_score,
    compute_momentum_scores,
    rank_scores,
)


# ---------------------------------------------------------------------------
# compute_momentum_score
# ---------------------------------------------------------------------------


class TestComputeMomentumScore:
    def test_basic_known_value(self):
        """280 closes where closes[-22]=1.20, closes[-274]=1.00 → 0.20."""
        closes = [Decimal("1.00")] * 280
        closes[-274] = Decimal("1.00")
        closes[-22] = Decimal("1.20")
        # Window: closes[-skip-1] / closes[-skip-1-lookback] - 1
        # = closes[-22] / closes[-22-252] - 1 = closes[-22] / closes[-274] - 1
        result = compute_momentum_score(closes)
        assert result == Decimal("0.20")
        assert isinstance(result, Decimal)

    def test_basic_short_window(self):
        """length=274 (exactly skip+lookback+1) → still works."""
        closes = [Decimal("1.00")] * 274
        closes[-274] = Decimal("1.00")  # index 0
        closes[-22] = Decimal("1.10")   # index 252
        result = compute_momentum_score(closes)
        assert result == Decimal("0.10")

    def test_min_length_boundary(self):
        """length = skip + lookback + 1 = 274 → valid (returns Decimal)."""
        closes = [Decimal("2.00")] * 274
        closes[-22] = Decimal("4.00")
        closes[-274] = Decimal("1.00")
        result = compute_momentum_score(closes)
        assert result == Decimal("3.0")  # 4.00 / 1.00 - 1 = 3.0

    def test_length_one_below_minimum_returns_none(self):
        """length = skip + lookback = 273 → None (insufficient)."""
        closes = [Decimal("1.00")] * 273
        result = compute_momentum_score(closes)
        assert result is None

    def test_empty_list_returns_none(self):
        assert compute_momentum_score([]) is None

    def test_none_input_returns_none(self):
        assert compute_momentum_score(None) is None

    def test_zero_in_closes_returns_none(self):
        closes = [Decimal("1.00")] * 280
        closes[-22] = Decimal("0")
        result = compute_momentum_score(closes)
        assert result is None

    def test_negative_close_returns_none(self):
        closes = [Decimal("1.00")] * 280
        closes[-274] = Decimal("-1.00")
        result = compute_momentum_score(closes)
        assert result is None

    def test_float_input_returns_none(self):
        """Mixed float in list → None (no silent cast)."""
        closes = [1.00] * 280  # plain float, not Decimal
        result = compute_momentum_score(closes)
        assert result is None

    def test_custom_window(self):
        """lookback=60, skip=5: closes[-6] / closes[-66] - 1."""
        closes = [Decimal("1.00")] * 67
        closes[-66] = Decimal("1.00")  # index 0
        closes[-6] = Decimal("1.50")   # index 60
        result = compute_momentum_score(closes, lookback=60, skip=5)
        assert result == Decimal("0.50")

    def test_negative_return(self):
        """Losing trade returns negative Decimal."""
        closes = [Decimal("1.00")] * 280
        closes[-22] = Decimal("0.80")
        closes[-274] = Decimal("1.00")
        result = compute_momentum_score(closes)
        assert result == Decimal("-0.20")

    def test_precision_preserved_no_quantize(self):
        """Output keeps full Decimal precision (no 4-decimal quantize)."""
        closes = [Decimal("1.00")] * 280
        closes[-22] = Decimal("1.123456789")
        closes[-274] = Decimal("1.00")
        result = compute_momentum_score(closes)
        # 1.123456789 / 1.00 - 1 = 0.123456789
        assert result == Decimal("0.123456789")
        # Verify it's NOT quantized to 4 decimals
        assert str(result) == "0.123456789"


# ---------------------------------------------------------------------------
# compute_momentum_scores
# ---------------------------------------------------------------------------


class TestComputeMomentumScores:
    def test_batch_mixed(self):
        closes_long = [Decimal("1.00")] * 280
        closes_long[-22] = Decimal("1.20")
        closes_long[-274] = Decimal("1.00")
        closes_short = [Decimal("1.00")] * 100  # insufficient
        history = {"510300": closes_long, "510500": closes_short}
        result = compute_momentum_scores(history)
        assert result == {"510300": Decimal("0.20"), "510500": None}

    def test_empty_dict(self):
        assert compute_momentum_scores({}) == {}

    def test_all_insufficient(self):
        history = {"a": [Decimal("1.00")] * 100, "b": [Decimal("1.00")] * 50}
        result = compute_momentum_scores(history)
        assert result == {"a": None, "b": None}

    def test_does_not_mutate_input(self):
        closes = [Decimal("1.00")] * 280
        closes[-22] = Decimal("1.20")
        closes[-274] = Decimal("1.00")
        history = {"a": closes}
        snapshot_before = list(closes)
        compute_momentum_scores(history)
        assert closes == snapshot_before


# ---------------------------------------------------------------------------
# rank_scores
# ---------------------------------------------------------------------------


class TestRankScores:
    def test_basic_order_descending(self):
        scores = {
            "a": Decimal("0.20"),
            "b": Decimal("0.10"),
            "c": Decimal("0.05"),
        }
        assert rank_scores(scores) == [
            ("a", 1, Decimal("0.20")),
            ("b", 2, Decimal("0.10")),
            ("c", 3, Decimal("0.05")),
        ]

    def test_tie_competition_ranking_skips_number(self):
        """2 equal scores + 1 lower → ranks [1, 1, 3]."""
        scores = {
            "a": Decimal("0.10"),
            "b": Decimal("0.10"),
            "c": Decimal("0.05"),
        }
        assert rank_scores(scores) == [
            ("a", 1, Decimal("0.10")),
            ("b", 1, Decimal("0.10")),
            ("c", 3, Decimal("0.05")),
        ]

    def test_tie_uses_input_order(self):
        """Tied scores preserve input dict insertion order."""
        scores = {
            "x": Decimal("0.10"),
            "y": Decimal("0.10"),
            "z": Decimal("0.10"),
        }
        result = rank_scores(scores)
        # All tied → all rank 1, order follows dict insertion
        assert result == [
            ("x", 1, Decimal("0.10")),
            ("y", 1, Decimal("0.10")),
            ("z", 1, Decimal("0.10")),
        ]

    def test_with_nones_at_end(self):
        scores = {
            "a": Decimal("0.10"),
            "b": None,
            "c": Decimal("0.05"),
            "d": None,
        }
        assert rank_scores(scores) == [
            ("a", 1, Decimal("0.10")),
            ("c", 2, Decimal("0.05")),
            ("b", None, None),
            ("d", None, None),
        ]

    def test_all_none(self):
        scores = {"a": None, "b": None, "c": None}
        assert rank_scores(scores) == [
            ("a", None, None),
            ("b", None, None),
            ("c", None, None),
        ]

    def test_empty_dict(self):
        assert rank_scores({}) == []

    def test_negative_scores_still_ranked(self):
        """Negative scores get a real rank (not pushed to None section)."""
        scores = {
            "a": Decimal("0.20"),
            "b": Decimal("-0.05"),
            "c": Decimal("0.10"),
        }
        assert rank_scores(scores) == [
            ("a", 1, Decimal("0.20")),
            ("c", 2, Decimal("0.10")),
            ("b", 3, Decimal("-0.05")),
        ]

    def test_mixed_ties_and_nones(self):
        """1 + 1 tie + 1 lower + 2 None → ranked then None section."""
        scores = {
            "a": Decimal("0.10"),
            "b": Decimal("0.10"),
            "c": Decimal("0.05"),
            "d": None,
            "e": None,
        }
        assert rank_scores(scores) == [
            ("a", 1, Decimal("0.10")),
            ("b", 1, Decimal("0.10")),
            ("c", 3, Decimal("0.05")),
            ("d", None, None),
            ("e", None, None),
        ]

    def test_single_score(self):
        assert rank_scores({"a": Decimal("0.5")}) == [("a", 1, Decimal("0.5"))]

    def test_return_type_is_list_of_tuples(self):
        scores = {"a": Decimal("0.10")}
        result = rank_scores(scores)
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 3 for item in result)


# ---------------------------------------------------------------------------
# Module-level re-exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_init_exposes_three_functions(self):
        from app.factors import compute_momentum_score, compute_momentum_scores, rank_scores

        assert callable(compute_momentum_score)
        assert callable(compute_momentum_scores)
        assert callable(rank_scores)