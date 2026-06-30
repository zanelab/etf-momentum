"""Signal generation: compare screening targets to current holdings.

Mirrors main.py's sell_routine + buy_routine:
- SELL any holding not in today's targets (defensive ETF is exempt unless
  explicitly listed).
- BUY each target not currently held, in equal-weight tranches sized by
  `total_value / len(targets)` and rounded down to multiples of 100 shares.
- If `targets` is empty, switch to defensive mode and buy the defensive ETF.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List

from app.data_sources.base import DataNotFoundError, MarketDataSource
from app.models.portfolio import Portfolio
from app.services.types import StrategyParams

SignalType = Literal["BUY", "SELL"]
ETF_LOT_SIZE = 100


@dataclass(frozen=True)
class Signal:
    type: SignalType
    etf: str
    reason: str
    shares: Optional[int] = None
    target_value: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None


def _round_lot(shares: float) -> int:
    return max(int(shares // ETF_LOT_SIZE) * ETF_LOT_SIZE, 0)


def generate_signals(
    *,
    targets: List[str],
    holdings: List[Portfolio],
    total_value: float,
    as_of: datetime,
    market: MarketDataSource,
    params: StrategyParams,
) -> List[Signal]:
    """Return the rebalance signals for today.

    Output order: SELL signals first (free cash), then BUY signals. Each
    signal carries the data needed by the UI: SELL has market_value + pnl;
    BUY has target_value + rounded share count.
    """
    defensive = params.defensive_etf
    target_set = set(targets)
    holding_map = {h.code: h for h in holdings}

    signals: List[Signal] = []

    # ── SELL signals: drop anything held that isn't a target
    for code, h in holding_map.items():
        if code == defensive:
            continue
        if code in target_set:
            continue
        try:
            snap = market.snapshot(code, as_of)
        except DataNotFoundError:
            continue
        last_price = float(snap["last_price"])
        market_value = last_price * h.shares
        pnl = (last_price - h.cost_price) * h.shares
        signals.append(
            Signal(
                type="SELL",
                etf=code,
                reason="不在今日目标列表",
                shares=h.shares,
                market_value=market_value,
                pnl=pnl,
            )
        )

    # ── BUY signals
    buy_targets = list(target_set)
    if not buy_targets:
        if defensive:
            buy_targets = [defensive]
            defensive_reason = "无动量目标，切换防御模式"
        else:
            return signals

    per_target_value = total_value / len(buy_targets)
    for code in buy_targets:
        if code in holding_map:
            continue
        try:
            snap = market.snapshot(code, as_of)
        except DataNotFoundError:
            continue
        last_price = float(snap["last_price"])
        if last_price <= 0:
            continue
        shares = _round_lot(per_target_value / last_price)
        if shares <= 0:
            continue
        reason = defensive_reason if buy_targets == [defensive] and code == defensive else "今日新进目标"
        signals.append(
            Signal(
                type="BUY",
                etf=code,
                reason=reason,
                shares=shares,
                target_value=per_target_value,
            )
        )

    return signals
