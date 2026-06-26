"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import DATABASE_URL


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print(f"[etf-momentum] DATABASE_URL={DATABASE_URL}")
    yield


app = FastAPI(
    title="etf-momentum API",
    version="0.1.0",
    description="A 股 ETF 动量策略系统后端 API",
    lifespan=lifespan,
)

# CORS: 允许 Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(api_v1_router)
