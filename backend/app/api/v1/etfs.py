"""ETF 业务端点（v1）。"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.etf import ETF

router = APIRouter(prefix="/etfs", tags=["etfs"])


@router.get("/count")
def count_etfs(db: Session = Depends(get_db)) -> dict:
    """返回 ETF 总数（冒烟测试端点，验证 Depends 注入）。"""
    total = db.execute(select(func.count()).select_from(ETF)).scalar_one()
    return {"count": total}
