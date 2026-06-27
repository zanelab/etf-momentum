"""FakeAkshareClient 单测 + Protocol 子类检查。"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.data.client import (
    AkshareClient,
    DailyPriceRow,
    EtfMasterRow,
    FakeAkshareClient,
    _coerce_date,
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


# ---------------------------------------------------------------------------
# _coerce_date：akshare 在不同 pandas 版本下日期列可能是 str / Timestamp / datetime / date
# ---------------------------------------------------------------------------


class TestCoerceDate:
    def test_date_passthrough(self):
        d = date(2024, 1, 15)
        assert _coerce_date(d) is d

    def test_datetime_to_date(self):
        assert _coerce_date(datetime(2024, 1, 15, 9, 30)) == date(2024, 1, 15)

    def test_string_isoformat(self):
        """akshare 实测 `日期` 列 dtype=str → 必须能正确解析。"""
        assert _coerce_date("2024-01-15") == date(2024, 1, 15)

    def test_pandas_timestamp_via_datetime_branch(self):
        """pd.Timestamp 是 datetime 子类，走 datetime 分支。"""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        ts = pd.Timestamp("2024-01-15")
        assert _coerce_date(ts) == date(2024, 1, 15)

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="unsupported date value"):
            _coerce_date(12345)

    def test_unsupported_string_format_raises(self):
        """非 ISO 格式的字符串应该让 fromisoformat 抛出，不是默默通过。"""
        with pytest.raises(ValueError):
            _coerce_date("2024/01/15")


# ---------------------------------------------------------------------------
# AkshareHttpClient.fetch_etf_hist：模拟 akshare 返回 dtype=str 日期列（真实场景）
# ---------------------------------------------------------------------------


class TestHttpClientFetchEtfHist:
    """akshare `fund_etf_hist_em` 实测返回 `日期` 列 dtype=str。"""

    def test_fetch_etf_hist_handles_str_date_column(self, monkeypatch):
        """模拟 akshare 返回的 DataFrame：`日期` 列 dtype=str。回归：以前会因为 hasattr 检查失败把字符串当 date 传给 SQLAlchemy。"""
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")

        from app.data.client import AkshareHttpClient

        df = pd.DataFrame({
            "日期": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "开盘": [Decimal("1.0"), Decimal("1.1"), Decimal("1.2")],
            "最高": [Decimal("1.0"), Decimal("1.1"), Decimal("1.2")],
            "最低": [Decimal("1.0"), Decimal("1.1"), Decimal("1.2")],
            "收盘": [Decimal("1.0"), Decimal("1.1"), Decimal("1.2")],
            "成交量": [100, 200, 300],
        })

        # 替换 akshare 模块
        class FakeAk:
            @staticmethod
            def fund_etf_hist_em(**kwargs):
                return df

        import sys
        monkeypatch.setitem(sys.modules, "akshare", FakeAk)

        client = AkshareHttpClient()
        rows = client.fetch_etf_hist("510300", date(2024, 1, 1), date(2024, 12, 31))

        assert len(rows) == 3
        for r in rows:
            assert isinstance(r.date, date), f"date should be date, got {type(r.date)}"
        assert rows[0].date == date(2024, 1, 2)
        assert rows[2].date == date(2024, 1, 4)
