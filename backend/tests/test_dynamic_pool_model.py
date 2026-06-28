"""Tests for DynamicPoolEntry model."""
from datetime import datetime

from sqlmodel import select

from app.db import get_engine, init_db, session_scope
from app.models.dynamic_pool import DynamicPoolEntry


def test_dynamic_pool_roundtrip() -> None:
    init_db()
    engine = get_engine()
    entry = DynamicPoolEntry(
        code="510300.XSHG",
        name="沪深300ETF",
        is_enabled=True,
        last_synced_at=datetime(2026, 6, 28, 14, 0),
    )
    with session_scope(engine) as session:
        session.add(entry)
        session.flush()

    with session_scope(engine) as session:
        fetched = session.exec(
            select(DynamicPoolEntry).where(DynamicPoolEntry.code == "510300.XSHG")
        ).first()
        assert fetched is not None
        assert fetched.name == "沪深300ETF"
        assert fetched.is_enabled is True
        assert isinstance(fetched.last_synced_at, datetime)


def test_dynamic_pool_default_is_enabled_false() -> None:
    """New entries default to is_enabled=False (user must explicitly opt in)."""
    init_db()
    engine = get_engine()
    entry = DynamicPoolEntry(
        code="510500.XSHG",
        name="中证500ETF",
        last_synced_at=datetime(2026, 6, 28, 14, 0),
    )
    with session_scope(engine) as session:
        session.add(entry)
        session.flush()
    with session_scope(engine) as session:
        fetched = session.exec(
            select(DynamicPoolEntry).where(DynamicPoolEntry.code == "510500.XSHG")
        ).first()
        assert fetched is not None
        assert fetched.is_enabled is False
