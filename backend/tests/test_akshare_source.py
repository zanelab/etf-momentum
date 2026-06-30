"""Tests for AkShareSource — uses a fake akshare module injected via sys.modules."""
from datetime import date, datetime
from types import ModuleType

import pandas as pd
import pytest

from app.data_sources.akshare_source import AkShareSource


def _install_fake_akshare(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Inject a minimal fake akshare into sys.modules so the import in
    AkShareSource.__init__ resolves without the real library."""
    fake = ModuleType("akshare")
    fake.fund_etf_hist_em = lambda *a, **kw: pd.DataFrame()  # default
    fake.fund_etf_spot_em = lambda *a, **kw: pd.DataFrame()
    monkeypatch.setitem(__import__("sys").modules, "akshare", fake)
    return fake


def test_akshare_import_error_when_package_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """If akshare is not importable, AkShareSource() must raise ImportError."""
    # Block the fake install: don't inject, and prevent real import
    import builtins
    import sys

    real_import = builtins.__import__

    def _blocked(name, *args, **kwargs):
        if name == "akshare" or name.startswith("akshare."):
            raise ImportError("akshare not installed (test)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    monkeypatch.delitem(sys.modules, "akshare", raising=False)
    with pytest.raises(ImportError, match="akshare"):
        AkShareSource()


def test_akshare_history_maps_chinese_columns_to_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """akshare returns `日期/开盘/收盘/...`; AkShareSource must rename to
    `date/open/close/...` and index by date."""
    fake = _install_fake_akshare(monkeypatch)

    def fake_hist_em(symbol: str, period: str, start_date: str, end_date: str, adjust: str):
        return pd.DataFrame(
            {
                "日期": ["2026-01-13", "2026-01-14", "2026-01-15"],
                "开盘": [3.85, 3.88, 3.90],
                "收盘": [3.87, 3.89, 3.92],
                "最高": [3.88, 3.90, 3.95],
                "最低": [3.84, 3.87, 3.88],
                "成交量": [1_000_000.0, 1_100_000.0, 1_200_000.0],
                "成交额": [3_870_000.0, 4_279_000.0, 4_704_000.0],
            }
        )

    fake.fund_etf_hist_em = fake_hist_em
    src = AkShareSource()
    df = src.history("510300", date(2026, 1, 13), date(2026, 1, 15))
    assert list(df.columns) == ["open", "close", "high", "low", "volume", "money"]
    assert df.index.name == "date"
    assert len(df) == 3
    assert df.iloc[-1]["close"] == 3.92


def test_akshare_history_filters_by_field_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install_fake_akshare(monkeypatch)
    fake.fund_etf_hist_em = lambda *a, **kw: pd.DataFrame(
        {
            "日期": ["2026-01-13", "2026-01-14"],
            "开盘": [3.85, 3.88],
            "收盘": [3.87, 3.89],
            "最高": [3.88, 3.90],
            "最低": [3.84, 3.87],
            "成交量": [1_000_000.0, 1_100_000.0],
            "成交额": [3_870_000.0, 4_279_000.0],
        }
    )
    src = AkShareSource()
    df = src.history("510300", date(2026, 1, 13), date(2026, 1, 14), fields=["close"])
    assert list(df.columns) == ["close"]


def test_akshare_snapshot_returns_last_bar_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install_fake_akshare(monkeypatch)
    fake.fund_etf_hist_em = lambda *a, **kw: pd.DataFrame(
        {
            "日期": ["2026-01-13", "2026-01-14", "2026-01-15"],
            "开盘": [3.85, 3.88, 3.90],
            "收盘": [3.87, 3.89, 3.92],
            "最高": [3.88, 3.90, 3.95],
            "最低": [3.84, 3.87, 3.88],
            "成交量": [1_000_000.0, 1_100_000.0, 1_200_000.0],
            "成交额": [3_870_000.0, 4_279_000.0, 4_704_000.0],
        }
    )
    src = AkShareSource()
    snap = src.snapshot("510300", datetime(2026, 1, 15, 14, 0))
    assert snap["last_price"] == 3.92
    assert snap["volume"] == 1_200_000.0
    assert snap["money"] == 4_704_000.0


def test_akshare_all_etfs_returns_code_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """fund_etf_spot_em() returns columns 代码/名称 (East Money); codes MUST be
    normalized to canonical form (XXXXXX.XSHG/XSHE)."""
    fake = _install_fake_akshare(monkeypatch)
    fake.fund_etf_spot_em = lambda: pd.DataFrame(
        {
            "代码": ["510300", "510500", "159915"],
            "名称": ["沪深300ETF", "中证500ETF", "创业板ETF"],
        }
    )
    src = AkShareSource()
    codes = src.all_etfs(date(2026, 1, 15))
    assert codes == ["510300.XSHG", "510500.XSHG", "159915.XSHE"]


def test_akshare_all_etf_entries_returns_normalized_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """all_etf_entries must return (canonical_code, name) pairs even when
    akshare returns bare 6-digit codes."""
    fake = _install_fake_akshare(monkeypatch)
    fake.fund_etf_spot_em = lambda: pd.DataFrame(
        {
            "代码": ["510300", "510500", "159915", "000001"],
            "名称": ["沪深300ETF", "中证500ETF", "创业板ETF", "测试"],
        }
    )
    src = AkShareSource()
    entries = src.all_etf_entries(date(2026, 1, 15))
    assert entries == [
        ("510300.XSHG", "沪深300ETF"),
        ("510500.XSHG", "中证500ETF"),
        ("159915.XSHE", "创业板ETF"),
        ("000001.XSHE", "测试"),
    ]


def test_akshare_raises_when_no_data_and_all_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When akshare fails after all retries and no fallback exists, raise DataNotFoundError."""
    fake = _install_fake_akshare(monkeypatch)

    def always_empty(*a, **kw):
        return pd.DataFrame()  # empty = "no data"

    fake.fund_etf_hist_em = always_empty
    src = AkShareSource(max_retries=0, initial_delay=0.0)
    from app.data_sources.base import DataNotFoundError

    with pytest.raises(DataNotFoundError):
        src.history("510300", date(2026, 1, 13), date(2026, 1, 14))
