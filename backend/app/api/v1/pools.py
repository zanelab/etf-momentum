"""ETF 策略池端点（v1）：CRUD。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import (
    EtfPoolCreatePydantic,
    EtfPoolDetailPydantic,
    EtfPoolListPydantic,
    EtfPoolSummaryPydantic,
    EtfPoolUpdatePydantic,
)
from app.db.session import get_db
from app.models.etf import ETF
from app.services.pool_service import (
    PoolNameConflictError,
    PoolNotFoundError,
    PoolService,
    PoolUnknownEtfCodeError,
)

router = APIRouter(prefix="/pools", tags=["pools"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_etf_map(db: Session, codes: list[str]) -> dict[str, ETF]:
    """批量查 ETF 字典，避免 N+1。"""
    if not codes:
        return {}
    rows = db.execute(select(ETF).where(ETF.code.in_(codes))).scalars().all()
    return {e.code: e for e in rows}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_pools(db: Session = Depends(get_db)) -> dict:
    """池列表（摘要，不含 members 明细）。"""
    svc = PoolService(db)
    pools = svc.list_all()
    items = [EtfPoolSummaryPydantic.from_orm(p) for p in pools]
    return {"items": items, "total": len(items)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pool(
    body: EtfPoolCreatePydantic,
    db: Session = Depends(get_db),
) -> dict:
    """新建池。"""
    svc = PoolService(db)
    try:
        pool = svc.create(
            name=body.name,
            description=body.description,
            etf_codes=list(body.etf_codes),
        )
    except PoolUnknownEtfCodeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PoolNameConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    etf_map = _build_etf_map(db, [m.etf_code for m in pool.members])
    return EtfPoolDetailPydantic.from_orm(pool, etf_map).model_dump(mode="json")


@router.get("/{pool_id}")
def get_pool(pool_id: int, db: Session = Depends(get_db)) -> dict:
    """单条池详情（含 members 明细）。"""
    svc = PoolService(db)
    try:
        pool = svc.get(pool_id)
    except PoolNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    etf_map = _build_etf_map(db, [m.etf_code for m in pool.members])
    return EtfPoolDetailPydantic.from_orm(pool, etf_map).model_dump(mode="json")


@router.put("/{pool_id}")
def update_pool(
    pool_id: int,
    body: EtfPoolUpdatePydantic,
    db: Session = Depends(get_db),
) -> dict:
    """整体替换池（name / description / members）。"""
    svc = PoolService(db)
    try:
        pool = svc.update(
            pool_id,
            name=body.name,
            description=body.description,
            etf_codes=list(body.etf_codes),
        )
    except PoolNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PoolUnknownEtfCodeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PoolNameConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    etf_map = _build_etf_map(db, [m.etf_code for m in pool.members])
    return EtfPoolDetailPydantic.from_orm(pool, etf_map).model_dump(mode="json")


@router.delete("/{pool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pool(pool_id: int, db: Session = Depends(get_db)) -> None:
    """删除池（cascade 清 members）。幂等：不存在时返回 204。"""
    svc = PoolService(db)
    svc.delete(pool_id)
    return None
