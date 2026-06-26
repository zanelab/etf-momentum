"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="etf-momentum API",
    version="0.1.0",
    description="A 股 ETF 动量策略系统后端 API",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(api_v1_router)
