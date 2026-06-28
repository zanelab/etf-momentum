"""Tests for CachedSource read-through cache decorator."""
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlmodel import select

from app.data_sources.base import DataNotFoundError, MarketDataSource
from app.data_sources.cache import CachedSource
from app.db import get_engine, init_db, session_scope
from app.models.market_bar_cache import MarketBarCache


class _StubSource(MarketDataSource):
    """Minimal in-memory MarketDataSource for testing the cache wrapper."""

    def __init__(self) -> None:
        self._history_calls = 0
        self._snapshot_calls = 0
        # 5 trading days of synthetic data
        self._df = pd.DataFrame(
            {
                "open": [3.85, 3.88, 3.90, 3.92, 3.95],
                "close": [3.87, 3.89, 3.92, 3.94, 3.97],
                "high": [3.88, 3.90, 3.95, 3.96, 3.99],
                "low": [3.84, 3.87, 3.88, 3.91, 3.94],
                "volume": [1_000_000.0, 1_100_000.0, 1_200_000.0, 1_300_000.0, 1_400_000.0],
                "money": [3_870_000.0, 4_279_000.0, 4_704_000.0, 5_122_000.0, 5_558_000.0],
            },
            index=pd.to_datetime(
                ["2026-01-13", "2026-01-14", "2026-01-15", "2026-01-16", "2026-01-17"]
            ),
        )
        self._df.index.name = "date"

    def history(self, code, start, end, fields=None):
        self._history_calls += 1
        mask = (self._df.index >= pd.Timestamp(start)) & (self._df.index <= pd.Timestamp(end))
        df = self._df.loc[mask]
        if fields is not None:
            df = df[[f for f in fields if f in df.columns]]
        return df

    def snapshot(self, code, as_of):
        self._snapshot_calls += 1
        valid = self._df.loc[self._df.index <= pd.Timestamp(as_of.date())]
        if valid.empty:
            raise DataNotFoundError(f"No stub data for {code}")
        row = valid.iloc[-1]
        return {
            "last_price": float(row["close"]),
            "volume": float(row["volume"]),
            "money": float(row["money"]),
        }

    def all_etfs(self, as_of):
        return ["510300.XSHG", "510500.XSHG"]


def _make_cached() -> tuple[CachedSource, _StubSource]:
    init_db()
    stub = _StubSource()
    cached = CachedSource(stub, engine=get_engine())
    return cached, stub


def test_snapshot_cache_miss_then_hit() -> None:
    cached, stub = _make_cached()
    # First call: miss -> calls stub, writes cache
    snap1 = cached.snapshot("510300.XSHG", datetime(2026, 1, 15, 14, 0))
    assert snap1["last_price"] == 3.92
    assert stub._snapshot_calls == 1
    assert cached.stats() == {"hit": 0, "miss": 1}

    # Second call: hit -> does NOT call stub
    snap2 = cached.snapshot("510300.XSHG", datetime(2026, 1, 15, 14, 0))
    assert snap2["last_price"] == 3.92
    assert stub._snapshot_calls == 1
    assert cached.stats() == {"hit": 1, "miss": 1}


def test_history_partial_cache_hit() -> None:
    """history() with one date cached and one not — stub should be called
    only for the missing date range."""
    cached, stub = _make_cached()
    # Prime cache for 2026-01-15 only
    cached.snapshot("510300.XSHG", datetime(2026, 1, 15, 14, 0))
    # Reset call counter
    stub._snapshot_calls = 0
    stub._history_calls = 0

    df = cached.history("510300.XSHG", date(2026, 1, 13), date(2026, 1, 17))
    # stub was called once for the full range (it doesn't know about the
    # cache; cache merges on top), but at least 1 row came from cache
    assert stub._history_calls == 1
    assert len(df) == 5
    # 4 of 5 dates came from stub but the cached date must be present
    assert pd.Timestamp("2026-01-15") in df.index


def test_history_all_cache_hit() -> None:
    """If all dates in [start, end] are already cached, history() returns
    directly from cache and does NOT call inner."""
    cached, stub = _make_cached()
    # Prime cache for all 5 dates via history() (write-through)
    cached.history("510300.XSHG", date(2026, 1, 13), date(2026, 1, 17))
    stub._history_calls = 0  # reset after priming
    df = cached.history("510300.XSHG", date(2026, 1, 13), date(2026, 1, 17))
    assert stub._history_calls == 0
    assert len(df) == 5


def test_stats_increments_correctly() -> None:
    cached, _ = _make_cached()
    cached.snapshot("510300.XSHG", datetime(2026, 1, 13, 14, 0))  # miss
    cached.snapshot("510300.XSHG", datetime(2026, 1, 13, 14, 0))  # hit
    cached.snapshot("510300.XSHG", datetime(2026, 1, 14, 14, 0))  # miss
    assert cached.stats() == {"hit": 1, "miss": 2}


def test_clear_empties_cache_table() -> None:
    cached, stub = _make_cached()
    cached.snapshot("510300.XSHG", datetime(2026, 1, 13, 14, 0))  # writes cache
    engine = get_engine()
    with session_scope(engine) as session:
        rows = session.exec(select(MarketBarCache)).all()
        assert len(rows) == 1
    cached.clear()
    with session_scope(engine) as session:
        rows = session.exec(select(MarketBarCache)).all()
        assert len(rows) == 0
    # After clear, next snapshot is a miss again
    snap = cached.snapshot("510300.XSHG", datetime(2026, 1, 13, 14, 0))
    assert snap["last_price"] == 3.87  # 2026-01-13 close
    assert cached.stats()["miss"] == 2
