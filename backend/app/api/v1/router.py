"""v1 业务路由聚合。"""

from fastapi import APIRouter

from app.api.v1.etfs import router as etfs_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(etfs_router)
