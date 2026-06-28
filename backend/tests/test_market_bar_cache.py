"""Tests for MarketBarCache model (per-(code, date) cache row)."""
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.db import get_engine, init_db, session_scope
from app.models.market_bar_cache import MarketBarCache


def test_market_bar_cache_roundtrip() -> None:
    init_db()
    engine = get_engine()
    bar = MarketBarCache(
        code="510300.XSHG",
        trade_date=date(2026, 1, 15),
        open=3.90,
        high=3.95,
        low=3.88,
        close=3.92,
        volume=1_000_000.0,
        money=3_920_000.0,
        cached_at=datetime(2026, 1, 15, 14, 0),
        source="akshare",
    )
    with session_scope(engine) as session:
        session.add(bar)
        session.flush()

    with session_scope(engine) as session:
        fetched = session.exec(
            select(MarketBarCache).where(
                MarketBarCache.code == "510300.XSHG",
                MarketBarCache.trade_date == date(2026, 1, 15),
            )
        ).first()
        assert fetched is not None
        assert fetched.open == 3.90
        assert fetched.close == 3.92
        assert fetched.source == "akshare"


def test_market_bar_cache_money_optional() -> None:
    """money field is optional (akshare sometimes returns None)."""
    init_db()
    engine = get_engine()
    bar = MarketBarCache(
        code="510300.XSHG",
        trade_date=date(2026, 1, 16),
        open=3.90,
        high=3.95,
        low=3.88,
        close=3.92,
        volume=1_000_000.0,
        money=None,
        cached_at=datetime(2026, 1, 16, 14, 0),
    )
    with session_scope(engine) as session:
        session.add(bar)
        session.flush()
    with session_scope(engine) as session:
        fetched = session.exec(
            select(MarketBarCache).where(
                MarketBarCache.code == "510300.XSHG",
                MarketBarCache.trade_date == date(2026, 1, 16),
            )
        ).first()
        assert fetched is not None
        assert fetched.money is None


def test_market_bar_cache_compound_key_uniqueness() -> None:
    """(code, trade_date) is a composite primary key — duplicate insert must raise."""
    init_db()
    engine = get_engine()
    bar1 = MarketBarCache(
        code="510300.XSHG",
        trade_date=date(2026, 1, 15),
        open=3.90,
        high=3.95,
        low=3.88,
        close=3.92,
        volume=1_000_000.0,
        money=3_920_000.0,
        cached_at=datetime(2026, 1, 15, 14, 0),
    )
    bar2 = MarketBarCache(
        code="510300.XSHG",
        trade_date=date(2026, 1, 15),  # same (code, trade_date)
        open=3.91,
        high=3.96,
        low=3.89,
        close=3.93,
        volume=1_100_000.0,
        money=4_000_000.0,
        cached_at=datetime(2026, 1, 15, 14, 5),
    )
    with session_scope(engine) as session:
        session.add(bar1)
        session.flush()
    try:
        with session_scope(engine) as session:
            session.add(bar2)
            session.flush()
        raised = False
    except IntegrityError:
        raised = True
    assert raised, "Expected IntegrityError on duplicate (code, trade_date)"
