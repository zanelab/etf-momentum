"""Tests for app.signals.persistence — save_signal_snapshot."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.signal_snapshot import SignalSnapshot
from app.signals.compute import SignalRow
from app.signals.persistence import save_signal_snapshot


SIGNAL_DATE = date(2024, 12, 31)


def _row(code: str, score: Decimal | None, rank: int | None, action: str) -> SignalRow:
    return SignalRow(
        etf_code=code,
        momentum_score=score,
        rank=rank,
        action=action,
    )


# ---------------------------------------------------------------------------
# 插入
# ---------------------------------------------------------------------------


def test_inserts_new_rows(db_session) -> None:
    rows = [
        _row("510300", Decimal("0.123456"), 1, "BUY"),
        _row("510500", Decimal("0.100000"), 2, "HOLD"),
    ]
    written = save_signal_snapshot(db_session, SIGNAL_DATE, rows)
    db_session.expire_all()

    assert len(written) == 2
    assert db_session.query(SignalSnapshot).count() == 2


def test_inserts_watch_with_none_score(db_session) -> None:
    rows = [_row("510300", None, None, "WATCH")]
    written = save_signal_snapshot(db_session, SIGNAL_DATE, rows)
    db_session.expire_all()

    assert len(written) == 1
    snap = db_session.execute(select(SignalSnapshot)).scalar_one()
    assert snap.momentum_score is None
    assert snap.rank is None
    assert snap.action == "WATCH"


# ---------------------------------------------------------------------------
# 跳过 vs 覆盖
# ---------------------------------------------------------------------------


def test_skip_existing_default(db_session) -> None:
    """overwrite=False 时同 (date, etf_code) 跳过。"""
    existing = SignalSnapshot(
        date=SIGNAL_DATE,
        etf_code="510300",
        momentum_score=Decimal("0.500000"),
        rank=99,
        action="HOLD",
    )
    db_session.add(existing)
    db_session.commit()

    rows = [_row("510300", Decimal("0.123456"), 1, "BUY")]
    written = save_signal_snapshot(db_session, SIGNAL_DATE, rows)
    db_session.expire_all()

    assert written == []  # 没写入
    snap = db_session.execute(select(SignalSnapshot)).scalar_one()
    # 原值保留
    assert snap.momentum_score == Decimal("0.500000")
    assert snap.rank == 99
    assert snap.action == "HOLD"


def test_overwrite_existing(db_session) -> None:
    """overwrite=True 时同 (date, etf_code) 更新。"""
    existing = SignalSnapshot(
        date=SIGNAL_DATE,
        etf_code="510300",
        momentum_score=Decimal("0.500000"),
        rank=99,
        action="HOLD",
    )
    db_session.add(existing)
    db_session.commit()

    rows = [_row("510300", Decimal("0.123456"), 1, "BUY")]
    written = save_signal_snapshot(
        db_session, SIGNAL_DATE, rows, overwrite=True
    )
    db_session.expire_all()

    assert len(written) == 1
    snap = db_session.execute(select(SignalSnapshot)).scalar_one()
    assert snap.momentum_score == Decimal("0.123456")
    assert snap.rank == 1
    assert snap.action == "BUY"


def test_overwrite_partial(db_session) -> None:
    """overwrite=True 时只覆盖已存在的；新 ETF 仍然插入。"""
    db_session.add(SignalSnapshot(
        date=SIGNAL_DATE, etf_code="510300",
        momentum_score=Decimal("0.999"), rank=1, action="BUY",
    ))
    db_session.commit()

    rows = [
        _row("510300", Decimal("0.123456"), 5, "HOLD"),  # 已存在 → 更新
        _row("510500", Decimal("0.100000"), 6, "WATCH"),  # 新增
    ]
    written = save_signal_snapshot(
        db_session, SIGNAL_DATE, rows, overwrite=True
    )
    db_session.expire_all()

    assert len(written) == 2
    snaps = db_session.execute(
        select(SignalSnapshot).order_by(SignalSnapshot.etf_code)
    ).scalars().all()
    assert len(snaps) == 2
    by_code = {s.etf_code: s for s in snaps}
    assert by_code["510300"].rank == 5
    assert by_code["510500"].rank == 6


# ---------------------------------------------------------------------------
# 边界
# ---------------------------------------------------------------------------


def test_empty_rows_no_commit_change(db_session) -> None:
    """rows=[] 时 commit 仍调用但不写入。"""
    written = save_signal_snapshot(db_session, SIGNAL_DATE, [])
    assert written == []
    assert db_session.query(SignalSnapshot).count() == 0


# ---------------------------------------------------------------------------
# 精度
# ---------------------------------------------------------------------------


def test_score_quantize_6dp(db_session) -> None:
    """score quantize 到 6 位（与 Numeric(10,6) 对齐）。"""
    rows = [_row("510300", Decimal("0.123456789"), 1, "BUY")]
    save_signal_snapshot(db_session, SIGNAL_DATE, rows)
    db_session.expire_all()

    snap = db_session.execute(select(SignalSnapshot)).scalar_one()
    # 0.123456789 → 0.123457
    assert snap.momentum_score == Decimal("0.123457")
