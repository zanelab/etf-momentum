"""AkShare-backed market data source for A-share ETFs.

Uses urllib directly to call eastmoney's K-line API (bypassing akshare's
requests-based HTTP layer which is blocked by eastmoney on some networks).
akshare is still used for the ETF spot list (fund_etf_spot_em).
"""
import json
import ssl
import urllib.request
from datetime import date as date_cls
from datetime import datetime
from typing import Optional, List

import pandas as pd

from app.data_sources.base import DataNotFoundError, FieldName, MarketDataSource
from app.data_sources.codes import normalize_etf_code
from app.data_sources.retry import retry_with_backoff

# eastmoney K-line API — verified reachable from Mac + Docker host network
_EM_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

_EM_KLINE_PARAMS = {
    "fields1": "f1,f2,f3,f4,f5,f6",
    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
    "ut": "7eea3edcaed734bea9cbfc24409ed989",
    "klt": "101",  # daily
    "fqt": "0",  # no adjust
}

# Map eastmoney's kline field indices to column names
_EM_KLINE_FIELDS = [
    "date", "open", "close", "high", "low", "volume", "money",
    "amplitude", "change_pct", "change", "turnover",
]


def _import_akshare():
    try:
        import akshare  # type: ignore
    except ImportError as e:
        raise ImportError(
            "akshare is not installed. Run `pip install -r backend/requirements.txt`."
        ) from e
    return akshare


class AkShareSource(MarketDataSource):
    """Fetches A-share ETF OHLCV via eastmoney API directly, with akshare as fallback for spot list."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ) -> None:
        _import_akshare()  # Fail fast if akshare is not installed
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._initial_delay = initial_delay
        self._ctx = ssl.create_default_context()

    def _call(self, fn):
        return retry_with_backoff(
            fn,
            max_retries=self._max_retries,
            backoff_factor=self._backoff_factor,
            initial_delay=self._initial_delay,
        )

    def _secid(self, code: str) -> str:
        """Convert normalized code (e.g. '510300') to eastmoney secid (e.g. '1.510300')."""
        # SH ETFs start with 51xxxx, SZ ETFs with 15xxxx or 15xxxx
        if code.startswith(("51", "588")):
            return f"1.{code}"
        else:
            return f"0.{code}"

    def _fetch_history_raw(self, code: str, start: date_cls, end: date_cls) -> pd.DataFrame:
        """Fetch daily OHLCV directly from eastmoney K-line API via urllib."""
        secid = self._secid(code)
        params = {
            **_EM_KLINE_PARAMS,
            "secid": secid,
            "beg": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{_EM_KLINE_URL}?{query}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://quote.eastmoney.com/",
                "Accept": "*/*",
            },
        )

        with urllib.request.urlopen(req, timeout=15, context=self._ctx) as resp:
            raw = resp.read().decode("utf-8")

        data = json.loads(raw)
        if data.get("rc") != 0:
            raise DataNotFoundError(f"eastmoney API error: {data.get('dsc', data)}")

        klines = data["data"].get("klines", [])
        if not klines:
            return pd.DataFrame()

        rows = [line.split(",") for line in klines]
        df = pd.DataFrame(rows, columns=_EM_KLINE_FIELDS)
        df["date"] = pd.to_datetime(df["date"])
        for col in ["open", "close", "high", "low", "volume", "money"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def history(
        self,
        code: str,
        start: date_cls,
        end: date_cls,
        fields: Optional[List[FieldName]] = None,
    ) -> pd.DataFrame:
        df = self._call(lambda: self._fetch_history_raw(code, start, end))
        if df.empty:
            raise DataNotFoundError(f"No data for {code} in [{start}, {end}]")
        df = df.set_index("date").sort_index()
        if fields is not None:
            cols = [f for f in fields if f in df.columns]
            df = df[cols]
        return df

    def snapshot(self, code: str, as_of: datetime) -> dict:
        as_of_date = as_of.date() if isinstance(as_of, datetime) else as_of
        start = as_of_date
        df = self._call(lambda: self._fetch_history_raw(code, start, as_of_date))
        if df.empty:
            raise DataNotFoundError(f"No snapshot for {code} at or before {as_of}")
        df = df.set_index(pd.to_datetime(df["date"])).sort_index()
        valid = df.loc[df.index <= pd.Timestamp(as_of_date)]
        if valid.empty:
            raise DataNotFoundError(f"No snapshot for {code} at or before {as_of}")
        row = valid.iloc[-1]
        return {
            "last_price": float(row["close"]),
            "volume": float(row["volume"]),
            "money": float(row["money"]) if "money" in row and row["money"] is not None else 0.0,
        }

    def all_etfs(self, as_of: date_cls) -> List[str]:
        return [code for code, _ in self.all_etf_entries(as_of)]

    def all_etf_entries(self, as_of: date_cls) -> List[tuple[str, str]]:
        akshare = _import_akshare()
        df = self._call(lambda: akshare.fund_etf_spot_em())
        if df is None or df.empty:
            return []
        code_col = "代码"
        name_col = "名称"
        if code_col not in df.columns:
            return []
        raw_codes = df[code_col].astype(str)
        if name_col in df.columns:
            names = df[name_col].astype(str)
        else:
            names = raw_codes
        codes: List[str] = []
        valid_names: List[str] = []
        for raw, n in zip(raw_codes.tolist(), names.tolist()):
            try:
                codes.append(normalize_etf_code(raw))
                valid_names.append(n)
            except ValueError:
                continue
        return list(zip(codes, valid_names))