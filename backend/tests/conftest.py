"""Pytest configuration: isolated SQLite DB per test."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from app import db


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Use a fresh SQLite file per test, and reset the cached engine."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        monkeypatch.setenv("ETF_DB_PATH", str(db_path))
        db.reset_engine_for_tests()
        yield
        db.reset_engine_for_tests()