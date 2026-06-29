"""Screening, portfolio, and signals endpoints."""
from __future__ import annotations

from datetime import date as date_type
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.data_sources import make_source
from app.data_sources.base import DataNotFoundError, MarketDataSource
from app.services.portfolio_mock import get_mock_portfolio
from app.services.screening import filter_etfs
from app.services.signals import generate_signals
from app.services.today import (
    load_display_names,
    load_static_pool,
    load_strategy_params,
    load_themes,
    resolve_today,
    select_kwargs_for_params,
)
from app.services.types import StrategyParams

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"

router = APIRouter(tags=["screening"])


def _market(source: Optional[str] = None):
    return make_source(source)


def _params_for_today() -> StrategyParams:
    merged = load_strategy_params()
    kwargs = select_kwargs_for_params(merged, set(StrategyParams.model_fields))
    return StrategyParams(**kwargs)


# ────────────── /api/screening/today ──────────────


class ScreeningTodayResponse(BaseModel):
    as_of: date_type
    targets: list[str]


@router.get("/screening/today", response_model=ScreeningTodayResponse)
def screening_today(source: Optional[str] = Query(None, description="Data source override")) -> ScreeningTodayResponse:
    as_of = resolve_today(FIXTURES_DIR)
    params = _params_for_today()
    static_pool = load_static_pool()
    themes = load_themes()
    targets = filter_etfs(
        as_of,
        static_pool=static_pool,
        dynamic_pool=[],
        themes=themes,
        params=params,
        market=_market(source),
        display_names=load_display_names(static_pool),
    )
    return ScreeningTodayResponse(as_of=as_of.date(), targets=targets)


# ────────────── /api/portfolio ──────────────


class PortfolioHoldingOut(BaseModel):
    code: str
    shares: int
    cost_price: float
    current_price: float
    market_value: float
    pnl: float


class PortfolioResponse(BaseModel):
    as_of: date_type
    total_market_value: float
    total_cost: float
    total_pnl: float
    available_cash: float
    net_value: float
    holdings: list[PortfolioHoldingOut]


@router.get("/portfolio", response_model=PortfolioResponse)
def portfolio(source: Optional[str] = Query(None, description="Data source override")) -> PortfolioResponse:
    as_of = resolve_today(FIXTURES_DIR)
    market = _market(source)
    holdings = get_mock_portfolio(as_of)
    rows: list[PortfolioHoldingOut] = []
    total_market_value = 0.0
    total_cost = 0.0
    for h in holdings:
        try:
            snap = market.snapshot(h.code, as_of)
        except DataNotFoundError:
            continue
        last_price = float(snap["last_price"])
        market_value = last_price * h.shares
        cost_total = h.cost_price * h.shares
        pnl = market_value - cost_total
        rows.append(
            PortfolioHoldingOut(
                code=h.code,
                shares=h.shares,
                cost_price=h.cost_price,
                current_price=last_price,
                market_value=market_value,
                pnl=pnl,
            )
        )
        total_market_value += market_value
        total_cost += cost_total
    return PortfolioResponse(
        as_of=as_of.date(),
        total_market_value=round(total_market_value, 2),
        total_cost=round(total_cost, 2),
        total_pnl=round(total_market_value - total_cost, 2),
        available_cash=round(100_000.0 - total_cost, 2),
        net_value=round(total_market_value + (100_000.0 - total_cost), 2),
        holdings=rows,
    )


# ────────────── /api/signals/today ──────────────


class SignalOut(BaseModel):
    type: str
    etf: str
    reason: str
    shares: int | None = None
    target_value: float | None = None
    market_value: float | None = None
    pnl: float | None = None


class SignalsResponse(BaseModel):
    as_of: date_type
    signals: list[SignalOut]


@router.get("/signals/today", response_model=SignalsResponse)
def signals_today(source: Optional[str] = Query(None, description="Data source override")) -> SignalsResponse:
    as_of = resolve_today(FIXTURES_DIR)
    params = _params_for_today()
    market = _market(source)

    # Targets
    static_pool = load_static_pool()
    themes = load_themes()
    targets = filter_etfs(
        as_of,
        static_pool=static_pool,
        dynamic_pool=[],
        themes=themes,
        params=params,
        market=market,
        display_names=load_display_names(static_pool),
    )

    # Portfolio + total value
    holdings = get_mock_portfolio(as_of)
    total_market_value = 0.0
    total_cost = 0.0
    for h in holdings:
        snap = _safe_snapshot(market, h.code, as_of)
        if snap is None:
            continue
        last_price = float(snap["last_price"])
        total_market_value += last_price * h.shares
        total_cost += h.cost_price * h.shares
    available_cash = 100_000.0 - total_cost
    total_value = available_cash + total_market_value

    sigs = generate_signals(
        targets=targets,
        holdings=holdings,
        total_value=total_value,
        as_of=as_of,
        market=market,
        params=params,
    )
    out = [
        SignalOut(
            type=s.type,
            etf=s.etf,
            reason=s.reason,
            shares=s.shares,
            target_value=s.target_value,
            market_value=s.market_value,
            pnl=s.pnl,
        )
        for s in sigs
    ]
    return SignalsResponse(as_of=as_of.date(), signals=out)


def _safe_snapshot(market: MarketDataSource, code: str, as_of) -> dict | None:
    try:
        return market.snapshot(code, as_of)
    except DataNotFoundError:
        return None
