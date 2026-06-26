"""ETF 业务端点（v1）。"""

from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.daily_price import DailyPrice
from app.models.etf import ETF

router = APIRouter(prefix="/etfs", tags=["etfs"])


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------


def _clamp_limit(limit: int | None) -> int:
    """limit clamp 到 [1, 500]，默认 50。"""
    if limit is None:
        return 50
    if limit < 1:
        return 1
    if limit > 500:
        return 500
    return limit


def _clamp_offset(offset: int | None) -> int:
    if offset is None:
        return 0
    return max(0, offset)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/count")
def count_etfs(db: Session = Depends(get_db)) -> dict:
    """返回 ETF 总数（冒烟测试端点，验证 Depends 注入）。"""
    total = db.execute(select(func.count()).select_from(ETF)).scalar_one()
    return {"count": total}


@router.get("")
def list_etfs(
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    """ETF 列表，支持 category 过滤。"""
    limit = _clamp_limit(limit)
    offset = _clamp_offset(offset)

    stmt = select(ETF)
    count_stmt = select(func.count()).select_from(ETF)
    if category:
        stmt = stmt.where(ETF.category == category)
        count_stmt = count_stmt.where(ETF.category == category)

    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(
        stmt.order_by(ETF.code).limit(limit).offset(offset)
    ).scalars().all()

    return {
        "items": [
            {
                "code": r.code,
                "name": r.name,
                "market": r.market,
                "category": r.category,
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{code}")
def get_etf(code: str, db: Session = Depends(get_db)) -> dict:
    """ETF 详情。"""
    etf = db.execute(select(ETF).where(ETF.code == code)).scalar_one_or_none()
    if etf is None:
        raise HTTPException(status_code=404, detail=f"ETF {code} not found")
    return {
        "code": etf.code,
        "name": etf.name,
        "market": etf.market,
        "category": etf.category,
    }


@router.get("/{code}/prices")
def get_etf_prices(
    code: str,
    start: _date | None = Query(default=None),
    end: _date | None = Query(default=None),
    limit: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    """ETF 日线历史，按 date 升序。"""
    # 404 if ETF 不存在
    etf = db.execute(select(ETF.code).where(ETF.code == code)).scalar_one_or_none()
    if etf is None:
        raise HTTPException(status_code=404, detail=f"ETF {code} not found")

    effective_limit = _clamp_limit(limit) if limit is not None else 500

    stmt = select(DailyPrice).where(DailyPrice.code == code)
    if start:
        stmt = stmt.where(DailyPrice.date >= start)
    if end:
        stmt = stmt.where(DailyPrice.date <= end)

    # 取最后 N 条（按 date desc），然后反转得到升序
    rows = (
        db.execute(stmt.order_by(DailyPrice.date.desc()).limit(effective_limit))
        .scalars()
        .all()
    )
    rows = list(reversed(rows))

    return [
        {
            "code": r.code,
            "date": r.date.isoformat(),
            "open": str(r.open),
            "high": str(r.high),
            "low": str(r.low),
            "close": str(r.close),
            "volume": r.volume,
        }
        for r in rows
    ]
