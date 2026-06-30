"""Read-through cache wrapping any MarketDataSource.

Bars are cached in the `market_bar_cache` table keyed by (code, trade_date).
The wrapper delegates `snapshot` and `history` calls to the inner source
on miss and writes the result back. Hit/miss counters are exposed via
`stats()`.
"""
from datetime import date as date_cls
from datetime import datetime
from typing import Optional, List

import pandas as pd
from sqlalchemy.engine import Engine
from sqlmodel import Session, delete, select

from app.data_sources.base import DataNotFoundError, FieldName, MarketDataSource
from app.models.market_bar_cache import MarketBarCache


class CachedSource(MarketDataSource):
    """Read-through cache for any MarketDataSource."""

    def __init__(self, inner: MarketDataSource, engine: Engine) -> None:
        self._inner = inner
        self._engine = engine
        self._hit_count = 0
        self._miss_count = 0

    def stats(self) -> dict:
        return {"hit": self._hit_count, "miss": self._miss_count}

    def clear(self) -> None:
        with Session(self._engine) as session:
            session.execute(delete(MarketBarCache))
            session.commit()

    def _read_one(self, code: str, d: date_cls) -> Optional[MarketBarCache]:
        with Session(self._engine) as session:
            row = session.exec(
                select(MarketBarCache).where(
                    MarketBarCache.code == code, MarketBarCache.trade_date == d
                )
            ).first()
            session.expunge(row) if row else None
            return row

    def _read_range(
        self, code: str, start: date_cls, end: date_cls
    ) -> dict[date_cls, MarketBarCache]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(MarketBarCache).where(
                    MarketBarCache.code == code,
                    MarketBarCache.trade_date >= start,
                    MarketBarCache.trade_date <= end,
                )
            ).all()
            return {r.trade_date: r for r in rows}

    def _write_one(self, code: str, d: date_cls, last_price: float, volume: float, money: float) -> None:
        with Session(self._engine) as session:
            existing = session.exec(
                select(MarketBarCache).where(
                    MarketBarCache.code == code, MarketBarCache.trade_date == d
                )
            ).first()
            if existing is not None:
                existing.open = last_price  # best-effort: only have close here
                existing.high = last_price
                existing.low = last_price
                existing.close = last_price
                existing.volume = volume
                existing.money = money
                existing.cached_at = datetime.utcnow()
            else:
                row = MarketBarCache(
                    code=code,
                    trade_date=d,
                    open=last_price,
                    high=last_price,
                    low=last_price,
                    close=last_price,
                    volume=volume,
                    money=money,
                    cached_at=datetime.utcnow(),
                )
                session.add(row)
            session.commit()

    def _write_history(self, code: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
        now = datetime.utcnow()
        with Session(self._engine) as session:
            for ts, row in df.iterrows():
                d = ts.date() if isinstance(ts, pd.Timestamp) else ts
                # upsert
                existing = session.exec(
                    select(MarketBarCache).where(
                        MarketBarCache.code == code, MarketBarCache.trade_date == d
                    )
                ).first()
                if existing is not None:
                    existing.open = float(row["open"])
                    existing.high = float(row["high"])
                    existing.low = float(row["low"])
                    existing.close = float(row["close"])
                    existing.volume = float(row["volume"])
                    existing.money = (
                        float(row["money"]) if "money" in row and row["money"] is not None else None
                    )
                    existing.cached_at = now
                else:
                    session.add(
                        MarketBarCache(
                            code=code,
                            trade_date=d,
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                            money=(
                                float(row["money"])
                                if "money" in row and row["money"] is not None
                                else None
                            ),
                            cached_at=now,
                        )
                    )
            session.commit()

    def snapshot(self, code: str, as_of: datetime) -> dict:
        target_date = as_of.date() if isinstance(as_of, datetime) else as_of
        cached = self._read_one(code, target_date)
        if cached is not None:
            self._hit_count += 1
            return {
                "last_price": float(cached.close),
                "volume": float(cached.volume),
                "money": float(cached.money) if cached.money is not None else 0.0,
            }
        # miss: fetch from inner
        self._miss_count += 1
        snap = self._inner.snapshot(code, as_of)
        self._write_one(
            code, target_date, snap["last_price"], snap["volume"], snap.get("money", 0.0)
        )
        return snap

    def history(
        self,
        code: str,
        start: date_cls,
        end: date_cls,
        fields: Optional[List[FieldName]] = None,
    ) -> pd.DataFrame:
        cached = self._read_range(code, start, end)
        # If every date in the cached range covers what inner would return,
        # we cannot know without calling inner. We use a simpler heuristic:
        # if the cache is non-empty AND its date range equals or exceeds
        # the requested range, skip inner. Otherwise always call inner
        # and write through.
        cached_dates = set(cached.keys())
        requested_dates = {
            d.date() for d in pd.date_range(start, end, freq="D")
        }  # calendar days; we accept that inner may return fewer trading days
        if cached_dates and requested_dates and cached_dates >= requested_dates:
            self._hit_count += len(cached_dates)
        else:
            df = self._inner.history(code, start, end, fields=None)
            if df.empty:
                raise DataNotFoundError(f"No data for {code} in [{start}, {end}]")
            newly_added = max(0, len(df) - len(cached))
            self._miss_count += newly_added
            self._write_history(code, df)
            cached = self._read_range(code, start, end)

        if not cached:
            raise DataNotFoundError(f"No data for {code} in [{start}, {end}]")
        rows = sorted(cached.items(), key=lambda kv: kv[0])
        records = []
        for d, row in rows:
            rec = {
                "date": pd.Timestamp(d),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
                "money": float(row.money) if row.money is not None else None,
            }
            records.append(rec)
        df = pd.DataFrame(records).set_index("date").sort_index()
        if fields is not None:
            cols = [f for f in fields if f in df.columns]
            df = df[cols]
        return df

    def all_etfs(self, as_of: date_cls) -> List[str]:
        return self._inner.all_etfs(as_of)

    def all_etf_entries(self, as_of: date_cls) -> List[tuple[str, str]]:
        return self._inner.all_etf_entries(as_of)
