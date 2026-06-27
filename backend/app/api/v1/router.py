"""v1 业务路由聚合。"""

from fastapi import APIRouter

from app.api.v1.backtest import router as backtest_router
from app.api.v1.etfs import router as etfs_router
from app.api.v1.pools import router as pools_router
from app.api.v1.signals import router as signals_router
from app.api.v1.sync import router as sync_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(etfs_router)
api_v1_router.include_router(signals_router)
api_v1_router.include_router(backtest_router)
api_v1_router.include_router(sync_router)
api_v1_router.include_router(pools_router)
