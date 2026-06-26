"""FakeAkshareClient 单测 + Protocol 子类检查。"""

from datetime import date
from decimal import Decimal

from app.data.client import (
    AkshareClient,
    DailyPriceRow,
    EtfMasterRow,
    FakeAkshareClient,
)


def test_fake_client_returns_preset_etfs():
    etfs = [
        EtfMasterRow(code="510300", name="沪深300ETF", market="SH", category="指数"),
        EtfMasterRow(code="510500", name="中证500ETF", market="SH", category="指数"),
    ]
    client = FakeAkshareClient(etfs=etfs)
    assert client.list_etfs() == etfs


def test_fake_client_filters_by_date_range():
    rows = [
        DailyPriceRow(date=date(2024, 1, 1), open=Decimal("1"), high=Decimal("1"),
                      low=Decimal("1"), close=Decimal("1"), volume=1),
        DailyPriceRow(date=date(2024, 1, 2), open=Decimal("2"), high=Decimal("2"),
                      low=Decimal("2"), close=Decimal("2"), volume=2),
        DailyPriceRow(date=date(2024, 1, 3), open=Decimal("3"), high=Decimal("3"),
                      low=Decimal("3"), close=Decimal("3"), volume=3),
    ]
    client = FakeAkshareClient(prices={"510300": rows})
    result = client.fetch_etf_hist("510300", date(2024, 1, 2), date(2024, 1, 2))
    assert len(result) == 1
    assert result[0].date == date(2024, 1, 2)


def test_fake_client_returns_empty_for_unknown_code():
    client = FakeAkshareClient()
    assert client.fetch_etf_hist("999999", date(2024, 1, 1), date(2024, 1, 1)) == []


def test_fake_client_satisfies_protocol():
    """FakeAkshareClient 应该是 AkshareClient Protocol 的合法实现。"""
    client: AkshareClient = FakeAkshareClient()
    assert hasattr(client, "list_etfs")
    assert hasattr(client, "fetch_etf_hist")
