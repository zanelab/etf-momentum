"""SignalSnapshot model CRUD 测试。"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.signal_snapshot import SignalSnapshot


def test_insert_signal(db_session):
    s = SignalSnapshot(
        date=date(2026, 1, 15),
        etf_code="510300",
        momentum_score=Decimal("0.123456"),
        rank=1,
        action="buy",
    )
    db_session.add(s)
    db_session.commit()

    assert s.id is not None


def test_unique_constraint_on_date_and_etf_code(db_session):
    s1 = SignalSnapshot(
        date=date(2026, 1, 15),
        etf_code="510300",
        momentum_score=Decimal("0.1"),
        rank=1,
        action="buy",
    )
    db_session.add(s1)
    db_session.commit()

    s2 = SignalSnapshot(
        date=date(2026, 1, 15),
        etf_code="510300",
        momentum_score=Decimal("0.2"),
        rank=2,
        action="sell",
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_query_signals_by_date_ordered_by_rank(db_session):
    db_session.add_all([
        SignalSnapshot(date=date(2026, 1, 15), etf_code="510500",
                       momentum_score=Decimal("0.3"), rank=3, action="hold"),
        SignalSnapshot(date=date(2026, 1, 15), etf_code="510300",
                       momentum_score=Decimal("0.5"), rank=1, action="buy"),
        SignalSnapshot(date=date(2026, 1, 15), etf_code="159915",
                       momentum_score=Decimal("0.4"), rank=2, action="buy"),
    ])
    db_session.commit()

    result = db_session.execute(
        select(SignalSnapshot)
        .where(SignalSnapshot.date == date(2026, 1, 15))
        .order_by(SignalSnapshot.rank)
    ).scalars().all()
    assert [s.etf_code for s in result] == ["510300", "159915", "510500"]
