"""池 service：CRUD + 业务校验。

设计要点：
- 事务原子性：create / update 在一个 session.commit() 内完成。
- name 唯一约束冲突 → IntegrityError → 转 409 业务异常（不在 service 层 import HTTPException，
  让 router 决定 HTTP 状态码；service 只抛 PoolNameConflictError）。
- etf_code 必须存在于 etfs 表，否则 PoolUnknownEtfCodeError。
"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.etf import ETF
from app.models.etf_pool import EtfPool, EtfPoolMember


class PoolServiceError(Exception):
    """池 service 异常的基类。"""


class PoolNameConflictError(PoolServiceError):
    """name 重复 → 409。"""

    def __init__(self, name: str) -> None:
        super().__init__(f"Pool {name!r} already exists")
        self.name = name


class PoolUnknownEtfCodeError(PoolServiceError):
    """etf_code 不在 etfs 表 → 422。"""

    def __init__(self, unknown_codes: list[str]) -> None:
        super().__init__(f"Unknown ETF codes: {unknown_codes}")
        self.unknown_codes = list(unknown_codes)


class PoolNotFoundError(PoolServiceError):
    """id 不存在 → 404。"""

    def __init__(self, pool_id: int) -> None:
        super().__init__(f"EtfPool {pool_id} not found")
        self.pool_id = pool_id


class PoolService:
    """封装对 etf_pools + etf_pool_members 表的 CRUD。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- Queries ----------------------------------------------------------

    def list_all(self) -> list[EtfPool]:
        """全部池（带 members），按 id 升序。"""
        return list(
            self.db.execute(select(EtfPool).order_by(EtfPool.id)).scalars().all()
        )

    def get(self, pool_id: int) -> EtfPool:
        """单条池详情；不存在时抛 PoolNotFoundError。"""
        pool = self.db.execute(
            select(EtfPool).where(EtfPool.id == pool_id)
        ).scalar_one_or_none()
        if pool is None:
            raise PoolNotFoundError(pool_id)
        return pool

    # -- Mutations --------------------------------------------------------

    def create(self, *, name: str, description: str | None, etf_codes: list[str]) -> EtfPool:
        """新建池。

        Args:
            name: 唯一名称
            description: 可选
            etf_codes: 池成员 codes（至少 1 个，全部必须存在于 etfs 表）

        Returns:
            创建后的 EtfPool（refresh 过）

        Raises:
            PoolUnknownEtfCodeError: 任一 code 不在 etfs 表
            PoolNameConflictError: name 重复（IntegrityError → 409）
        """
        if not etf_codes:
            raise ValueError("etf_codes must not be empty")

        self._verify_codes_exist(etf_codes)

        pool = EtfPool(name=name, description=description)
        for position, code in enumerate(etf_codes):
            pool.members.append(EtfPoolMember(etf_code=code, position=position))

        self.db.add(pool)
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            if "uq_etf_pools_name" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                raise PoolNameConflictError(name) from e
            raise

        self.db.refresh(pool)
        return pool

    def update(
        self,
        pool_id: int,
        *,
        name: str,
        description: str | None,
        etf_codes: list[str],
    ) -> EtfPool:
        """整体替换池的 name / description / members。

        Raises:
            PoolNotFoundError: id 不存在
            PoolUnknownEtfCodeError: 任一 code 不在 etfs 表
            PoolNameConflictError: 新 name 已被另一池占用
        """
        if not etf_codes:
            raise ValueError("etf_codes must not be empty")

        pool = self.get(pool_id)
        self._verify_codes_exist(etf_codes)

        pool.name = name
        pool.description = description

        # 整体替换 members：清空后重新加
        pool.members.clear()
        for position, code in enumerate(etf_codes):
            pool.members.append(EtfPoolMember(etf_code=code, position=position))

        # flush 触发 IntegrityError 以捕获重名
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            if "uq_etf_pools_name" in str(e.orig).lower() or "unique" in str(e.orig).lower():
                raise PoolNameConflictError(name) from e
            raise

        self.db.refresh(pool)
        return pool

    def delete(self, pool_id: int) -> None:
        """删除池（cascade 清 members）。不存在不抛异常（idempotent）。"""
        pool = self.db.execute(
            select(EtfPool).where(EtfPool.id == pool_id)
        ).scalar_one_or_none()
        if pool is None:
            return
        self.db.delete(pool)
        self.db.commit()

    # -- Helpers ----------------------------------------------------------

    def _verify_codes_exist(self, codes: list[str]) -> None:
        """检查 codes 是否全部存在于 etfs 表。"""
        if not codes:
            return
        rows = self.db.execute(
            select(ETF.code).where(ETF.code.in_(codes))
        ).scalars().all()
        existing = set(rows)
        missing = [c for c in codes if c not in existing]
        if missing:
            raise PoolUnknownEtfCodeError(missing)
