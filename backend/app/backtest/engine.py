"""Backtest engine: takes price history, produces NAV curve + performance metrics.

Pure functions — no DB access, no logging side-effects, deterministic given
the same inputs. Persistence is a separate concern (see persistence.py).

Algorithm:
1. Build trading calendar (union of all dates in [start, end])
2. Determine rebalance dates (last trading day of each month/quarter)
3. Walk each trading day:
   a. Liquidate any held positions whose data has stopped (delisted ETF)
   b. Mark-to-market → append (date, NAV) to nav_series
   c. If today is a rebalance day: score → rank → top-N → equal-weight buy
4. Compute performance metrics from nav_series
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Iterable

from app.factors.momentum import compute_momentum_scores, rank_scores


class RebalanceFrequency(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass(frozen=True)
class BacktestParams:
    etf_pool: list[str]
    start: date
    end: date
    initial_cash: Decimal
    lookback: int = 252
    skip: int = 21
    top_n: int = 5
    rebalance_freq: RebalanceFrequency = RebalanceFrequency.MONTHLY


@dataclass(frozen=True)
class RebalanceEvent:
    date: date
    scores: dict[str, Decimal | None]
    selected: list[str]
    weights: dict[str, Decimal]


@dataclass
class BacktestResult:
    nav_series: list[tuple[date, Decimal]]
    rebalance_log: list[RebalanceEvent]
    metrics: dict[str, Decimal | None]


# ---------------------------------------------------------------------------
# Validation / calendar helpers
# ---------------------------------------------------------------------------


def _validate_params(
    params: BacktestParams,
    price_history: dict[str, list[tuple[date, Decimal]]],
) -> None:
    if params.end < params.start:
        raise ValueError(f"end ({params.end}) must be >= start ({params.start})")
    if params.initial_cash <= 0:
        raise ValueError(f"initial_cash must be > 0, got {params.initial_cash}")
    if params.top_n < 1:
        raise ValueError(f"top_n must be >= 1, got {params.top_n}")
    if params.lookback < 1:
        raise ValueError(f"lookback must be >= 1, got {params.lookback}")
    if params.skip < 0:
        raise ValueError(f"skip must be >= 0, got {params.skip}")
    if not params.etf_pool:
        raise ValueError("etf_pool cannot be empty")
    # Pool codes must all appear in price_history (caller responsibility, but
    # catch obvious mismatches)
    missing = [c for c in params.etf_pool if c not in price_history]
    if missing:
        raise ValueError(f"price_history missing etf_pool codes: {missing}")


def _build_calendar(
    price_history: dict[str, list[tuple[date, Decimal]]],
    start: date,
    end: date,
) -> list[date]:
    """Union of all dates in [start, end], sorted."""
    dates: set[date] = set()
    for series in price_history.values():
        for d, _ in series:
            if start <= d <= end:
                dates.add(d)
    return sorted(dates)


def _find_rebalance_dates(
    calendar: Iterable[date],
    freq: RebalanceFrequency,
) -> set[date]:
    """Last trading day of each month (MONTHLY) or quarter (QUARTERLY)."""
    by_period: dict[tuple, date] = {}
    for d in calendar:
        if freq == RebalanceFrequency.MONTHLY:
            key = (d.year, d.month)
        else:
            q = (d.month - 1) // 3 + 1
            key = (d.year, q)
        if key not in by_period or d > by_period[key]:
            by_period[key] = d
    return set(by_period.values())


def _build_close_lookup(
    price_history: dict[str, list[tuple[date, Decimal]]],
) -> dict[date, dict[str, Decimal]]:
    """{date: {code: close}} for O(1) date-code lookups."""
    lookup: dict[date, dict[str, Decimal]] = {}
    for code, series in price_history.items():
        for d, c in series:
            lookup.setdefault(d, {})[code] = c
    return lookup


def _slice_closes_for_momentum(
    price_history: dict[str, list[tuple[date, Decimal]]],
    code: str,
    end_date: date,
    lookback: int,
    skip: int,
) -> list[Decimal] | None:
    """Last (lookback + skip + 1) closes of `code` strictly before end_date.

    Returns None if insufficient history.
    """
    series = price_history.get(code, [])
    # Filter to dates strictly before end_date (we don't use end_date's close)
    filtered = [c for d, c in series if d < end_date]
    if len(filtered) < lookback + skip + 1:
        return None
    return filtered[-(lookback + skip + 1):]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _decimal_pow(base: Decimal, exponent: Decimal) -> Decimal:
    """Fractional-exponent power via float intermediate (used only for annualized).

    Acceptable here: annualized return is a derived statistic; the underlying
    NAV values themselves stay full-precision Decimal.
    """
    import math
    if base <= 0:
        return Decimal("0")
    return Decimal(str(math.pow(float(base), float(exponent))))


def _compute_metrics(
    nav_series: list[tuple[date, Decimal]],
    initial_cash: Decimal,
) -> dict[str, Decimal | None]:
    """Compute total / annualized / max drawdown / sharpe from a NAV series."""
    if not nav_series:
        return {
            "total_return": Decimal("0"),
            "annualized_return": Decimal("0"),
            "max_drawdown": Decimal("0"),
            "sharpe_ratio": None,
        }

    initial = initial_cash
    final = nav_series[-1][1]
    total_return = final / initial - Decimal("1")

    days = (nav_series[-1][0] - nav_series[0][0]).days
    if days > 0 and final > 0 and initial > 0:
        years = Decimal(days) / Decimal("365")
        annualized_return = (
            _decimal_pow(final / initial, Decimal(1) / years) - Decimal("1")
        )
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

    sharpe_ratio: Decimal | None
    if len(daily_returns) < 2:
        sharpe_ratio = None
    else:
        n = Decimal(len(daily_returns))
        mean_r = sum(daily_returns, Decimal("0")) / n
        variance = sum((r - mean_r) ** 2 for r in daily_returns) / (n - Decimal("1"))
        std_r = variance.sqrt()
        if std_r == 0:
            sharpe_ratio = None
        else:
            sharpe_ratio = (mean_r / std_r) * Decimal("252").sqrt()

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe_ratio,
    }


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


def run_backtest(
    params: BacktestParams,
    price_history: dict[str, list[tuple[date, Decimal]]],
) -> BacktestResult:
    """Simulate a momentum strategy over `params.start` to `params.end`.

    Steps per trading day:
    1. Liquidate held positions whose data has stopped (delisted → cash)
    2. Mark-to-market → append NAV
    3. If today is a rebalance date: score → rank → top-N → equal-weight buy
    """
    _validate_params(params, price_history)

    calendar = _build_calendar(price_history, params.start, params.end)
    rebalance_set = _find_rebalance_dates(calendar, params.rebalance_freq)
    close_lookup = _build_close_lookup(price_history)

    shares: dict[str, Decimal] = {}
    cash: Decimal = params.initial_cash
    nav_series: list[tuple[date, Decimal]] = []
    rebalance_log: list[RebalanceEvent] = []

    for current_date in calendar:
        # Step 1: liquidate held codes whose data stopped (delisted)
        for code in list(shares.keys()):
            if code not in close_lookup.get(current_date, {}):
                # Find last available close strictly before today
                series = price_history.get(code, [])
                last_close: Decimal | None = None
                for d, c in series:
                    if d < current_date:
                        last_close = c
                    else:
                        break
                if last_close is not None and last_close > 0:
                    cash += shares[code] * last_close
                del shares[code]

        # Step 2: mark-to-market
        day_closes = close_lookup.get(current_date, {})
        nav = cash + sum(
            shares[c] * day_closes.get(c, Decimal("0")) for c in shares
        )
        nav_series.append((current_date, nav))

        # Step 3: rebalance?
        if current_date not in rebalance_set:
            continue

        scores = _compute_scores(price_history, params, current_date)
        ranked = rank_scores(scores)
        top = [(c, r) for (c, r, s) in ranked if s is not None][: params.top_n]
        if not top:
            continue

        # Sell everything → cash = NAV
        cash = nav

        # Filter to codes with positive close on rebalance day
        buy_codes = [code for code, _ in top if day_closes.get(code, Decimal("0")) > 0]
        if not buy_codes:
            continue

        n = len(buy_codes)
        weight = Decimal(1) / Decimal(n)
        new_shares: dict[str, Decimal] = {}
        for code in buy_codes:
            close = day_closes[code]
            allocation = cash * weight
            new_shares[code] = allocation / close
            cash -= allocation

        shares = new_shares
        # Quantize weights to 10 decimals for cleanliness, then assign the residual
        # to the last code so sum(weights) is exactly Decimal("1") regardless of n.
        quant = Decimal("0.0000000001")
        base_weight = (Decimal(1) / Decimal(n)).quantize(quant)
        weights: dict[str, Decimal] = {}
        for i, code in enumerate(buy_codes):
            if i < len(buy_codes) - 1:
                weights[code] = base_weight
            else:
                weights[code] = Decimal(1) - sum(weights.values())
        rebalance_log.append(
            RebalanceEvent(
                date=current_date,
                scores=scores,
                selected=buy_codes,
                weights=weights,
            )
        )

    metrics = _compute_metrics(nav_series, params.initial_cash)
    return BacktestResult(
        nav_series=nav_series,
        rebalance_log=rebalance_log,
        metrics=metrics,
    )


def _compute_scores(
    price_history: dict[str, list[tuple[date, Decimal]]],
    params: BacktestParams,
    rebalance_date: date,
) -> dict[str, Decimal | None]:
    """Compute momentum scores for each ETF, using closes before rebalance_date."""
    closes_by_code: dict[str, list[Decimal]] = {}
    for code in params.etf_pool:
        window = _slice_closes_for_momentum(
            price_history, code, rebalance_date, params.lookback, params.skip
        )
        if window is not None:
            closes_by_code[code] = window
    return compute_momentum_scores(
        closes_by_code, lookback=params.lookback, skip=params.skip
    )