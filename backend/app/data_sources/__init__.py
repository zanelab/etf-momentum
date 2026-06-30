"""Market data source factory.

Selects a `MarketDataSource` by name. When `name` is None, the
`ETF_DATA_SOURCE` environment variable is consulted (default: "akshare").

Sources are memoized per name so that CachedSource stats (hit/miss counters)
accumulate across requests within the same process.
"""
import os
from typing import Optional

from app.data_sources.akshare_source import AkShareSource
from app.data_sources.base import MarketDataSource
from app.data_sources.cache import CachedSource
from app.db import get_engine

# Memoize built sources so CachedSource stats persist across requests.
_cache: dict[str, MarketDataSource] = {}


def make_source(name: Optional[str] = None) -> MarketDataSource:
    """Build a MarketDataSource by name (memoized per name).

    Args:
        name: Only "akshare" is supported. If None, the
            `ETF_DATA_SOURCE` env var is used (default "akshare").

    Returns:
        A MarketDataSource wrapped in CachedSource backed by the project SQLite DB.

    Raises:
        ValueError: If `name` (or the resolved env var) is not "akshare".
    """
    selected = (name or os.environ.get("ETF_DATA_SOURCE", "akshare")).lower()
    if selected in _cache:
        return _cache[selected]
    if selected == "akshare":
        inner = AkShareSource()
        src: MarketDataSource = CachedSource(inner, engine=get_engine())
    else:
        raise ValueError(
            f"Unknown data source: {selected!r}. Valid: 'akshare'."
        )
    _cache[selected] = src
    return src


def reset_source_cache() -> None:
    """Clear the memoized sources (used by tests for isolation)."""
    _cache.clear()
