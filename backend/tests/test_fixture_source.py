"""Tests for FixtureCSVSource."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from app.data_sources.base import DataNotFoundError
from app.data_sources.fixture import FixtureCSVSource


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    """Write a tiny 5-row fixture for a single ETF."""
    code = "TEST.XSHG"
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=5, freq="B").strftime("%Y-%m-%d"),
            "open": [10.0, 10.1, 10.2, 10.3, 10.4],
            "high": [10.2, 10.3, 10.4, 10.5, 10.6],
            "low": [9.9, 10.0, 10.1, 10.2, 10.3],
            "close": [10.1, 10.2, 10.3, 10.4, 10.5],
            "volume": [1000, 1100, 1200, 1300, 1400],
            "money": [10100.0, 11220.0, 12360.0, 13520.0, 14700.0],
        }
    )
    df.to_csv(tmp_path / f"{code}.csv", index=False)
    return tmp_path


def test_history_returns_dataframe_indexed_by_date(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    df = src.history("TEST.XSHG", date(2024, 1, 1), date(2024, 1, 31))
    assert len(df) == 5
    assert isinstance(df.index, pd.DatetimeIndex)
    assert list(df.columns) == ["open", "high", "low", "close", "volume", "money"]


def test_history_filters_fields(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    df = src.history("TEST.XSHG", date(2024, 1, 1), date(2024, 1, 31), fields=["close", "volume"])
    assert list(df.columns) == ["close", "volume"]


def test_history_filters_date_range(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    df = src.history("TEST.XSHG", date(2024, 1, 3), date(2024, 1, 4))
    assert len(df) == 2
    assert df.iloc[0]["close"] == pytest.approx(10.3)


def test_history_missing_code_raises(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    with pytest.raises(DataNotFoundError):
        src.history("NOPE.XSHG", date(2024, 1, 1), date(2024, 1, 31))


def test_snapshot_returns_latest_before_as_of(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    snap = src.snapshot("TEST.XSHG", datetime(2024, 1, 3, 10, 0))
    assert snap["last_price"] == pytest.approx(10.3)


def test_snapshot_missing_code_raises(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    with pytest.raises(DataNotFoundError):
        src.snapshot("NOPE.XSHG", datetime(2024, 1, 1))


def test_all_etfs_lists_csv_files(fixtures_dir: Path) -> None:
    src = FixtureCSVSource(fixtures_dir)
    etfs = src.all_etfs(date(2024, 1, 1))
    assert etfs == ["TEST.XSHG"]
