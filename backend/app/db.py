"""Database engine, session, and initialization helpers."""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "etf_momentum.db"

_engine = None


def get_db_path() -> Path:
    env = os.environ.get("ETF_DB_PATH")
    return Path(env) if env else DEFAULT_DB_PATH


def get_engine():
    """Return a process-wide SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        connect_args = {"check_same_thread": False}
        _engine = create_engine(url, echo=False, connect_args=connect_args)
    return _engine


def reset_engine_for_tests() -> None:
    """Reset the cached engine (used by tests with isolated DB paths)."""
    global _engine
    _engine = None


def init_db() -> None:
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(get_engine())


def session_scope(engine=None) -> Iterator[Session]:
    """Context manager yielding a SQLModel Session with auto commit/rollback."""
    return _session_scope_impl(engine)


@contextmanager
def _session_scope_impl(engine=None):
    eng = engine or get_engine()
    session = Session(eng)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()