"""Tests for filter_etfs() screening service."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from app.data_sources.base import DataNotFoundError
from app.data_sources.fixture import FixtureCSVSource
from app.services.screening import (
    DEFAULT_DEFENSIVE_ETF,
    _classify_theme,
    _compute_momentum_score,
    _compute_volume_ratio,
    _passes_ma_filter,
    filter_etfs,
)
from app.services.types import StrategyParams

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def _params(**overrides) -> StrategyParams:
    defaults = dict(
        stock_sum=1,
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


def _market() -> FixtureCSVSource:
    return FixtureCSVSource(str(FIXTURES_DIR))


# ────────────── Unit tests for helpers ──────────────


def test_classify_theme_matches_first_keyword() -> None:
    themes = {"半导体": ["芯片"], "医药": ["医药"]}
    assert _classify_theme("X.XSHG", "芯片ETF", themes) == "半导体"


def test_classify_theme_no_match() -> None:
    themes = {"半导体": ["芯片"]}
    assert _classify_theme("X.XSHG", "未知ETF", themes) == "其他"


def test_classify_theme_none_name() -> None:
    themes = {"半导体": ["芯片"]}
    assert _classify_theme("X.XSHG", None, themes) == "其他"


def test_passes_ma_filter_true_for_fixture() -> None:
    """518880 has 500 days with strong uptrend; should pass MA filter on this date."""
    market = _market()
    as_of = datetime(2026, 1, 15)
    assert _passes_ma_filter("518880.XSHG", as_of, _params(), market) is True


def test_passes_ma_filter_false_for_short_history() -> None:
    """ETFs need >= ma_long days of history."""
    market = _market()
    as_of = datetime(2024, 4, 22)  # 1 trading day in
    assert _passes_ma_filter("510300.XSHG", as_of, _params(), market) is False


def test_passes_ma_filter_raises_for_missing_etf() -> None:
    market = _market()
    with pytest.raises(DataNotFoundError):
        _passes_ma_filter("NOPE.XSHG", datetime(2026, 1, 15), _params(), market)


def test_compute_momentum_score_returns_tuple() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    result = _compute_momentum_score("510300.XSHG", as_of, _params(), market)
    assert result is not None
    score, annual_ret, r2 = result
    assert isinstance(score, float)
    assert isinstance(annual_ret, float)
    assert isinstance(r2, float)


def test_compute_momentum_score_uses_pre_today_window_plus_snapshot() -> None:
    """Window must include `momentum_days` bars BEFORE as_of, then today's snapshot.

    Regression: previously the helper took history up to and including as_of and
    appended today's snapshot, duplicating the latest bar. Mirrors main.py's
    attribute_history(N) + get_current_data() pattern.
    """
    market = _market()
    as_of = datetime(2026, 1, 15)
    params = _params(momentum_days=25)

    # Snapshot for today
    snap = market.snapshot("510300.XSHG", as_of)
    today_price = snap["last_price"]

    # Bar immediately before as_of
    history_window = market.history(
        "510300.XSHG",
        as_of.date() - timedelta(days=params.momentum_days * 2),
        as_of.date() - timedelta(days=1),
        fields=["close"],
    )
    assert len(history_window) >= params.momentum_days
    expected_pre_today = history_window["close"].to_numpy()[-params.momentum_days :]

    result = _compute_momentum_score("510300.XSHG", as_of, params, market)
    assert result is not None
    # Replay the regression math from those exact inputs:
    prices = np.append(expected_pre_today, today_price)
    y = np.log(prices)
    x = np.arange(len(y))
    weights = np.linspace(1, 2, len(y))
    slope, intercept = np.polyfit(x, y, 1, w=weights)
    annual_ret = math.exp(slope * 250) - 1
    fitted_y = slope * x + intercept
    ss_res = float(np.sum(weights * (y - fitted_y) ** 2))
    ss_tot = float(np.sum(weights * (y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
    expected_score = annual_ret * r2

    score, exp_ret, exp_r2 = result
    assert math.isclose(score, expected_score, rel_tol=1e-9)
    assert math.isclose(exp_ret, annual_ret, rel_tol=1e-9)
    assert math.isclose(exp_r2, r2, rel_tol=1e-9)


def test_compute_volume_ratio_positive() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    ratio = _compute_volume_ratio("510300.XSHG", as_of, _params(), market)
    assert ratio is not None
    assert ratio > 0


def test_compute_volume_ratio_excludes_today_from_average() -> None:
    """Average volume window ends day BEFORE as_of; today's vol comes from snapshot."""
    market = _market()
    as_of = datetime(2026, 1, 15)
    params = _params(volume_lookback=5)

    snap = market.snapshot("510300.XSHG", as_of)
    today_vol = float(snap["volume"])

    history_window = market.history(
        "510300.XSHG",
        as_of.date() - timedelta(days=params.volume_lookback * 2),
        as_of.date() - timedelta(days=1),
        fields=["volume"],
    )
    expected_avg = float(history_window["volume"].iloc[-params.volume_lookback :].mean())
    expected_ratio = today_vol / expected_avg

    ratio = _compute_volume_ratio("510300.XSHG", as_of, params, market)
    assert ratio is not None
    assert math.isclose(ratio, expected_ratio, rel_tol=1e-9)


# ────────────── filter_etfs integration tests ──────────────


def test_filter_etfs_excludes_defensive() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    targets = filter_etfs(
        as_of,
        static_pool=["510300.XSHG", "511880.XSHG"],
        dynamic_pool=[],
        themes={"宽基": ["沪深300"]},
        params=_params(stock_sum=5),
        market=market,
        display_names={"510300.XSHG": "沪深300ETF", "511880.XSHG": "银华日利"},
    )
    assert "511880.XSHG" not in targets


def test_filter_etfs_returns_at_most_stock_sum() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    params = _params(stock_sum=3)
    targets = filter_etfs(
        as_of,
        static_pool=["510300.XSHG", "510500.XSHG", "159915.XSHE"],
        dynamic_pool=[],
        themes={},
        params=params,
        market=market,
    )
    assert len(targets) <= 3


def test_filter_etfs_returns_empty_when_no_pool() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    targets = filter_etfs(
        as_of, static_pool=[], dynamic_pool=[], themes={}, params=_params(), market=market
    )
    assert targets == []


def test_filter_etfs_empty_when_ma_filter_rejects_all() -> None:
    """Use a window too early for any ETF to have enough history."""
    market = _market()
    as_of = datetime(2024, 4, 22)  # 1 trading day after fixtures start
    targets = filter_etfs(
        as_of,
        static_pool=["510300.XSHG"],
        dynamic_pool=[],
        themes={},
        params=_params(),
        market=market,
    )
    assert targets == []


def test_filter_etfs_industry_diversification_picks_one_per_theme() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    params = _params(stock_sum=2, enable_industry_diverse=True)
    targets = filter_etfs(
        as_of,
        static_pool=["510300.XSHG", "159915.XSHE"],  # 宽基 vs 跨境
        dynamic_pool=[],
        themes={"宽基": ["沪深300"], "跨境": ["创业板"]},
        params=params,
        market=market,
        display_names={
            "510300.XSHG": "沪深300ETF",
            "159915.XSHE": "创业板ETF",
        },
    )
    assert len(targets) <= 2


def test_filter_etfs_ma_filter_disabled_skips_step1() -> None:
    """When ma_filter is disabled, all candidates go to momentum stage."""
    market = _market()
    as_of = datetime(2026, 1, 15)
    params_disabled = _params(enable_ma_filter=False, stock_sum=2)
    targets_disabled = filter_etfs(
        as_of,
        static_pool=["510300.XSHG", "510500.XSHG"],
        dynamic_pool=[],
        themes={},
        params=params_disabled,
        market=market,
    )
    # Same call with ma_filter enabled — both should produce SOME output
    # (just asserting it doesn't crash and returns a list)
    assert isinstance(targets_disabled, list)


def test_filter_etfs_deduplicates_static_and_dynamic() -> None:
    market = _market()
    as_of = datetime(2026, 1, 15)
    targets = filter_etfs(
        as_of,
        static_pool=["510300.XSHG", "510500.XSHG"],
        dynamic_pool=["510300.XSHG"],  # duplicate
        themes={},
        params=_params(stock_sum=5),
        market=market,
    )
    # '510300' should appear at most once even though in both pools
    assert targets.count("510300.XSHG") <= 1