"""Signal 业务端点（v1）：list-by-date 与 latest。"""

from datetime import date as _date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.signal_snapshot import SignalSnapshot

router = APIRouter(prefix="/signals", tags=["signals"])


def _serialize_row(r: SignalSnapshot) -> dict[str, Any]:
    return {
        "etf_code": r.etf_code,
        "momentum_score": None if r.momentum_score is None else str(r.momentum_score),
        "rank": r.rank,
        "action": r.action,
    }


def _query_snapshot(db: Session, snapshot_date: _date) -> list[SignalSnapshot]:
    rows = (
        db.execute(
            select(SignalSnapshot)
            .where(SignalSnapshot.date == snapshot_date)
            .order_by(
                SignalSnapshot.rank.is_(None),
                SignalSnapshot.rank.asc(),
                SignalSnapshot.etf_code.asc(),
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.get("/latest")
def get_latest_signals(db: Session = Depends(get_db)) -> dict[str, Any]:
    """显式 latest：DB MAX(date)。"""
    latest_date = db.execute(select(func.max(SignalSnapshot.date))).scalar_one()
    if latest_date is None:
        return {"date": None, "rows": []}
    rows = _query_snapshot(db, latest_date)
    return {"date": latest_date.isoformat(), "rows": [_serialize_row(r) for r in rows]}


@router.get("")
def list_signals(
    date: _date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """GET /signals?date=YYYY-MM-DD。不传 date → DB MAX(date)。"""
    if date is None:
        return get_latest_signals(db=db)

    rows = _query_snapshot(db, date)
    return {
        "date": date.isoformat(),
        "rows": [_serialize_row(r) for r in rows],
    }
