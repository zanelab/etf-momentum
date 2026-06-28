"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app import db as db_module
from app.api.backtest import router as backtest_router
from app.api.configs import router as configs_router
from app.api.market import router as market_router
from app.api.screening import router as screening_router
from app.data_sources import make_source
from app.data_sources.cache import CachedSource
from app.seed import seed_if_empty
from app.services.daily_sync import sync_today


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_module.init_db()
    seed_if_empty()
    sync_today()
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
