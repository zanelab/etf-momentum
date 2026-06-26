"""ETF 基础查询工具。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.etf import ETF


class EtfRepository:
    """封装对 etfs 表的常用查询。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> ETF | None:
        return self.db.execute(
            select(ETF).where(ETF.code == code)
        ).scalar_one_or_none()

    def list_all(self) -> list[ETF]:
        return list(self.db.execute(select(ETF).order_by(ETF.code)).scalars().all())

    def create(self, *, code: str, name: str, market: str, category: str | None = None) -> ETF:
        etf = ETF(code=code, name=name, market=market, category=category)
        self.db.add(etf)
        self.db.commit()
        self.db.refresh(etf)
        return etf
