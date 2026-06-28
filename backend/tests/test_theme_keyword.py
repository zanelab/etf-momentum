"""Tests for ThemeKeyword model."""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.db import get_engine, init_db, session_scope
from app.models.theme_keyword import ThemeKeyword


def test_theme_keyword_roundtrip() -> None:
    init_db()
    engine = get_engine()
    with session_scope(engine) as session:
        session.add(ThemeKeyword(theme="半导体", keyword="芯片"))
        session.flush()

    with session_scope(engine) as session:
        fetched = session.exec(select(ThemeKeyword).where(ThemeKeyword.theme == "半导体")).first()
        assert fetched is not None
        assert fetched.keyword == "芯片"


def test_theme_keyword_unique_pair() -> None:
    init_db()
    engine = get_engine()
    with session_scope(engine) as session:
        session.add(ThemeKeyword(theme="半导体", keyword="芯片"))
        session.flush()

    with session_scope(engine) as session:
        session.add(ThemeKeyword(theme="半导体", keyword="芯片"))
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return
    raise AssertionError("Expected IntegrityError on duplicate (theme, keyword)")
