"""Backtest engine: daily replay of filter_etfs with equal-weight allocation.

Algorithm:
- On each trading day t in [start, end]:
  1. Run filter_etfs against data up to t-1 (history window) + t snapshot
  2. Liquidate current positions (mark-to-market)
  3. Allocate equal-weight to today's targets (or fall back to defensive ETF
     if no targets)
- Track daily NAV starting at 1.0
- Stats: total_return, annualized_sharpe, max_drawdown, trading_days, n_rebalances
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import numpy as np

from app.data_sources.base import DataNotFoundError, MarketDataSource
from app.services.screening import filter_etfs
from app.services.types import StrategyParams

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"


@dataclass
class NAVSeries:
    dates: list[date] = field(default_factory=list)
    navs: list[float] = field(default_factory=list)
    daily_returns: list[float] = field(default_factory=list)


@dataclass
class BacktestStats:
    initial_nav: float
    final_nav: float
    total_return: float
    annualized_return: float
    sharpe: float
    max_drawdown: float
    trading_days: int
    n_rebalances: int


@dataclass
class BacktestResult:
    start: date
    end: date
    nav_series: NAVSeries
    stats: BacktestStats
    equity_curve: list[dict[str, Any]]  # [{date, nav, daily_return}, ...]


def _trading_days(start: date, end: date) -> list[date]:
    """Return sorted list of trading days in [start, end]."""
    import pandas as pd

    days: set[date] = set()
    for csv_path in FIXTURES_DIR.glob("*.csv"):
        df = pd.read_csv(csv_path, parse_dates=["date"], usecols=["date"])
        in_window = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
        days.update(in_window["date"].dt.date.tolist())
    return sorted(days)


def _annualized_return(total_return: float, n_days: int) -> float:
    if n_days <= 0:
        return 0.0
    return (1 + total_return) ** (250 / n_days) - 1


def _sharpe(daily_returns: list[float]) -> float:
    if len(daily_returns) < 2:
        return 0.0
    arr = np.array(daily_returns, dtype=float)
    std = float(arr.std(ddof=1))
    if std == 0:
        return 0.0
    return float(arr.mean() / std * math.sqrt(250))


def _max_drawdown(navs: list[float]) -> float:
    if not navs:
        return 0.0
    arr = np.array(navs, dtype=float)
    peak = np.maximum.accumulate(arr)
    drawdown = (arr - peak) / peak
    return float(drawdown.min())


def _filter_targets_for_day(
    as_of: datetime,
    *,
    params: StrategyParams,
    market: MarketDataSource,
    static_pool: list[str],
    themes: dict[str, list[str]],
    display_names: dict[str, str],
) -> list[str]:
    return filter_etfs(
        as_of,
        static_pool=static_pool,
        dynamic_pool=[],
        themes=themes,
        params=params,
        market=market,
        display_names=display_names,
    )


def run_backtest(
    *,
    start: date,
    end: date,
    params: StrategyParams,
    market: MarketDataSource,
    static_pool: list[str],
    themes: dict[str, list[str]],
    display_names: dict[str, str],
    initial_nav: float = 1.0,
) -> BacktestResult:
    days = _trading_days(start, end)
    if not days:
        empty = NAVSeries()
        return BacktestResult(
            start=start,
            end=end,
            nav_series=empty,
            stats=BacktestStats(
                initial_nav=initial_nav,
                final_nav=initial_nav,
                total_return=0.0,
                annualized_return=0.0,
                sharpe=0.0,
                max_drawdown=0.0,
                trading_days=0,
                n_rebalances=0,
            ),
            equity_curve=[],
        )

    # State: holdings {etf: shares}. Start with empty; day 0 we'll buy targets.
    holdings: dict[str, float] = {}  # etf -> shares (float for accuracy)
    cash: float = initial_nav
    current_targets: list[str] = []
    navs: list[float] = []
    dates: list[date] = []
    n_rebalances = 0

    for d in days:
        as_of = datetime.combine(d, time(14, 0))
        # 1) Compute NAV at start of day using yesterday's close (or starting cash).
        if holdings:
            nav_today = cash
            for etf, shares in holdings.items():
                try:
                    snap = market.snapshot(etf, as_of)
                    nav_today += float(snap["last_price"]) * shares
                except DataNotFoundError:
                    # ETF delisted/missing: treat as zero
                    continue
        else:
            nav_today = cash

        navs.append(nav_today)
        dates.append(d)

        # 2) Determine today's targets
        targets = _filter_targets_for_day(
            as_of,
            params=params,
            market=market,
            static_pool=static_pool,
            themes=themes,
            display_names=display_names,
        )
        if not targets:
            targets = [params.defensive_etf] if params.defensive_etf else []

        # 3) Rebalance if targets changed
        if set(targets) != set(current_targets):
            # Liquidate current
            cash = nav_today
            holdings = {}
            # Buy new equal-weight
            if targets:
                per_target = cash / len(targets)
                for etf in targets:
                    try:
                        snap = market.snapshot(etf, as_of)
                        last_price = float(snap["last_price"])
                    except DataNotFoundError:
                        continue
                    if last_price <= 0:
                        continue
                    shares = per_target / last_price
                    holdings[etf] = shares
                cash = nav_today - sum(holdings[e] * market.snapshot(e, as_of)["last_price"] for e in holdings)
            current_targets = targets
            n_rebalances += 1

    # Daily returns
    daily_returns: list[float] = []
    prev = initial_nav
    for nav in navs:
        daily_returns.append((nav / prev) - 1)
        prev = nav

    final_nav = navs[-1]
    total_return = final_nav / initial_nav - 1
    ann_ret = _annualized_return(total_return, len(days))
    sharpe = _sharpe(daily_returns)
    mdd = _max_drawdown(navs)

    nav_series = NAVSeries(dates=dates, navs=navs, daily_returns=daily_returns)
    assert len(dates) == len(navs) == len(daily_returns)
    equity_curve: list[dict[str, Any]] = []
    for i in range(len(dates)):
        equity_curve.append(
            {
                "date": dates[i].isoformat(),
                "nav": navs[i],
                "daily_return": daily_returns[i],
            }
        )
    stats = BacktestStats(
        initial_nav=initial_nav,
        final_nav=final_nav,
        total_return=total_return,
        annualized_return=ann_ret,
        sharpe=sharpe,
        max_drawdown=mdd,
        trading_days=len(days),
        n_rebalances=n_rebalances,
    )
    return BacktestResult(
        start=start,
        end=end,
        nav_series=nav_series,
        stats=stats,
        equity_curve=equity_curve,
    )
