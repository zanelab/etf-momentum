"""Backtest HTTP endpoints (POST to create, GET to query)."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.data_sources.fixture import FixtureCSVSource
from app.services.backtest import run_backtest
from app.services.backtest_task import (
    create_task,
    get_task,
    mark_completed,
    mark_failed,
)
from app.services.today import (
    load_display_names,
    load_static_pool,
    load_strategy_params,
    select_kwargs_for_params,
)
from app.services.types import StrategyParams

log = logging.getLogger(__name__)

router = APIRouter(tags=["backtest"])
MAX_WINDOW_DAYS = 366  # inclusive guard, ~1 trading year

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def _market() -> FixtureCSVSource:
    return FixtureCSVSource(FIXTURES_DIR)


class BacktestRequest(BaseModel):
    start: date
    end: date
    initial_nav: float = Field(default=1.0, gt=0)


def _serialize_result(result) -> dict:
    return {
        "start": result.start.isoformat(),
        "end": result.end.isoformat(),
        "stats": {
            "initial_nav": result.stats.initial_nav,
            "final_nav": result.stats.final_nav,
            "total_return": result.stats.total_return,
            "annualized_return": result.stats.annualized_return,
            "sharpe": result.stats.sharpe,
            "max_drawdown": result.stats.max_drawdown,
            "trading_days": result.stats.trading_days,
            "n_rebalances": result.stats.n_rebalances,
        },
        "nav_series": result.equity_curve,
    }


def _run_task(task_id: str, request: BacktestRequest) -> None:
    try:
        merged = load_strategy_params()
        kwargs = select_kwargs_for_params(merged, set(StrategyParams.model_fields))
        params = StrategyParams(**kwargs)

        static_pool = load_static_pool()
        from app.services.today import load_themes

        themes = load_themes()
        display_names = load_display_names(static_pool)

        market = _market()
        result = run_backtest(
            start=request.start,
            end=request.end,
            params=params,
            market=market,
            static_pool=static_pool,
            themes=themes,
            display_names=display_names,
            initial_nav=request.initial_nav,
        )
        mark_completed(task_id, _serialize_result(result))
    except Exception as exc:  # noqa: BLE001 — surface to user
        log.exception("Backtest task %s failed", task_id)
        mark_failed(task_id, str(exc))


@router.post("")
def create_backtest(req: BacktestRequest, bg: BackgroundTasks) -> dict:
    if (req.end - req.start).days > MAX_WINDOW_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Backtest window exceeds {MAX_WINDOW_DAYS} days (got {(req.end - req.start).days}).",
        )
    if req.end <= req.start:
        raise HTTPException(status_code=400, detail="end must be after start.")

    merged = load_strategy_params()
    kwargs = select_kwargs_for_params(merged, set(StrategyParams.model_fields))
    params = StrategyParams(**kwargs)

    static_pool = load_static_pool()
    from app.services.today import load_themes

    themes = load_themes()
    display_names = load_display_names(static_pool)

    task_id = create_task(
        start=req.start,
        end=req.end,
        params=params,
        static_pool=static_pool,
        themes=themes,
        display_names=display_names,
    )
    bg.add_task(_run_task, task_id, req)
    return {"task_id": task_id, "status": "running"}


@router.get("/{task_id}")
def get_backtest(task_id: str) -> dict:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Backtest task not found: {task_id}")
    return task
