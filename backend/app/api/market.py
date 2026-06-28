"""Market data endpoints: ETF listing + OHLCV history."""
from __future__ import annotations

from datetime import date as date_type
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data_sources.base import DataNotFoundError
from app.data_sources.fixture import FixtureCSVSource
from app.services.today import load_display_names

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"

router = APIRouter(tags=["market"])


def _market() -> FixtureCSVSource:
    return FixtureCSVSource(FIXTURES_DIR)


class ETFListItem(BaseModel):
    code: str
    display_name: str | None = None


class ETFListResponse(BaseModel):
    etfs: list[ETFListItem]


@router.get("/list", response_model=ETFListResponse)
def list_etfs() -> ETFListResponse:
    market = _market()
    codes = market.all_etfs(date_type.today())
    names = load_display_names(codes)
    etfs = [ETFListItem(code=c, display_name=names.get(c)) for c in codes]
    return ETFListResponse(etfs=etfs)


class HistoryRow(BaseModel):
    model_config = {"extra": "allow"}
    date: str


class HistoryResponse(BaseModel):
    model_config = {"extra": "allow"}
    code: str
    start: str
    end: str
    fields: list[str]
    rows: list[dict]


def _serialize_value(v) -> float | None:
    if v is None:
        return None
    try:
        if v != v:  # NaN
            return None
    except TypeError:
        pass
    return float(v)


@router.get("/history", response_model=HistoryResponse)
def market_history(
    code: Annotated[str, Query(min_length=4)],
    start: Annotated[date_type, Query(...)],
    end: Annotated[date_type, Query(...)],
    fields: Annotated[
        str | None,
        Query(description="Comma-separated field list"),
    ] = None,
) -> HistoryResponse:
    if end < start:
        raise HTTPException(status_code=400, detail="end must be on or after start")
    if fields:
        requested = [f.strip() for f in fields.split(",") if f.strip()]
    else:
        requested = ["open", "high", "low", "close", "volume"]

    market = _market()
    try:
        df = market.history(code, start, end, fields=requested)
    except DataNotFoundError as err:
        raise HTTPException(status_code=404, detail=f"No data for {code}") from err
    rows: list[dict] = []
    for ts, row in df.iterrows():
        rec: dict = {"date": ts.strftime("%Y-%m-%d")}
        for f in requested:
            rec[f] = _serialize_value(row.get(f))
        rows.append(rec)
    return HistoryResponse(
        code=code,
        start=start.isoformat(),
        end=end.isoformat(),
        fields=requested,
        rows=rows,
    )
