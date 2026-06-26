"""Backtest result persistence — write BacktestRun ORM rows."""

import json
from decimal import Decimal

from sqlalchemy.orm import Session

from app.backtest.engine import BacktestParams, BacktestResult
from app.models.backtest_run import BacktestRun


def _decimal_to_str(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return str(v)


def save_backtest_run(
    session: Session,
    params: BacktestParams,
    result: BacktestResult,
) -> BacktestRun:
    """Persist a BacktestResult as a BacktestRun row.

    The ORM has no dedicated columns for skip / top_n / initial_cash / final_nav;
    these are stored inside the `metrics` JSON column under the `params` key
    so a future reader can fully reconstruct the inputs that produced this run.
    """
    final_nav = result.nav_series[-1][1] if result.nav_series else None

    metrics_payload: dict[str, object] = {
        "total_return": _decimal_to_str(result.metrics.get("total_return")),
        "annualized_return": _decimal_to_str(result.metrics.get("annualized_return")),
        "max_drawdown": _decimal_to_str(result.metrics.get("max_drawdown")),
        "sharpe_ratio": _decimal_to_str(result.metrics.get("sharpe_ratio")),
        "params": {
            "lookback": params.lookback,
            "skip": params.skip,
            "top_n": params.top_n,
            "initial_cash": str(params.initial_cash),
            "final_nav": str(final_nav) if final_nav is not None else None,
        },
    }
    # Mirror final_nav at top level for query convenience
    metrics_payload["final_nav"] = str(final_nav) if final_nav is not None else None

    run = BacktestRun(
        name=None,
        etf_pool=list(params.etf_pool),
        momentum_window=params.lookback,
        rebalance_freq=params.rebalance_freq.value,
        start_date=params.start,
        end_date=params.end,
        metrics=metrics_payload,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run