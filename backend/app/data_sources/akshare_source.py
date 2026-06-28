"""AkShare-backed market data source for A-share ETFs.

Wraps the `akshare` library. Lazy-imports the package on first call so the
rest of the app can be loaded even when akshare is not installed.
"""
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from app.data_sources.base import DataNotFoundError, FieldName, MarketDataSource
from app.data_sources.fixture import FixtureCSVSource
from app.data_sources.retry import retry_with_backoff

# akshare's `fund_etf_hist_em` returns these Chinese column names; we rename
# to our canonical English column names.
_HIST_COL_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "money",
}

_NAME_COL_CODE = "基金代码"
_NAME_COL_NAME = "基金名称"


def _import_akshare():
    try:
        import akshare  # type: ignore
    except ImportError as e:
        raise ImportError(
            "akshare is not installed. Run `pip install -r backend/requirements-realtime.txt`."
        ) from e
    return akshare


class AkShareSource(MarketDataSource):
    """Fetches A-share ETF OHLCV via akshare.

    If `fixtures_dir` is provided, all akshare calls fall back to
    FixtureCSVSource after retries are exhausted.
    """

    def __init__(
        self,
        fixtures_dir: Optional[Path] = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ) -> None:
        # Validate import eagerly so callers fail fast
        _import_akshare()
        self._fallback = FixtureCSVSource(fixtures_dir) if fixtures_dir else None
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._initial_delay = initial_delay

    def _call(self, fn) -> "object":
        return retry_with_backoff(
            fn,
            max_retries=self._max_retries,
            backoff_factor=self._backoff_factor,
            initial_delay=self._initial_delay,
        )

    def _fetch_history_raw(self, code: str, start: date_cls, end: date_cls) -> pd.DataFrame:
        akshare = _import_akshare()
        # akshare expects "%Y%m%d" string format for start/end
        start_s = start.strftime("%Y%m%d")
        end_s = end.strftime("%Y%m%d")
        df = akshare.fund_etf_hist_em(
            symbol=code, period="daily", start_date=start_s, end_date=end_s, adjust=""
        )
        if df is None or df.empty:
            return pd.DataFrame()
        return df.rename(columns=_HIST_COL_MAP)

    def history(
        self,
        code: str,
        start: date_cls,
        end: date_cls,
        fields: Optional[list[FieldName]] = None,
    ) -> pd.DataFrame:
        try:
            df = self._call(lambda: self._fetch_history_raw(code, start, end))
        except Exception:
            if self._fallback is not None:
                return self._fallback.history(code, start, end, fields=fields)
            raise
        if df.empty:
            if self._fallback is not None:
                return self._fallback.history(code, start, end, fields=fields)
            raise DataNotFoundError(f"No akshare data for {code} in [{start}, {end}]")
        df = df.set_index("date").sort_index()
        if fields is not None:
            cols = [f for f in fields if f in df.columns]
            df = df[cols]
        return df

    def snapshot(self, code: str, as_of: datetime) -> dict:
        # We need history to compute snapshot; fetch a small window and take last.
        as_of_date = as_of.date() if isinstance(as_of, datetime) else as_of
        # Pull the last 5 trading days ending at as_of
        start = as_of_date  # 5-day window is enough
        try:
            df = self._call(lambda: self._fetch_history_raw(code, start, as_of_date))
        except Exception:
            if self._fallback is not None:
                return self._fallback.snapshot(code, as_of)
            raise
        if df.empty:
            if self._fallback is not None:
                return self._fallback.snapshot(code, as_of)
            raise DataNotFoundError(f"No snapshot for {code} at or before {as_of}")
        df = df.set_index(pd.to_datetime(df["date"])).sort_index()
        valid = df.loc[df.index <= pd.Timestamp(as_of_date)]
        if valid.empty:
            if self._fallback is not None:
                return self._fallback.snapshot(code, as_of)
            raise DataNotFoundError(f"No snapshot for {code} at or before {as_of}")
        row = valid.iloc[-1]
        return {
            "last_price": float(row["close"]),
            "volume": float(row["volume"]),
            "money": float(row["money"]) if "money" in row and row["money"] is not None else 0.0,
        }

    def all_etfs(self, as_of: date_cls) -> list[str]:
        return [code for code, _ in self.all_etf_entries(as_of)]

    def all_etf_entries(self, as_of: date_cls) -> list[tuple[str, str]]:
        akshare = _import_akshare()
        df = self._call(lambda: akshare.fund_etf_name_em())
        if df is None or df.empty:
            if self._fallback is not None:
                return self._fallback.all_etf_entries(as_of)
            return []
        if _NAME_COL_CODE not in df.columns:
            if self._fallback is not None:
                return self._fallback.all_etf_entries(as_of)
            return []
        codes = df[_NAME_COL_CODE].astype(str)
        if _NAME_COL_NAME in df.columns:
            names = df[_NAME_COL_NAME].astype(str)
        else:
            names = codes  # fallback if name column missing
        return list(zip(codes.tolist(), names.tolist()))  # noqa: B905
