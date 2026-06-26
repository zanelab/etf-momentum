"""Backtest 业务端点（v1）：create / list / detail / nav。"""

from datetime import date as _date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.etfs import _clamp_limit, _clamp_offset
from app.api.v1.schemas import BacktestRequestPydantic
from app.backtest.engine import BacktestParams, RebalanceFrequency, run_backtest
from app.backtest.persistence import save_backtest_run
from app.db.session import get_db
from app.models.backtest_run import BacktestRun
from app.models.daily_price import DailyPrice

router = APIRouter(prefix="/backtest", tags=["backtest"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_run(run: BacktestRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "name": run.name,
        "etf_pool": list(run.etf_pool),
        "momentum_window": run.momentum_window,
        "rebalance_freq": run.rebalance_freq,
        "start_date": run.start_date.isoformat(),
        "end_date": run.end_date.isoformat(),
        "metrics": run.metrics,
        "created_at": run.created_at.isoformat() if run.created_at else "",
    }


def _load_price_history(
    db: Session,
    etf_pool: list[str],
    start: _date,
    end: _date,
    lookback: int,
    skip: int,
) -> dict[str, list[tuple[_date, Decimal]]]:
    """从 DB 加载 [start - lookback*1.5 - skip, end] 区间的日线。

    Returns:
        {code: [(date, close), ...]}，按 date 升序。
        缺失的 code 不在 dict 里，调用方负责检查并报错。
    """
    earliest = start - timedelta(days=int(lookback * 1.5) + skip + 10)
    history: dict[str, list[tuple[_date, Decimal]]] = {}
    for code in etf_pool:
        rows = (
            db.execute(
                select(DailyPrice.date, DailyPrice.close)
                .where(
                    DailyPrice.code == code,
                    DailyPrice.date >= earliest,
                    DailyPrice.date <= end,
                )
                .order_by(DailyPrice.date.asc())
            )
            .all()
        )
        if not rows:
            continue
        history[code] = [(r.date, r.close) for r in rows]
    return history


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
def create_backtest(
    req: BacktestRequestPydantic,
    db: Session = Depends(get_db),
) -> dict:
    """提交新回测：同步执行 run_backtest + save_backtest_run。

    Pydantic 自动 422 校验失败。
    """
    if req.start > req.end:
        raise HTTPException(
            status_code=422,
            detail=f"start ({req.start}) must be <= end ({req.end})",
        )

    params = BacktestParams(
        etf_pool=list(req.etf_pool),
        start=req.start,
        end=req.end,
        initial_cash=req.initial_cash,
        lookback=req.lookback,
        skip=req.skip,
        top_n=req.top_n,
        rebalance_freq=RebalanceFrequency(req.rebalance_freq),
    )

    # Load price history
    history = _load_price_history(
        db, list(req.etf_pool), req.start, req.end, req.lookback, req.skip
    )

    # Detect missing codes
    missing = [c for c in req.etf_pool if c not in history]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"insufficient price history for: {missing}. "
                f"POST /api/v1/sync/prices first."
            ),
        )

    # Run + save
    try:
        result = run_backtest(params, history)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    run = save_backtest_run(db, params, result)
    return _serialize_run(run)


@router.get("")
def list_backtests(
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """BacktestRun 列表，按 created_at desc。"""
    limit = _clamp_limit(limit) if limit is not None else 20
    offset = _clamp_offset(offset)

    total = db.execute(select(func.count()).select_from(BacktestRun)).scalar_one()
    rows = (
        db.execute(
            select(BacktestRun)
            .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return {
        "items": [_serialize_run(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{run_id}")
def get_backtest_detail(run_id: int, db: Session = Depends(get_db)) -> dict:
    """单条 BacktestRun 详情（含 metrics）。"""
    run = db.execute(
        select(BacktestRun).where(BacktestRun.id == run_id)
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail=f"BacktestRun {run_id} not found")
    return _serialize_run(run)


@router.get("/{run_id}/nav")
def get_backtest_nav(run_id: int, db: Session = Depends(get_db)) -> dict:
    """NAV 序列（前端画图用）。"""
    run = db.execute(
        select(BacktestRun).where(BacktestRun.id == run_id)
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail=f"BacktestRun {run_id} not found")
    nav_series = run.nav_series if run.nav_series else []
    return {"id": run_id, "nav_series": nav_series}
