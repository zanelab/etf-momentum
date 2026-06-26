"""12-1 momentum factor — pure functions, no I/O.

Classic AQR / Carhart definition:
    momentum(t) = close(t - skip - 1) / close(t - skip - 1 - lookback) - 1

Defaults `lookback=252, skip=21` correspond to 12 months of trading days
minus the most recent month (the "skip" avoids short-term reversal).
"""

from decimal import Decimal


def _validate_closes(
    closes: list[Decimal] | None,
    lookback: int,
    skip: int,
) -> bool:
    """Return True iff closes has enough valid Decimal data to compute a score."""
    if closes is None or len(closes) == 0:
        return False
    if len(closes) < skip + lookback + 1:
        return False
    recent = closes[-skip - 1]
    past = closes[-skip - 1 - lookback]
    if not isinstance(recent, Decimal) or not isinstance(past, Decimal):
        return False
    if recent <= 0 or past <= 0:
        return False
    return True


def compute_momentum_score(
    closes: list[Decimal],
    lookback: int = 252,
    skip: int = 21,
) -> Decimal | None:
    """Compute the 12-1 momentum score for a single ETF.

    Returns `(closes[-skip-1] / closes[-skip-1-lookback]) - 1`, or `None` when
    the input is too short, malformed, or contains non-positive prices.

    Result is not quantized — call sites that persist to a `Numeric(10,4)`
    column should quantize themselves.
    """
    if not _validate_closes(closes, lookback, skip):
        return None
    recent = closes[-skip - 1]
    past = closes[-skip - 1 - lookback]
    return recent / past - Decimal("1")


def compute_momentum_scores(
    price_history: dict[str, list[Decimal]],
    lookback: int = 252,
    skip: int = 21,
) -> dict[str, Decimal | None]:
    """Compute momentum scores for every code in `price_history`.

    Returns a fresh dict; the input is not mutated. Codes whose history is
    insufficient (or contains bad data) map to `None`.
    """
    return {
        code: compute_momentum_score(closes, lookback=lookback, skip=skip)
        for code, closes in price_history.items()
    }


def rank_scores(
    scores: dict[str, Decimal | None],
) -> list[tuple[str, int | None, Decimal | None]]:
    """Rank codes by score descending using competition ranking.

    Rules:
    - Tied scores share the same rank; the next non-tied rank skips the
      occupied slots (e.g. `[1, 1, 3]`).
    - Insertion order of `scores` is the stable tiebreaker (Python's
      `sorted` is stable).
    - Codes with a `None` score are appended at the end with `rank=None`;
      they do not consume any rank slot.
    """
    valid = [(code, score) for code, score in scores.items() if score is not None]
    nones = [(code, None) for code, score in scores.items() if score is None]

    valid.sort(key=lambda kv: kv[1], reverse=True)

    ranked: list[tuple[str, int | None, Decimal | None]] = []
    prev_score: Decimal | None = None
    last_rank: int | None = None
    for index, (code, score) in enumerate(valid):
        if index == 0:
            rank = 1
        elif score == prev_score:
            rank = last_rank  # tie — share the previous rank
        else:
            rank = index + 1  # skip slots occupied by the previous tie group
        ranked.append((code, rank, score))
        prev_score = score
        last_rank = rank

    for code, _ in nones:
        ranked.append((code, None, None))

    return ranked