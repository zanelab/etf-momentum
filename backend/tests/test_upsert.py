"""upsert 工具函数单测。"""

from datetime import date
from decimal import Decimal

import pytest

from app.data.client import DailyPriceRow, EtfMasterRow
from app.data.upsert import upsert_daily_price, upsert_etf
from app.models.daily_price import DailyPrice
from app.models.etf import ETF


def test_upsert_etf_inserts_new_row(db_session):
    upsert_etf(
        db_session,
        EtfMasterRow(code="510300", name="沪深300ETF", market="SH", category="指数"),
    )
    db_session.commit()

    rows = db_session.query(ETF).all()
    assert len(rows) == 1
    assert rows[0].code == "510300"
    assert rows[0].name == "沪深300ETF"


def test_upsert_etf_updates_existing(db_session):
    upsert_etf(db_session, EtfMasterRow(code="510300", name="旧名", market="SH"))
    db_session.commit()

    upsert_etf(db_session, EtfMasterRow(code="510300", name="新名", market="SH"))
    db_session.commit()

    rows = db_session.query(ETF).all()
    assert len(rows) == 1
    assert rows[0].name == "新名"


def test_upsert_daily_price_inserts_new_row(db_session):
    upsert_daily_price(
        db_session,
        "510300",
        DailyPriceRow(date=date(2024, 1, 1), open=Decimal("4.0"),
                      high=Decimal("4.1"), low=Decimal("3.9"),
                      close=Decimal("4.05"), volume=1000),
    )
    db_session.commit()

    rows = db_session.query(DailyPrice).all()
    assert len(rows) == 1
    assert rows[0].code == "510300"
    assert rows[0].close == Decimal("4.05")


def test_upsert_daily_price_updates_existing(db_session):
    upsert_daily_price(
        db_session,
        "510300",
        DailyPriceRow(date=date(2024, 1, 1), open=Decimal("4.0"),
                      high=Decimal("4.0"), low=Decimal("4.0"),
                      close=Decimal("4.0"), volume=1),
    )
    db_session.commit()

    upsert_daily_price(
        db_session,
        "510300",
        DailyPriceRow(date=date(2024, 1, 1), open=Decimal("5.0"),
                      high=Decimal("5.0"), low=Decimal("5.0"),
                      close=Decimal("5.0"), volume=99),
    )
    db_session.commit()

    rows = db_session.query(DailyPrice).all()
    assert len(rows) == 1
    assert rows[0].close == Decimal("5.0")
    assert rows[0].volume == 99
