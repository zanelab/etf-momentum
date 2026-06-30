"""Screening, portfolio, and signals endpoints."""
from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.data_sources import make_source
from app.data_sources.base import DataNotFoundError, MarketDataSource
from app.services.portfolio import get_all_holdings
from app.services.screening import filter_etfs, filter_etfs_detailed
from app.services.signals import generate_signals
from app.services.today import (
    load_display_names,
    load_static_pool,
    load_strategy_params,
    load_themes,
    select_kwargs_for_params,
)
from app.services.types import StrategyParams

router = APIRouter(tags=["screening"])


def _market(source: Optional[str] = None):
    return make_source(source)


def _params_for_today() -> StrategyParams:
    merged = load_strategy_params()
    kwargs = select_kwargs_for_params(merged, set(StrategyParams.model_fields))
    return StrategyParams(**kwargs)


# ────────────── /api/screening/today ──────────────


class ScreeningTargetDetail(BaseModel):
    """Per-ETF scoring detail returned alongside `targets` (spec §5.3 进阶)."""

    code: str
    momentum_score: float
    annual_return: float
    r2: float
    volume_ratio: Optional[float]


class ScreeningTodayResponse(BaseModel):
    as_of: date_type
    targets: List[str]
    details: List[ScreeningTargetDetail]


@router.get("/screening/today", response_model=ScreeningTodayResponse)
def screening_today(source: Optional[str] = Query(None, description="Data source override")) -> ScreeningTodayResponse:
    as_of = datetime.now()
    params = _params_for_today()
    static_pool = load_static_pool()
    themes = load_themes()
    scored = filter_etfs_detailed(
        as_of,
        static_pool=static_pool,
        dynamic_pool=[],
        themes=themes,
        params=params,
        market=_market(source),
        display_names=load_display_names(static_pool),
    )
    targets = [s.code for s in scored]
    details = [
        ScreeningTargetDetail(
            code=s.code,
            momentum_score=s.momentum_score,
            annual_return=s.annual_return,
            r2=s.r2,
            volume_ratio=s.volume_ratio,
        )
        for s in scored
    ]
    return ScreeningTodayResponse(as_of=as_of.date(), targets=targets, details=details)


# ────────────── /api/portfolio ──────────────


class PortfolioHoldingOut(BaseModel):
    code: str
    name: str
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
    holdings: List[PortfolioHoldingOut]


@router.get("/portfolio", response_model=PortfolioResponse)
def portfolio(source: Optional[str] = Query(None, description="Data source override")) -> PortfolioResponse:
    as_of = datetime.now()
    market = _market(source)
    holdings = get_all_holdings()
    rows: List[PortfolioHoldingOut] = []
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
                name=h.name,
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
    shares: Optional[int] = None
    target_value: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None


class SignalsResponse(BaseModel):
    as_of: date_type
    signals: List[SignalOut]


@router.get("/signals/today", response_model=SignalsResponse)
def signals_today(source: Optional[str] = Query(None, description="Data source override")) -> SignalsResponse:
    as_of = datetime.now()
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
    holdings = get_all_holdings()
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