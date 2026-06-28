"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db as db_module
from app.api.backtest import router as backtest_router
from app.api.configs import router as configs_router
from app.api.market import router as market_router
from app.api.screening import router as screening_router
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
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


app.include_router(configs_router, prefix="/api/configs")
app.include_router(screening_router, prefix="/api")
app.include_router(backtest_router, prefix="/api/backtest")
app.include_router(market_router, prefix="/api/market")
