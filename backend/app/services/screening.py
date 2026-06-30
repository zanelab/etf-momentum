from typing import Optional, List
"""ETF screening service — migrated from main.py filter_etfs().

Behavior is preserved verbatim: dual-MA filter, momentum scoring with weighted
log-linear regression, industry diversification selection. The original JoinQuant
APIs (`attribute_history`, `get_current_data`, etc.) are replaced by explicit
parameters and a `MarketDataSource` injection so the function is pure and testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from app.data_sources.base import DataNotFoundError, MarketDataSource
from app.data_sources.codes import normalize_etf_code
from app.services.types import StrategyParams

DEFAULT_DEFENSIVE_ETF = "511880.XSHG"


@dataclass(frozen=True)
class EtfScore:
    """Per-ETF scoring result returned by `filter_etfs_detailed`.

    `volume_ratio` is None when volume check is disabled (no ratio was computed).
    """
    code: str
    momentum_score: float
    annual_return: float
    r2: float
    volume_ratio: Optional[float]


def _classify_theme(etf: str, display_name: Optional[str], themes: dict[str, List[str]]) -> str:
    """Map an ETF to a theme by keyword match on display name.

    Mirrors `get_etf_industry()` from main.py: first match wins, else "其他".
    """
    if not display_name:
        return "其他"
    for theme, keywords in themes.items():
        for kw in keywords:
            if kw in display_name:
                return theme
    return "其他"


def _passes_ma_filter(
    etf: str,
    as_of: datetime,
    params: StrategyParams,
    market: MarketDataSource,
) -> bool:
    df = market.history(
        etf,
        as_of.date() - timedelta(days=params.ma_long * 2),
        as_of.date(),
        fields=["close"],
    )
    if df.empty or len(df) < params.ma_long:
        return False
    closes = df["close"].to_numpy()
    ma_short = float(np.mean(closes[-params.ma_short :]))
    ma_long = float(np.mean(closes[-params.ma_long :]))
    return bool(closes[-1] > ma_short and ma_short > ma_long)


def _compute_volume_ratio(
    etf: str,
    as_of: datetime,
    params: StrategyParams,
    market: MarketDataSource,
) -> float | None:
    df = market.history(
        etf,
        as_of.date() - timedelta(days=params.volume_lookback * 2),
        as_of.date() - timedelta(days=1),
        fields=["volume"],
    )
    if df.empty or len(df) < params.volume_lookback:
        return None
    avg_vol = float(df["volume"].iloc[-params.volume_lookback :].mean())
    if avg_vol <= 0:
        return None
    snap = market.snapshot(etf, as_of)
    today_vol = float(snap["volume"])
    if today_vol <= 0:
        return None
    return today_vol / avg_vol


def _compute_momentum_score(
    etf: str,
    as_of: datetime,
    params: StrategyParams,
    market: MarketDataSource,
) -> tuple[float, float, float] | None:
    """Return (score, annual_return, r2). None if data insufficient.

    Mirrors main.py: take the last `momentum_days` bars BEFORE `as_of`, then
    append today's snapshot bar — so the regression runs on N+1 points
    covering the full lookback window including today.
    """
    df = market.history(
        etf,
        as_of.date() - timedelta(days=params.momentum_days * 2),
        as_of.date() - timedelta(days=1),
        fields=["close"],
    )
    if df.empty or len(df) < params.momentum_days:
        return None
    prices = df["close"].to_numpy()[-params.momentum_days :]
    snap = market.snapshot(etf, as_of)
    current_price = float(snap["last_price"])
    prices = np.append(prices, current_price)
    if np.any(prices <= 0):
        return None
    y = np.log(prices)
    x = np.arange(len(y))
    weights = np.linspace(1, 2, len(y))
    slope, intercept = np.polyfit(x, y, 1, w=weights)
    annual_ret = math.exp(slope * 250) - 1
    fitted_y = slope * x + intercept
    ss_res = float(np.sum(weights * (y - fitted_y) ** 2))
    ss_tot = float(np.sum(weights * (y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0
    score = annual_ret * r2
    return (float(score), float(annual_ret), float(r2))


def filter_etfs(
    as_of: datetime,
    static_pool: List[str],
    dynamic_pool: List[str],
    themes: dict[str, List[str]],
    params: StrategyParams,
    market: MarketDataSource,
    display_names: dict[str, str] | None = None,
) -> List[str]:
    """Return today's target ETF list ordered by score (best first).

    Mirrors `filter_etfs()` in `main.py` (the JoinQuant version) with explicit
    parameters instead of global state / JoinQuant APIs.

    Pool fusion: combined_pool = unique(static ∪ dynamic), defensive_etf excluded.
    Step 1 (dual MA): drop candidates failing `close > MA_short > MA_long`.
    Step 2 (momentum): drop volume-spike, then score by `annual_return × R²`,
                       keep `0 < score < 5`.
    Step 3 (selection): with `enable_industry_diverse`, pick at most one ETF per
                        theme; fall back to top-scored if themes exhausted.
    """
    return [s.code for s in filter_etfs_detailed(
        as_of=as_of,
        static_pool=static_pool,
        dynamic_pool=dynamic_pool,
        themes=themes,
        params=params,
        market=market,
        display_names=display_names,
    )]


def filter_etfs_detailed(
    as_of: datetime,
    static_pool: List[str],
    dynamic_pool: List[str],
    themes: dict[str, List[str]],
    params: StrategyParams,
    market: MarketDataSource,
    display_names: dict[str, str] | None = None,
) -> List[EtfScore]:
    """Like `filter_etfs`, but returns per-ETF scoring details (spec §5.3 进阶).

    Returned list is ordered by score (best first). Volume_ratio is the value
    computed during the volume-check step; if volume check is disabled, it is
    None. `filter_etfs` is implemented in terms of this function.
    """
    display_names = display_names or {}

    # Pool fusion — normalize every input to canonical form so that bare
    # 6-digit codes (akshare) deduplicate with suffixed codes (static pool).
    pool: List[str] = list({normalize_etf_code(c) for c in static_pool + dynamic_pool})
    defensive_canonical = normalize_etf_code(params.defensive_etf)
    if defensive_canonical in pool:
        pool.remove(defensive_canonical)

    # Step 1: MA filter
    if params.enable_ma_filter:
        passed_ma: List[str] = []
        for etf in pool:
            try:
                if _passes_ma_filter(etf, as_of, params, market):
                    passed_ma.append(etf)
            except DataNotFoundError:
                continue
    else:
        passed_ma = list(pool)

    if not passed_ma:
        return []

    # Step 2: Volume check + momentum scoring
    score_list: List[EtfScore] = []
    for etf in passed_ma:
        try:
            vol_ratio: Optional[float] = None
            if params.enable_volume_check:
                vol_ratio = _compute_volume_ratio(etf, as_of, params, market)
                if vol_ratio is None or vol_ratio > params.volume_threshold:
                    continue
            result = _compute_momentum_score(etf, as_of, params, market)
            if result is None:
                continue
            score, annual_ret, r2 = result
            if 0 < score < 5:
                score_list.append(EtfScore(
                    code=etf,
                    momentum_score=float(score),
                    annual_return=float(annual_ret),
                    r2=float(r2),
                    volume_ratio=vol_ratio,
                ))
        except DataNotFoundError:
            continue

    score_list.sort(key=lambda s: s.momentum_score, reverse=True)

    # Step 3: Selection (with optional industry diversification)
    selected: List[EtfScore] = []
    if params.enable_industry_diverse:
        seen: set[str] = set()
        for entry in score_list:
            theme = _classify_theme(entry.code, display_names.get(entry.code), themes)
            if theme in seen:
                continue
            selected.append(entry)
            seen.add(theme)
            if len(selected) >= params.stock_sum:
                break
        # Fallback: relax theme constraint
        if len(selected) < params.stock_sum:
            for entry in score_list:
                if entry not in selected:
                    selected.append(entry)
                    if len(selected) >= params.stock_sum:
                        break
    else:
        selected = list(score_list[: params.stock_sum])

    return selected
