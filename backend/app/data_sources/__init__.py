"""Market data source factory.

Selects a `MarketDataSource` by name. When `name` is None, the
`ETF_DATA_SOURCE` environment variable is consulted (default: "fixture").

Sources are memoized per name so that CachedSource stats (hit/miss counters)
accumulate across requests within the same process.
"""
import os
from pathlib import Path
from typing import Optional

from app.data_sources.akshare_source import AkShareSource
from app.data_sources.base import MarketDataSource
from app.data_sources.cache import CachedSource
from app.data_sources.fixture import FixtureCSVSource
from app.db import get_engine

DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"

# Memoize built sources so CachedSource stats persist across requests.
_cache: dict[str, MarketDataSource] = {}


def _fixtures_dir() -> Path:
    env = os.environ.get("FIXTURES_DIR")
    return Path(env) if env else DEFAULT_FIXTURES_DIR


def make_source(name: Optional[str] = None) -> MarketDataSource:
    """Build a MarketDataSource by name (memoized per name).

    Args:
        name: One of "fixture" or "akshare". If None, the
            `ETF_DATA_SOURCE` env var is used (default "fixture").

    Returns:
        A MarketDataSource. For "akshare" the result is wrapped in
        CachedSource backed by the project SQLite DB.

    Raises:
        ValueError: If `name` (or the resolved env var) is not a recognized source.
    """
    selected = (name or os.environ.get("ETF_DATA_SOURCE", "fixture")).lower()
    if selected in _cache:
        return _cache[selected]
    if selected == "fixture":
        src: MarketDataSource = FixtureCSVSource(_fixtures_dir())
    elif selected == "akshare":
        inner = AkShareSource(fixtures_dir=_fixtures_dir())
        src = CachedSource(inner, engine=get_engine())
    else:
        raise ValueError(
            f"Unknown data source: {selected!r}. Valid options: 'fixture', 'akshare'."
        )
    _cache[selected] = src
    return src


def reset_source_cache() -> None:
    """Clear the memoized sources (used by tests for isolation)."""
    _cache.clear()
