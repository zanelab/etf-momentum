"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app import db as db_module
from app.api.backtest import router as backtest_router
from app.api.configs import router as configs_router
from app.api.market import router as market_router
from app.api.screening import router as screening_router
from app.api.sync import router as sync_router
from app.data_sources import make_source
from app.data_sources.cache import CachedSource
from app.db import get_engine, session_scope
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.seed import seed_if_empty
from app.services.daily_sync import sync_historical_for_pool

log = logging.getLogger(__name__)


def _pool_union_codes() -> list[str]:
    """Deduplicated union of static_pool + dynamic_pool codes (sorted)."""
    codes: set[str] = set()
    with session_scope(get_engine()) as s:
        for code, in s.query(StaticPool.code).all():
            codes.add(code)
        for code, in s.query(DynamicPoolEntry.code).all():
            codes.add(code)
    return sorted(codes)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_module.init_db()
    seed_if_empty()
    # Run an initial historical sync over the pool union. A failure here MUST
    # NOT crash the app — the sync endpoints exist precisely so users can
    # retry manually.
    try:
        codes = _pool_union_codes()
        if codes:
            sync_historical_for_pool(
                codes=codes,
                from_date=date.today() - timedelta(days=30),
                to_date=date.today(),
            )
    except Exception:  # noqa: BLE001 — startup must continue on sync failure
        log.exception("startup historical sync failed; continuing")
    yield


app = FastAPI(
    title="ETF Momentum API",
    version="0.1.0",
    description="Backend for the ETF momentum rotation strategy.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health(
    stats: Annotated[
        int | None,
        Query(description="When 1 and active source is CachedSource, include hit/miss counters."),
    ] = None,
) -> dict:
    """Liveness probe.

    With `?stats=1`, also reports cache hit/miss counts when the active
    source is wrapped in CachedSource.
    """
    body: dict = {"status": "ok"}
    if stats == 1:
        source = make_source()
        if isinstance(source, CachedSource):
            counters = source.stats()
            body["cache_hit"] = counters["hit"]
            body["cache_miss"] = counters["miss"]
    return body


app.include_router(configs_router, prefix="/api/configs")
app.include_router(screening_router, prefix="/api")
app.include_router(backtest_router, prefix="/api/backtest")
app.include_router(market_router, prefix="/api/market")
app.include_router(sync_router, prefix="/api")
