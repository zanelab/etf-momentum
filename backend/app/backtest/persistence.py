"""Backtest result persistence — write BacktestRun ORM rows."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.backtest.engine import BacktestParams, BacktestResult
from app.models.backtest_run import BacktestRun


def _decimal_to_str(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return str(v)


def _nav_to_json(nav_series: list[tuple]) -> list[dict[str, str]]:
    """[(date, Decimal), ...] → [{"date": "YYYY-MM-DD", "nav": "..."}]"""
    out: list[dict[str, str]] = []
    for d, nav in nav_series:
        out.append({"date": d.isoformat(), "nav": str(nav)})
    return out


def save_backtest_run(
    session: Session,
    params: BacktestParams,
    result: BacktestResult,
) -> BacktestRun:
    """Persist a BacktestResult as a BacktestRun row.

    The ORM has no dedicated columns for skip / top_n / initial_cash / final_nav;
    these are stored inside the `metrics` JSON column under the `params` key
    so a future reader can fully reconstruct the inputs that produced this run.

    The full `nav_series` is stored in the dedicated `nav_series` JSON column
    so the GET /backtest/{id}/nav endpoint can return it without recomputing.
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
        nav_series=_nav_to_json(result.nav_series),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
