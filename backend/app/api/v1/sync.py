"""Sync 端点（v1）：etfs 与 prices。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.schemas import SyncPricesRequestPydantic, SyncResponsePydantic
from app.data.client import AkshareClient, AkshareHttpClient
from app.data.daily_prices import sync_daily_prices
from app.data.etf_master import sync_etf_master
from app.db.session import get_db

router = APIRouter(prefix="/sync", tags=["sync"])


def _build_client() -> AkshareClient:
    """默认构造真实 akshare 客户端。测试可通过 monkeypatch 替换。"""
    return AkshareHttpClient()


@router.post("/etfs", response_model=None)
def post_sync_etfs(db: Session = Depends(get_db)) -> dict:
    """同步全市场 ETF 主数据到 etfs 表。"""
    result = sync_etf_master(db, _build_client())
    return {
        "fetched": result.get("fetched", 0),
        "upserted": result.get("upserted", 0),
    }


@router.post("/prices")
def post_sync_prices(
    body: SyncPricesRequestPydantic,
    db: Session = Depends(get_db),
) -> dict:
    """按 codes 同步日线行情到 daily_prices 表。"""
    result = sync_daily_prices(
        db,
        _build_client(),
        list(body.codes),
        start=body.start,
        end=body.end,
        full=body.full,
    )
    return result
