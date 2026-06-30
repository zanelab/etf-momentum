"""Tests for the signals service (sell + buy generation) and related API endpoints."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.models.portfolio import Portfolio
from app.services.screening import DEFAULT_DEFENSIVE_ETF
from app.services.signals import generate_signals
from app.services.types import StrategyParams


def _mock_market(snapshots: dict[str, float]) -> MagicMock:
    """Build a mock market that returns a fixed last_price for each code."""
    market = MagicMock()
    market.snapshot = lambda code, as_of: {"last_price": snapshots[code], "volume": 0, "money": 0}
    return market


def _params(**overrides):
    defaults = dict(
        stock_sum=3,
        momentum_days=25,
        volume_lookback=5,
        volume_threshold=2.5,
        ma_short=20,
        ma_long=60,
        enable_volume_check=True,
        enable_ma_filter=True,
        defensive_etf=DEFAULT_DEFENSIVE_ETF,
        enable_industry_diverse=False,
    )
    defaults.update(overrides)
    return StrategyParams(**defaults)


# ────────────── Signal generation ──────────────


def test_generate_signals_no_holdings_emits_only_buys() -> None:
    market = _mock_market({"510300.XSHG": 3.87, "518880.XSHG": 4.12})
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG", "518880.XSHG"]
    signals = generate_signals(
        targets=targets,
        holdings=[],
        total_value=200_000.0,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    assert all(s.type == "BUY" for s in signals)
    assert {s.etf for s in signals} == set(targets)


def test_generate_signals_sells_holdings_not_in_targets() -> None:
    market = _mock_market({"510300.XSHG": 3.87, "159915.XSHE": 2.05})
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG"]
    holdings = [
        Portfolio(code="510300.XSHG", name="沪深300", shares=10_000, cost_price=3.95),
        Portfolio(code="159915.XSHE", name="创业板", shares=8_000, cost_price=2.10),
    ]
    signals = generate_signals(
        targets=targets,
        holdings=holdings,
        total_value=200_000.0,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    by_etf = {s.etf: s for s in signals}
    assert "159915.XSHE" in by_etf
    assert by_etf["159915.XSHE"].type == "SELL"
    assert by_etf["159915.XSHE"].shares == 8_000


def test_generate_signals_buys_targets_not_held() -> None:
    market = _mock_market({"510300.XSHG": 3.87, "518880.XSHG": 4.12})
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG", "518880.XSHG"]
    holdings = [
        Portfolio(code="510300.XSHG", name="沪深300", shares=10_000, cost_price=3.95)
    ]
    signals = generate_signals(
        targets=targets,
        holdings=holdings,
        total_value=200_000.0,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    buy_targets = {s.etf for s in signals if s.type == "BUY"}
    assert "518880.XSHG" in buy_targets
    assert "510300.XSHG" not in buy_targets


def test_generate_signals_equal_weight_allocation() -> None:
    market = _mock_market({"510300.XSHG": 3.87, "518880.XSHG": 4.12})
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG", "518880.XSHG"]
    total = 200_000.0
    signals = generate_signals(
        targets=targets,
        holdings=[],
        total_value=total,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    target_value = total / len(targets)
    for s in signals:
        assert s.type == "BUY"
        assert s.target_value == pytest.approx(target_value)
        # shares must be a positive multiple of 100 (ETF lot size)
        assert s.shares is not None
        assert s.shares > 0
        assert s.shares % 100 == 0


def test_generate_signals_held_target_is_noop() -> None:
    """If a target is already held, no signal is emitted for it."""
    market = _mock_market({"510300.XSHG": 3.87})
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG"]
    holdings = [
        Portfolio(code="510300.XSHG", name="沪深300", shares=10_000, cost_price=3.95)
    ]
    signals = generate_signals(
        targets=targets,
        holdings=holdings,
        total_value=200_000.0,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    assert signals == []


def test_generate_signals_empty_targets_uses_defensive() -> None:
    market = _mock_market({DEFAULT_DEFENSIVE_ETF: 100.0})
    as_of = datetime(2026, 3, 19)
    signals = generate_signals(
        targets=[],
        holdings=[],
        total_value=100_000.0,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    assert len(signals) == 1
    assert signals[0].type == "BUY"
    assert signals[0].etf == DEFAULT_DEFENSIVE_ETF
    assert "防御" in signals[0].reason


def test_generate_signals_sell_includes_market_value_and_pnl() -> None:
    market = _mock_market({"510300.XSHG": 3.87, "159915.XSHE": 2.05})
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG"]
    holdings = [
        Portfolio(code="510300.XSHG", name="沪深300", shares=10_000, cost_price=3.95),
        Portfolio(code="159915.XSHE", name="创业板", shares=8_000, cost_price=2.10),
    ]
    signals = generate_signals(
        targets=targets,
        holdings=holdings,
        total_value=200_000.0,
        as_of=as_of,
        market=market,
        params=_params(),
    )
    sell = next(s for s in signals if s.etf == "159915.XSHE")
    expected_market_value = 2.05 * 8_000
    expected_pnl = (2.05 - 2.10) * 8_000
    assert sell.market_value == pytest.approx(expected_market_value)
    assert sell.pnl == pytest.approx(expected_pnl)
