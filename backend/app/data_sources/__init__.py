"""Market data source factory.

Selects a `MarketDataSource` by name. When `name` is None, the
`ETF_DATA_SOURCE` environment variable is consulted (default: "fixture").
"""
import os
from pathlib import Path
from typing import Optional

from app.data_sources.akshare_source import AkShareSource
from app.data_sources.base import MarketDataSource
from app.data_sources.cache import CachedSource
from app.data_sources.fixture import FixtureCSVSource
from app.db import get_db_path, get_engine

DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def _fixtures_dir() -> Path:
    env = os.environ.get("FIXTURES_DIR")
    return Path(env) if env else DEFAULT_FIXTURES_DIR


def make_source(name: Optional[str] = None) -> MarketDataSource:
    """Build a MarketDataSource by name.

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
    if selected == "fixture":
        return FixtureCSVSource(_fixtures_dir())
    if selected == "akshare":
        inner = AkShareSource(fixtures_dir=_fixtures_dir())
        return CachedSource(inner, engine=get_engine())
    raise ValueError(
        f"Unknown data source: {selected!r}. Valid options: 'fixture', 'akshare'."
    )
