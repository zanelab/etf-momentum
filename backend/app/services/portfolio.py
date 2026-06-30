"""Portfolio CRUD service backed by SQLite."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, delete, select, update

from app.db import get_engine
from app.models.portfolio import Portfolio


def get_all_holdings() -> list[Portfolio]:
    """Return all portfolio holdings sorted by code."""
    with Session(get_engine()) as session:
        rows = session.exec(select(Portfolio).order_by(Portfolio.code)).all()
        return list(rows)


def upsert_holding(code: str, name: str, shares: int, cost_price: float) -> Portfolio:
    """Insert or update a portfolio holding."""
    with Session(get_engine()) as session:
        existing = session.exec(select(Portfolio).where(Portfolio.code == code)).first()
        if existing:
            existing.name = name
            existing.shares = shares
            existing.cost_price = cost_price
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        else:
            row = Portfolio(code=code, name=name, shares=shares, cost_price=cost_price)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row


def delete_holding(code: str) -> bool:
    """Delete a portfolio holding by code. Returns True if deleted, False if not found."""
    with Session(get_engine()) as session:
        existing = session.exec(select(Portfolio).where(Portfolio.code == code)).first()
        if not existing:
            return False
        session.delete(existing)
        session.commit()
        return True