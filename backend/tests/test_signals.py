"""Tests for the signals service (sell + buy generation) and related API endpoints."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.data_sources.fixture import FixtureCSVSource
from app.services.portfolio_mock import Holding, get_mock_portfolio
from app.services.screening import DEFAULT_DEFENSIVE_ETF
from app.services.signals import (
    generate_signals,
)
from app.services.types import StrategyParams

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def _market() -> FixtureCSVSource:
    return FixtureCSVSource(FIXTURES_DIR)


def _params(**overrides) -> StrategyParams:
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


# ────────────── Portfolio mock ──────────────


def test_get_mock_portfolio_returns_three_holdings() -> None:
    portfolio = get_mock_portfolio(datetime(2026, 3, 19))
    assert len(portfolio) == 3
    for h in portfolio:
        assert isinstance(h, Holding)
        assert h.shares > 0
        assert h.shares % 100 == 0
        assert h.cost_price > 0


def test_get_mock_portfolio_codes_are_known_etfs() -> None:
    portfolio = get_mock_portfolio(datetime(2026, 3, 19))
    fixtures = {p.stem for p in FIXTURES_DIR.glob("*.csv")}
    for h in portfolio:
        assert h.code in fixtures


# ────────────── Signal generation ──────────────


def test_generate_signals_no_holdings_emits_only_buys() -> None:
    market = _market()
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
    market = _market()
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG"]
    holdings = [
        Holding(code="510300.XSHG", shares=10_000, cost_price=3.95),
        Holding(code="159915.XSHE", shares=8_000, cost_price=2.10),
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
    market = _market()
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG", "518880.XSHG"]
    holdings = [Holding(code="510300.XSHG", shares=10_000, cost_price=3.95)]
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
    market = _market()
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
    market = _market()
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG"]
    holdings = [Holding(code="510300.XSHG", shares=10_000, cost_price=3.95)]
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
    market = _market()
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
    market = _market()
    as_of = datetime(2026, 3, 19)
    targets = ["510300.XSHG"]
    holdings = [
        Holding(code="510300.XSHG", shares=10_000, cost_price=3.95),
        Holding(code="159915.XSHE", shares=8_000, cost_price=2.10),
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
    snap = market.snapshot("159915.XSHE", as_of)
    expected_market_value = snap["last_price"] * 8_000
    expected_pnl = (snap["last_price"] - 2.10) * 8_000
    assert sell.market_value == pytest.approx(expected_market_value)
    assert sell.pnl == pytest.approx(expected_pnl)
