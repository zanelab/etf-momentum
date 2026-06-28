"""Market data source abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal

import pandas as pd


class DataNotFoundError(LookupError):
    """Raised when requested market data is unavailable."""


FieldName = Literal["open", "high", "low", "close", "volume", "money"]


class MarketDataSource(ABC):
    """Abstract interface for fetching historical market data."""

    @abstractmethod
    def history(
        self,
        code: str,
        start: date,
        end: date,
        fields: list[FieldName] | None = None,
    ) -> pd.DataFrame:
        """Return a DataFrame indexed by date with the requested fields."""
        ...

    @abstractmethod
    def snapshot(self, code: str, as_of: datetime) -> dict[str, float]:
        """Return the latest snapshot fields for `code` at or before `as_of`.

        Returns a dict with at least `last_price` and `volume`.
        """
        ...

    @abstractmethod
    def all_etfs(self, as_of: date) -> list[str]:
        """Return all ETF codes known to this source as of `as_of`."""
        ...