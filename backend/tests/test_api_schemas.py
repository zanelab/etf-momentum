"""Pydantic schema 单元测试：序列化、默认值、ORM 转换。"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas import (
    BacktestRequestPydantic,
    DailyPricePydantic,
    ETFPydantic,
    ListResponsePydantic,
    NavPointPydantic,
    NavSeriesPydantic,
    SignalRowPydantic,
    SignalSnapshotPydantic,
    SyncPricesRequestPydantic,
)
from app.models.backtest_run import BacktestRun
from app.models.daily_price import DailyPrice
from app.models.etf import ETF
from app.models.signal_snapshot import SignalSnapshot


def test_decimal_serialized_as_string():
    """Decimal 字段序列化到 JSON 时必须为 string，避免精度损失。"""
    dp = DailyPricePydantic(
        code="510300",
        date=date(2024, 1, 2),
        open=Decimal("4.1230"),
        high=Decimal("4.2000"),
        low=Decimal("4.1000"),
        close=Decimal("4.1230"),
        volume=1000,
    )
    payload = dp.model_dump_json()
    assert '"close":"4.1230"' in payload
    assert '"open":"4.1230"' in payload
    # 反序列化：Pydantic 把 str 还原为 Decimal（因字段类型是 Decimal）
    loaded = DailyPricePydantic.model_validate_json(payload)
    assert loaded.close == Decimal("4.1230")


def test_backtest_request_defaults():
    """BacktestRequestPydantic 默认值与 design.md 一致。"""
    req = BacktestRequestPydantic(
        etf_pool=["510300"],
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
        initial_cash="100000",
    )
    assert req.lookback == 252
    assert req.skip == 21
    assert req.top_n == 5
    assert req.rebalance_freq == "monthly"


def test_etf_from_orm():
    """ETFPydantic.from_orm 把 ETF ORM 行转 Pydantic。"""
    etf = ETF(code="510300", name="沪深300ETF", market="SH", category="指数")
    p = ETFPydantic.from_orm(etf)
    assert p.code == "510300"
    assert p.name == "沪深300ETF"
    assert p.market == "SH"
    assert p.category == "指数"


def test_etf_from_orm_category_none():
    """category 为 None 时正确传递。"""
    etf = ETF(code="510300", name="X", market="SH", category=None)
    p = ETFPydantic.from_orm(etf)
    assert p.category is None


def test_signal_row_serializes_decimal_as_string():
    """SignalRowPydantic 中 momentum_score (Decimal | None) 序列化为 string。"""
    row = SignalRowPydantic(
        etf_code="510300",
        momentum_score=Decimal("0.123456"),
        rank=1,
        action="BUY",
    )
    payload = row.model_dump_json()
    assert '"momentum_score":"0.123456"' in payload
    assert '"rank":1' in payload


def test_signal_row_watch_uses_null_decimal():
    """WATCH 行 momentum_score=None、rank=None。"""
    row = SignalRowPydantic(
        etf_code="999999",
        momentum_score=None,
        rank=None,
        action="WATCH",
    )
    payload = row.model_dump_json()
    assert '"momentum_score":null' in payload
    assert '"rank":null' in payload
    assert '"action":"WATCH"' in payload


def test_signal_snapshot_pydantic_round_trip():
    """SignalSnapshotPydantic 可序列化整组 snapshot。"""
    snap = SignalSnapshotPydantic(
        date=date(2024, 12, 31),
        rows=[
            SignalRowPydantic(etf_code="510300", momentum_score=Decimal("0.1"), rank=1, action="BUY"),
            SignalRowPydantic(etf_code="510500", momentum_score=Decimal("0.05"), rank=2, action="BUY"),
        ],
    )
    payload = snap.model_dump_json()
    loaded = SignalSnapshotPydantic.model_validate_json(payload)
    assert loaded.date == date(2024, 12, 31)
    assert len(loaded.rows) == 2
    assert loaded.rows[0].momentum_score == Decimal("0.1")


def test_nav_point_pydantic_serializes_decimal_as_string():
    """NavPointPydantic.nav (Decimal) 序列化为 string。"""
    pt = NavPointPydantic(date=date(2024, 1, 2), nav=Decimal("100000"))
    assert '"nav":"100000"' in pt.model_dump_json()


def test_nav_series_pydantic_round_trip():
    """NavSeriesPydantic 整体序列化。"""
    series = NavSeriesPydantic(
        id=1,
        nav_series=[
            NavPointPydantic(date=date(2024, 1, 2), nav=Decimal("100000")),
            NavPointPydantic(date=date(2024, 1, 3), nav=Decimal("101000")),
        ],
    )
    loaded = NavSeriesPydantic.model_validate_json(series.model_dump_json())
    assert loaded.id == 1
    assert len(loaded.nav_series) == 2
    assert loaded.nav_series[1].nav == Decimal("101000")


def test_list_response_pydantic_generic():
    """ListResponsePydantic[T] 泛型分页响应。"""
    resp = ListResponsePydantic[ETFPydantic](
        items=[ETFPydantic(code="510300", name="X", market="SH", category=None)],
        total=100,
        limit=50,
        offset=0,
    )
    payload = resp.model_dump_json()
    loaded = ListResponsePydantic.model_validate_json(
        payload, context=None  # noqa: not actually used; for round-trip we use raw
    ) if False else None
    # 直接用 dict 验证
    import json
    d = json.loads(payload)
    assert d["total"] == 100
    assert d["limit"] == 50
    assert d["offset"] == 0
    assert d["items"][0]["code"] == "510300"


def test_sync_prices_request_codes_only():
    """SyncPricesRequestPydantic 只传 codes 时 start/end/full 可缺省。"""
    req = SyncPricesRequestPydantic(codes=["510300", "510500"])
    assert req.codes == ["510300", "510500"]
    assert req.start is None
    assert req.end is None
    assert req.full is False


def test_sync_prices_request_full_flag():
    """SyncPricesRequestPydantic full=True。"""
    req = SyncPricesRequestPydantic(
        codes=["510300"],
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        full=True,
    )
    assert req.full is True
    assert req.start == date(2024, 1, 1)


def test_backtest_request_invalid_pool_empty():
    """etf_pool 为空时 Pydantic 拒绝（min_length=1）。"""
    with pytest.raises(ValidationError):
        BacktestRequestPydantic(
            etf_pool=[],
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
            initial_cash="100000",
        )


def test_backtest_request_invalid_freq():
    """rebalance_freq 不在枚举中时 Pydantic 拒绝。"""
    with pytest.raises(ValidationError):
        BacktestRequestPydantic(
            etf_pool=["510300"],
            start=date(2024, 1, 1),
            end=date(2024, 12, 31),
            initial_cash="100000",
            rebalance_freq="daily",
        )


def test_backtest_request_initial_cash_decimal_parsing():
    """initial_cash 接受 string 形式的 Decimal。"""
    req = BacktestRequestPydantic(
        etf_pool=["510300"],
        start=date(2024, 1, 1),
        end=date(2024, 12, 31),
        initial_cash="12345.67",
    )
    assert req.initial_cash == Decimal("12345.67")
