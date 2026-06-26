"""Real-time signal computation — pure functions, no DB.

Given an ETF pool and price history, compute today's momentum ranking and
generate BUY / HOLD / WATCH actions. Reuses app.factors.momentum for the
underlying score and rank algorithms.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.factors.momentum import compute_momentum_scores, rank_scores


# 6 位小数，与 SignalSnapshot.momentum_score: Numeric(10,6) 对齐
SCORE_QUANT = Decimal("0.000001")


@dataclass(frozen=True)
class SignalRow:
    etf_code: str
    momentum_score: Decimal | None  # quantize 到 6 位；None → WATCH
    rank: int | None                # WATCH 时为 None
    action: str                     # "BUY" / "HOLD" / "WATCH"


def _quantize_score(score: Decimal | None) -> Decimal | None:
    if score is None:
        return None
    return score.quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)


def compute_signals(
    etf_pool: list[str],
    price_history: dict[str, list[tuple[date, Decimal]]],
    signal_date: date,
    *,
    top_n: int = 5,
    lookback: int = 252,
    skip: int = 21,
) -> list[SignalRow]:
    """Compute momentum ranking + action for each ETF in pool at signal_date.

    Args:
        etf_pool: list of ETF codes to score.
        price_history: {code: [(date, close), ...]} — may include dates on or
            after `signal_date`; only closes strictly before signal_date are used.
        signal_date: the "as-of" date for the signal.
        top_n: top-N ranked ETFs get action='BUY'.
        lookback, skip: 12-1 momentum parameters (passed to compute_momentum_scores).

    Returns:
        list[SignalRow] sorted by rank ascending (Nones at the end, then by
        etf_code for stable order). Action is BUY / HOLD / WATCH.
        WATCH: code is in pool but price history is insufficient
               (< lookback + skip + 1 closes before signal_date).
        BUY: rank ≤ top_n (1-indexed).
        HOLD: rank > top_n.

    Raises:
        ValueError: if top_n <= 0.
    """
    if top_n <= 0:
        raise ValueError(f"top_n must be >= 1, got {top_n}")

    # 1. Slice closes per code, dropping dates >= signal_date
    closes_by_code: dict[str, list[Decimal]] = {}
    for code in etf_pool:
        series = price_history.get(code, [])
        filtered = [c for d, c in series if d < signal_date]
        if len(filtered) < lookback + skip + 1:
            continue  # WATCH — will be appended later
        closes_by_code[code] = filtered[-(lookback + skip + 1):]

    # 2. Score + rank (reuse momentum module)
    scores = compute_momentum_scores(closes_by_code, lookback=lookback, skip=skip)
    ranked = rank_scores(scores)  # (code, rank, score) in score-desc order

    # 3. Assign action
    rows: list[SignalRow] = []
    for code, rank, score in ranked:
        if score is None:
            action = "WATCH"
        elif rank is not None and rank <= top_n:
            action = "BUY"
        else:
            action = "HOLD"
        rows.append(SignalRow(
            etf_code=code,
            momentum_score=_quantize_score(score),
            rank=rank,
            action=action,
        ))

    # 4. WATCH rows: codes in pool that were dropped at step 1
    covered = {r.etf_code for r in rows}
    for code in etf_pool:
        if code in covered:
            continue
        if code not in price_history:
            # pool 中但 price_history 完全没数据 → 视为 WATCH
            rows.append(SignalRow(
                etf_code=code,
                momentum_score=None,
                rank=None,
                action="WATCH",
            ))
        else:
            # pool 中、有数据、但长度不足 → WATCH
            rows.append(SignalRow(
                etf_code=code,
                momentum_score=None,
                rank=None,
                action="WATCH",
            ))

    # 5. Sort: WATCH (rank=None) at end, then by etf_code for stable order
    rows.sort(key=lambda r: (
        1 if r.rank is None else 0,
        r.rank if r.rank is not None else 0,
        r.etf_code,
    ))
    return rows


__all__ = ["SignalRow", "compute_signals"]
