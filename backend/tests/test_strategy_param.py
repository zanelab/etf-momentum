"""Tests for StrategyParam model."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import select

from app.db import get_engine, init_db, session_scope
from app.models.strategy_param import StrategyParam


def test_strategy_param_json_value() -> None:
    init_db()
    engine = get_engine()
    with session_scope(engine) as session:
        param = StrategyParam(key="momentum_days", value_json="25")
        session.add(param)
        session.flush()

    with session_scope(engine) as session:
        fetched = session.exec(select(StrategyParam).where(StrategyParam.key == "momentum_days")).first()
        assert fetched is not None
        assert fetched.value_json == "25"
        assert isinstance(fetched.updated_at, datetime)