"""CSV-backed fixture market data source."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from app.data_sources.base import DataNotFoundError, FieldName, MarketDataSource

ALL_FIELDS: list[FieldName] = ["open", "high", "low", "close", "volume", "money"]


class FixtureCSVSource(MarketDataSource):
    """Reads daily OHLCV from `fixtures_dir/<code>.csv`."""

    REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume", "money"]

    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = Path(fixtures_dir)

    def _path_for(self, code: str) -> Path:
        return self.fixtures_dir / f"{code}.csv"

    def _load(self, code: str) -> pd.DataFrame:
        path = self._path_for(code)
        if not path.exists():
            raise DataNotFoundError(f"No fixture for {code} (looked at {path})")
        df = pd.read_csv(path, parse_dates=["date"])
        missing = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Fixture {path} missing columns: {missing}")
        df = df.set_index("date").sort_index()
        return df

    def history(
        self,
        code: str,
        start: date,
        end: date,
        fields: list[FieldName] | None = None,
    ) -> pd.DataFrame:
        df = self._load(code)
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        mask = (df.index >= start_ts) & (df.index <= end_ts)
        df = df.loc[mask]
        if fields is not None:
            cols = [f for f in fields if f in df.columns]
            df = df[cols]
        return df

    def snapshot(self, code: str, as_of: datetime) -> dict[str, float]:
        df = self._load(code)
        as_of_ts = pd.Timestamp(as_of.date())
        valid = df.loc[df.index <= as_of_ts]
        if valid.empty:
            raise DataNotFoundError(f"No snapshot data for {code} at or before {as_of}")
        row = valid.iloc[-1]
        return {
            "last_price": float(row["close"]),
            "volume": float(row["volume"]),
            "money": float(row["money"]),
        }

    def all_etfs(self, as_of: date) -> list[str]:
        return sorted(
            p.stem
            for p in self.fixtures_dir.glob("*.csv")
            if p.is_file()
        )
