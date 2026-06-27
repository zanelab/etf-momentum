"""Tests for app.backtest.engine._validate_params.

Direct unit tests for every ValueError branch. The end-to-end tests in
test_backtest_engine.py only exercise the happy path; this file locks
the input-contract semantics so that future refactors of the validator
cannot silently drop a check.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.backtest.engine import (
    BacktestParams,
    RebalanceFrequency,
    _validate_params,
)


def _minimal_history(start: date, n_days: int = 300) -> list[tuple[date, Decimal]]:
    """Return `n_days` consecutive (date, price) entries starting at `start`."""
    from datetime import timedelta

    return [
        (start + timedelta(days=i), Decimal("1.00") + Decimal(i) * Decimal("0.001"))
        for i in range(n_days)
    ]


def _valid_params(**overrides) -> BacktestParams:
    """Return a minimally valid BacktestParams; override any field."""
    base = dict(
        etf_pool=["510300"],
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
        initial_cash=Decimal("100000"),
    )
    base.update(overrides)
    return BacktestParams(**base)


class TestValidateParams:
    # ---- end < start ----------------------------------------------------

    def test_end_before_start_raises(self):
        p = _valid_params(start=date(2024, 6, 30), end=date(2024, 1, 1))
        with pytest.raises(ValueError, match="end"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_end_equals_start_is_valid(self):
        """A 1-day window is allowed."""
        p = _valid_params(start=date(2024, 1, 1), end=date(2024, 1, 1))
        # Should not raise
        _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    # ---- initial_cash ---------------------------------------------------

    def test_initial_cash_zero_raises(self):
        p = _valid_params(initial_cash=Decimal("0"))
        with pytest.raises(ValueError, match="initial_cash"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_initial_cash_negative_raises(self):
        p = _valid_params(initial_cash=Decimal("-1"))
        with pytest.raises(ValueError, match="initial_cash"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    # ---- top_n ----------------------------------------------------------

    def test_top_n_zero_raises(self):
        p = _valid_params(top_n=0)
        with pytest.raises(ValueError, match="top_n"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_top_n_negative_raises(self):
        p = _valid_params(top_n=-1)
        with pytest.raises(ValueError, match="top_n"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    # ---- lookback -------------------------------------------------------

    def test_lookback_zero_raises(self):
        p = _valid_params(lookback=0)
        with pytest.raises(ValueError, match="lookback"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_lookback_negative_raises(self):
        p = _valid_params(lookback=-1)
        with pytest.raises(ValueError, match="lookback"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    # ---- skip -----------------------------------------------------------

    def test_skip_negative_raises(self):
        p = _valid_params(skip=-1)
        with pytest.raises(ValueError, match="skip"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_skip_zero_is_valid(self):
        p = _valid_params(skip=0)
        _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    # ---- etf_pool -------------------------------------------------------

    def test_empty_pool_raises(self):
        p = _valid_params(etf_pool=[])
        with pytest.raises(ValueError, match="empty"):
            _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_missing_pool_codes_raises(self):
        """Pool references codes that aren't in price_history."""
        p = _valid_params(etf_pool=["510300", "510999"])
        with pytest.raises(ValueError, match="missing"):
            _validate_params(
                p,
                {
                    "510300": _minimal_history(date(2023, 1, 1)),
                    # "510999" intentionally absent
                },
            )

    def test_missing_pool_codes_message_lists_them(self):
        p = _valid_params(etf_pool=["510300", "510999", "510888"])
        with pytest.raises(ValueError) as exc_info:
            _validate_params(
                p,
                {"510300": _minimal_history(date(2023, 1, 1))},
            )
        msg = str(exc_info.value)
        # Both missing codes should appear in the message
        assert "510999" in msg
        assert "510888" in msg

    # ---- happy path (no raise) -----------------------------------------

    def test_all_valid_passes(self):
        p = _valid_params()
        # Should not raise
        _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})

    def test_default_params_are_valid(self):
        """A fresh BacktestParams with only the 4 required fields must validate."""
        p = BacktestParams(
            etf_pool=["510300"],
            start=date(2024, 1, 1),
            end=date(2024, 6, 30),
            initial_cash=Decimal("100000"),
        )
        assert p.rebalance_freq == RebalanceFrequency.MONTHLY
        _validate_params(p, {"510300": _minimal_history(date(2023, 1, 1))})
