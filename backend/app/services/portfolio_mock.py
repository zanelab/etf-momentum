"""Mock portfolio data for local development.

Returns a stable list of `Holding` rows for a given as-of date. Each ETF has
multiple-of-100 share counts and a plausible cost price below the typical
fixture close so unrealized P&L is realistic for the demo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Holding:
    code: str
    shares: int
    cost_price: float


# A stable 3-ETF mock portfolio. Mix of one wide-index, one sector, one cross-
# border so signal generation always has interesting sell/buy interactions.
_MOCK_PORTFOLIO: list[Holding] = [
    Holding(code="510300.XSHG", shares=10_000, cost_price=3.85),
    Holding(code="518880.XSHG", shares=5_000, cost_price=4.20),
    Holding(code="513100.XSHG", shares=12_000, cost_price=1.65),
]


def get_mock_portfolio(_as_of) -> list[Holding]:
    """Return the mock portfolio as-of `as_of` (datetime, currently ignored).

    The fixture window covers 2024-04 to 2026-03, so this same list works for
    any as_of within that range. Keeping the signature date-aware means the
    caller can later swap in a date-dependent source without changing API
    call sites.
    """
    return list(_MOCK_PORTFOLIO)
