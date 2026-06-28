"""Pydantic models for screening service inputs."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class StrategyParams(BaseModel):
    """Strategy parameters (mirrors main.py STRATEGY_CONFIG)."""

    model_config = {"extra": "forbid"}

    stock_sum: int = Field(default=1, ge=1, le=20)
    min_money: int = Field(default=500, ge=0)
    momentum_days: int = Field(default=25, ge=5, le=250)
    enable_volume_check: bool = True
    volume_lookback: int = Field(default=5, ge=1)
    volume_threshold: float = Field(default=2.5, gt=0)
    ma_short: int = Field(default=20, ge=2)
    ma_long: int = Field(default=60, ge=5)
    enable_ma_filter: bool = True
    stop_loss_ratio: float = Field(default=0.92, gt=0, lt=2)
    defensive_etf: str = Field(default="511880.XSHG", max_length=32)
    enable_industry_diverse: bool = False
    dynamic_pool_size: int = Field(default=150, ge=1)
    dynamic_pool_min_money: int = Field(default=50_000_000, ge=0)

    @field_validator("ma_long")
    @classmethod
    def _ma_long_gt_short(cls, v: int, info) -> int:
        short = info.data.get("ma_short")
        if short is not None and v <= short:
            raise ValueError("ma_long must be greater than ma_short")
        return v
