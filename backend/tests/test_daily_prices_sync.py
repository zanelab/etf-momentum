"""sync_daily_prices 集成测试。"""

from datetime import date
from decimal import Decimal

from app.data.client import DailyPriceRow, FakeAkshareClient
from app.data.daily_prices import sync_daily_prices
from app.models.daily_price import DailyPrice


def _row(d: date, close: str = "4.0") -> DailyPriceRow:
    return DailyPriceRow(
        date=d, open=Decimal(close), high=Decimal(close),
        low=Decimal(close), close=Decimal(close), volume=100,
    )


def test_sync_inserts_new_prices(db_session):
    client = FakeAkshareClient(prices={
        "510300": [_row(date(2024, 1, d)) for d in (1, 2, 3)],
    })
    result = sync_daily_prices(
        db_session, client, ["510300"],
        start=date(2024, 1, 1), end=date(2024, 1, 3),
    )

    assert result["fetched"] == 1
    assert result["succeeded"] == 1
    assert result["failed"] == 0
    assert result["rows_written"] == 3
    assert db_session.query(DailyPrice).count() == 3


def test_sync_upserts_existing_prices(db_session):
    client1 = FakeAkshareClient(prices={
        "510300": [_row(date(2024, 1, 1), "4.0")],
    })
    sync_daily_prices(db_session, client1, ["510300"],
                      start=date(2024, 1, 1), end=date(2024, 1, 1))

    client2 = FakeAkshareClient(prices={
        "510300": [_row(date(2024, 1, 1), "9.9")],
    })
    result = sync_daily_prices(db_session, client2, ["510300"],
                               start=date(2024, 1, 1), end=date(2024, 1, 1))

    assert result["rows_written"] == 1
    assert db_session.query(DailyPrice).count() == 1
    assert db_session.query(DailyPrice).filter_by(code="510300").one().close == Decimal("9.9")


def test_sync_continues_after_one_failure(db_session, caplog):
    """一只失败不应阻塞下一只。"""
    class FlakyClient(FakeAkshareClient):
        def fetch_etf_hist(self, code, start, end):
            if code == "510300":
                raise ValueError("network error")
            return super().fetch_etf_hist(code, start, end)

    client = FlakyClient(prices={
        "510500": [_row(date(2024, 1, 1))],
    })
    result = sync_daily_prices(
        db_session, client, ["510300", "510500"],
        start=date(2024, 1, 1), end=date(2024, 1, 1),
    )

    assert result["fetched"] == 2
    assert result["succeeded"] == 1
    assert result["failed"] == 1
    assert result["rows_written"] == 1
    assert db_session.query(DailyPrice).count() == 1
    assert "510300" in caplog.text or "sync daily prices" in caplog.text


def test_full_mode_fetches_all_history(db_session):
    """full=True 时无论 DB 是否有数据都从 akshare 起点拉。"""
    # 预先插入 2024-01-05 的数据
    db_session.add(DailyPrice(
        code="510300", date=date(2024, 1, 5),
        open=Decimal("1"), high=Decimal("1"), low=Decimal("1"),
        close=Decimal("1"), volume=1,
    ))
    db_session.commit()

    # fake 返回 2024-01-01 到 2024-01-10
    client = FakeAkshareClient(prices={
        "510300": [_row(date(2024, 1, d)) for d in range(1, 11)],
    })
    result = sync_daily_prices(
        db_session, client, ["510300"],
        start=None, end=date(2024, 1, 10), full=True,
    )

    assert result["rows_written"] == 10
    assert db_session.query(DailyPrice).filter_by(code="510300").count() == 10


def test_incremental_default_uses_last_synced_date(db_session):
    """start=None 且 full=False 时从 DB 最后日期+1 开始拉。"""
    # 预存到 2024-01-05
    db_session.add_all([
        DailyPrice(code="510300", date=date(2024, 1, d),
                   open=Decimal("1"), high=Decimal("1"),
                   low=Decimal("1"), close=Decimal("1"), volume=1)
        for d in range(1, 6)
    ])
    db_session.commit()

    captured: dict = {}

    class CapturingClient(FakeAkshareClient):
        def fetch_etf_hist(self, code, start, end):
            captured["start"] = start
            captured["end"] = end
            return []

    client = CapturingClient()
    sync_daily_prices(db_session, client, ["510300"],
                      end=date(2024, 1, 31))

    assert captured["start"] == date(2024, 1, 6)
    assert captured["end"] == date(2024, 1, 31)
