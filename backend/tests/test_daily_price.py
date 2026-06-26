"""DailyPrice model CRUD 测试。"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.daily_price import DailyPrice


def test_insert_single_daily_price(db_session):
    p = DailyPrice(
        code="510300",
        date=date(2026, 1, 15),
        open=Decimal("4.123"),
        high=Decimal("4.156"),
        low=Decimal("4.100"),
        close=Decimal("4.135"),
        volume=12_345_678,
    )
    db_session.add(p)
    db_session.commit()

    assert p.id is not None


def test_unique_constraint_on_code_and_date(db_session):
    p1 = DailyPrice(
        code="510300",
        date=date(2026, 1, 15),
        open=Decimal("4.000"),
        high=Decimal("4.000"),
        low=Decimal("4.000"),
        close=Decimal("4.000"),
        volume=1,
    )
    db_session.add(p1)
    db_session.commit()

    p2 = DailyPrice(
        code="510300",
        date=date(2026, 1, 15),
        open=Decimal("5.000"),
        high=Decimal("5.000"),
        low=Decimal("5.000"),
        close=Decimal("5.000"),
        volume=1,
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_query_history_ordered_by_date_asc(db_session):
    rows = [
        DailyPrice(
            code="510300",
            date=date(2026, 1, d),
            open=Decimal("4.0"),
            high=Decimal("4.0"),
            low=Decimal("4.0"),
            close=Decimal("4.0"),
            volume=1,
        )
        for d in (10, 15, 12, 17)
    ]
    db_session.add_all(rows)
    db_session.commit()

    result = db_session.execute(
        select(DailyPrice)
        .where(DailyPrice.code == "510300")
        .order_by(DailyPrice.date)
    ).scalars().all()
    assert [r.date.day for r in result] == [10, 12, 15, 17]
