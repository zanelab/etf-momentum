"""Portfolio REST API."""
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.portfolio import delete_holding, get_all_holdings, upsert_holding

router = APIRouter()


class PortfolioResponse(BaseModel):
    code: str
    name: str
    shares: int
    cost_price: float


class PortfolioCreate(BaseModel):
    code: str = Field(max_length=32)
    name: str = Field(max_length=128)
    shares: int = Field(gt=0)
    cost_price: float = Field(gt=0)


class PortfolioUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    shares: int | None = Field(default=None, gt=0)
    cost_price: float | None = Field(default=None, gt=0)


@router.get("", response_model=list[PortfolioResponse])
def list_portfolio() -> list[dict[str, Any]]:
    """Return all portfolio holdings."""
    holdings = get_all_holdings()
    return [
        {
            "code": h.code,
            "name": h.name,
            "shares": h.shares,
            "cost_price": h.cost_price,
        }
        for h in holdings
    ]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(body: PortfolioCreate) -> dict[str, Any]:
    """Add a new portfolio holding."""
    h = upsert_holding(body.code, body.name, body.shares, body.cost_price)
    return {
        "code": h.code,
        "name": h.name,
        "shares": h.shares,
        "cost_price": h.cost_price,
    }


@router.put("/{code}", response_model=PortfolioResponse)
def update_portfolio(code: str, body: PortfolioUpdate) -> dict[str, Any]:
    """Update an existing portfolio holding."""
    # Fetch current to merge with partial update
    holdings = get_all_holdings()
    existing = next((h for h in holdings if h.code == code), None)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    name = body.name if body.name is not None else existing.name
    shares = body.shares if body.shares is not None else existing.shares
    cost_price = body.cost_price if body.cost_price is not None else existing.cost_price

    h = upsert_holding(code, name, shares, cost_price)
    return {
        "code": h.code,
        "name": h.name,
        "shares": h.shares,
        "cost_price": h.cost_price,
    }


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_portfolio(code: str) -> None:
    """Delete a portfolio holding."""
    deleted = delete_holding(code)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")