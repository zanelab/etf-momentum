"""Tests for StaticPool model."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import select

from app.db import get_engine, init_db, session_scope
from app.models.static_pool import StaticPool


def test_static_pool_roundtrip() -> None:
    init_db()
    engine = get_engine()
    with session_scope(engine) as session:
        entry = StaticPool(code="510300.XSHG", display_name="沪深300ETF", enabled=True)
        session.add(entry)
        session.flush()
        code = entry.code

    with session_scope(engine) as session:
        fetched = session.exec(select(StaticPool).where(StaticPool.code == code)).first()
        assert fetched is not None
        assert fetched.display_name == "沪深300ETF"
        assert fetched.enabled is True
        assert isinstance(fetched.created_at, datetime)
        assert isinstance(fetched.updated_at, datetime)


def test_static_pool_defaults() -> None:
    init_db()
    engine = get_engine()
    with session_scope(engine) as session:
        entry = StaticPool(code="510500.XSHG")
        session.add(entry)
        session.flush()

    with session_scope(engine) as session:
        fetched = session.exec(select(StaticPool).where(StaticPool.code == "510500.XSHG")).first()
        assert fetched is not None
        assert fetched.display_name is None
        assert fetched.enabled is True
