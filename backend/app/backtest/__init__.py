"""Backtest engine — pure-function portfolio simulation on momentum signals.

Given a price history and BacktestParams, run_backtest produces a NAV
series, rebalance log, and standard performance metrics. No DB access.
"""

from app.backtest.engine import (
    BacktestParams,
    BacktestResult,
    RebalanceEvent,
    RebalanceFrequency,
    run_backtest,
)
from app.backtest.metrics import compute_metrics
from app.backtest.persistence import save_backtest_run

__all__ = [
    "BacktestParams",
    "BacktestResult",
    "RebalanceEvent",
    "RebalanceFrequency",
    "compute_metrics",
    "run_backtest",
    "save_backtest_run",
]