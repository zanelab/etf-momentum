"""Pydantic 请求/响应模型（v1 API）。"""

from datetime import date
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

ALLOWED_REBALANCE_FREQ = ("monthly", "quarterly")

from app.models.backtest_run import BacktestRun
from app.models.daily_price import DailyPrice
from app.models.etf import ETF
from app.models.signal_snapshot import SignalSnapshot

T = TypeVar("T")


class _DecimalAsStrBase(BaseModel):
    """所有 Decimal 字段序列化为 string，金融保精度。"""

    model_config = ConfigDict(
        # 让 Pydantic v2 在序列化 Decimal 时输出 str
        json_encoders={Decimal: str},
    )


# ---------------------------------------------------------------------------
# ETF
# ---------------------------------------------------------------------------


class ETFPydantic(BaseModel):
    code: str
    name: str
    market: str
    category: str | None = None

    @classmethod
    def from_orm(cls, etf: ETF) -> "ETFPydantic":
        return cls(
            code=etf.code,
            name=etf.name,
            market=etf.market,
            category=etf.category,
        )


class ETFListPydantic(_DecimalAsStrBase):
    items: list[ETFPydantic]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Daily price
# ---------------------------------------------------------------------------


class DailyPricePydantic(BaseModel):
    code: str
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    @field_serializer("open", "high", "low", "close", when_used="json")
    def _serialize_decimal(self, v: Decimal) -> str:
        return str(v)

    @classmethod
    def from_orm(cls, dp: DailyPrice) -> "DailyPricePydantic":
        return cls(
            code=dp.code,
            date=dp.date,
            open=dp.open,
            high=dp.high,
            low=dp.low,
            close=dp.close,
            volume=dp.volume,
        )


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


class SignalRowPydantic(BaseModel):
    etf_code: str
    momentum_score: Decimal | None
    rank: int | None
    action: str

    @field_serializer("momentum_score", when_used="json")
    def _serialize_score(self, v: Decimal | None) -> str | None:
        return None if v is None else str(v)

    @classmethod
    def from_orm(cls, row: SignalSnapshot) -> "SignalRowPydantic":
        return cls(
            etf_code=row.etf_code,
            momentum_score=row.momentum_score,
            rank=row.rank,
            action=row.action,
        )


class SignalSnapshotPydantic(BaseModel):
    date: date
    rows: list[SignalRowPydantic]


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


class BacktestRequestPydantic(BaseModel):
    """POST /backtest 请求体。"""

    etf_pool: list[str] = Field(min_length=1)
    start: date
    end: date
    initial_cash: Decimal
    lookback: int = 252
    skip: int = 21
    top_n: int = 5
    rebalance_freq: str = "monthly"  # "monthly" | "quarterly"

    @field_validator("rebalance_freq")
    @classmethod
    def _validate_freq(cls, v: str) -> str:
        if v not in ALLOWED_REBALANCE_FREQ:
            raise ValueError(
                f"rebalance_freq must be one of {ALLOWED_REBALANCE_FREQ}, got {v!r}"
            )
        return v

    @field_serializer("initial_cash", when_used="json")
    def _serialize_cash(self, v: Decimal) -> str:
        return str(v)


class NavPointPydantic(BaseModel):
    date: date
    nav: Decimal

    @field_serializer("nav", when_used="json")
    def _serialize_nav(self, v: Decimal) -> str:
        return str(v)


class NavSeriesPydantic(BaseModel):
    id: int
    nav_series: list[NavPointPydantic]


class BacktestRunPydantic(_DecimalAsStrBase):
    """GET /backtest/{id} 响应。"""

    id: int
    name: str | None = None
    etf_pool: list[str]
    momentum_window: int
    rebalance_freq: str
    start_date: date
    end_date: date
    metrics: dict[str, Any] | None = None
    created_at: str  # ISO 8601

    @classmethod
    def from_orm(cls, run: BacktestRun) -> "BacktestRunPydantic":
        return cls(
            id=run.id,
            name=run.name,
            etf_pool=list(run.etf_pool),
            momentum_window=run.momentum_window,
            rebalance_freq=run.rebalance_freq,
            start_date=run.start_date,
            end_date=run.end_date,
            metrics=run.metrics,
            created_at=run.created_at.isoformat() if run.created_at else "",
        )


class BacktestListPydantic(_DecimalAsStrBase):
    items: list[BacktestRunPydantic]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


class SyncPricesRequestPydantic(BaseModel):
    codes: list[str] = Field(min_length=1)
    start: date | None = None
    end: date | None = None
    full: bool = False


class SyncResponsePydantic(BaseModel):
    """Sync 响应统一格式。"""

    succeeded: int = 0
    failed: int = 0
    rows_written: int = 0
    fetched: int = 0
    upserted: int = 0


# ---------------------------------------------------------------------------
# 通用
# ---------------------------------------------------------------------------


class ListResponsePydantic(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


__all__ = [
    "ETFPydantic",
    "ETFListPydantic",
    "DailyPricePydantic",
    "SignalRowPydantic",
    "SignalSnapshotPydantic",
    "BacktestRequestPydantic",
    "BacktestRunPydantic",
    "BacktestListPydantic",
    "NavPointPydantic",
    "NavSeriesPydantic",
    "SyncPricesRequestPydantic",
    "SyncResponsePydantic",
    "ListResponsePydantic",
]
