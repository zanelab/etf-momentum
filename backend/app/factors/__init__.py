"""Factor calculation primitives — pure functions on price history.

12-1 momentum factor (AQR / Carhart standard): measures 12-month return
excluding the most recent month. See `momentum.compute_momentum_score`.
"""

from app.factors.momentum import (
    compute_momentum_score,
    compute_momentum_scores,
    rank_scores,
)

__all__ = [
    "compute_momentum_score",
    "compute_momentum_scores",
    "rank_scores",
]