"""Performance metrics for a NAV series — pure functions, no DB.

Extracted from app.backtest.engine so the live-signal module (future) can
compute the same indicators on a same-day simulated portfolio without
importing the whole engine.

Six indicators returned by compute_metrics:
- total_return, annualized_return, max_drawdown, sharpe_ratio,
  sortino_ratio, calmar_ratio

Edge cases:
- Empty nav_series → all values 0 or None (zero metrics dict)
- Single point → ratios None, total_return 0
- Constant NAV → sharpe / sortino None (std = 0)
- No negative returns → sortino None
- max_drawdown = 0 → calmar None
"""

import math
from decimal import Decimal
from typing import Iterable


ANNUALIZATION = Decimal(252).sqrt()


def _decimal_pow(base: Decimal, exponent: Decimal) -> Decimal:
    """Fractional-exponent power via float intermediate.

    Used only for annualized return — a derived statistic. NAV values
    themselves stay full-precision Decimal.
    """
    if base <= 0:
        return Decimal("0")
    return Decimal(str(math.pow(float(base), float(exponent))))


def _zero_metrics() -> dict[str, Decimal | None]:
    return {
        "total_return": Decimal("0"),
        "annualized_return": Decimal("0"),
        "max_drawdown": Decimal("0"),
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "calmar_ratio": None,
    }


def _annualized_ratio(
    excess_returns: list[Decimal],
    raw_returns_for_std: list[Decimal],
) -> Decimal | None:
    """Standard annualized ratio: mean(excess) / std(raw) * sqrt(252).

    `raw_returns_for_std` is the population used for the denominator:
    - sharpe: all daily returns
    - sortino: only the negative daily returns (downside deviation)

    Variance is computed with Bessel's correction (n-1).
    """
    if len(excess_returns) < 2 or len(raw_returns_for_std) < 2:
        return None
    mean_excess = sum(excess_returns, Decimal("0")) / Decimal(len(excess_returns))
    mean_raw = sum(raw_returns_for_std, Decimal("0")) / Decimal(len(raw_returns_for_std))
    variance = sum(
        (r - mean_raw) ** 2 for r in raw_returns_for_std
    ) / Decimal(len(raw_returns_for_std) - 1)
    std = variance.sqrt()
    if std == 0:
        return None
    return (mean_excess / std) * ANNUALIZATION


def compute_metrics(
    nav_series: list[tuple],
    initial_cash: Decimal,
    *,
    risk_free_rate: Decimal = Decimal("0"),
) -> dict[str, Decimal | None]:
    """Compute 6 performance indicators from a NAV series.

    Args:
        nav_series: List of (date, Decimal NAV) tuples, sorted by date ascending.
        initial_cash: Starting capital (for total_return calculation).
        risk_free_rate: Annualized risk-free rate (default 0). Per-day rate
            is computed as risk_free_rate / 252.

    Returns:
        dict with keys: total_return, annualized_return, max_drawdown,
        sharpe_ratio, sortino_ratio, calmar_ratio. Ratios are None when
        they cannot be computed (e.g. zero variance, no negative returns).
    """
    if not nav_series:
        return _zero_metrics()

    final = nav_series[-1][1]
    total_return = final / initial_cash - Decimal("1")

    days = (nav_series[-1][0] - nav_series[0][0]).days
    if days > 0 and final > 0 and initial_cash > 0:
        years = Decimal(days) / Decimal("365")
        annualized_return = _decimal_pow(
            final / initial_cash, Decimal(1) / years
        ) - Decimal("1")
    else:
        annualized_return = Decimal("0")

    peak = nav_series[0][1]
    max_dd = Decimal("0")
    for _, nav in nav_series:
        if nav > peak:
            peak = nav
        if peak > 0:
            dd = peak / nav - Decimal("1")
            if dd > max_dd:
                max_dd = dd

    daily_returns: list[Decimal] = []
    for i in range(1, len(nav_series)):
        prev = nav_series[i - 1][1]
        curr = nav_series[i][1]
        if prev > 0:
            daily_returns.append(curr / prev - Decimal("1"))

    daily_rf = risk_free_rate / Decimal("252")
    excess_returns = [r - daily_rf for r in daily_returns]

    sharpe_ratio = _annualized_ratio(excess_returns, daily_returns)

    negative_returns = [r for r in excess_returns if r < 0]
    sortino_ratio = _annualized_ratio(excess_returns, negative_returns)

    if max_dd > 0:
        calmar_ratio: Decimal | None = annualized_return / max_dd
    else:
        calmar_ratio = None

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "calmar_ratio": calmar_ratio,
    }


__all__ = ["compute_metrics", "ANNUALIZATION"]
