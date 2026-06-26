"""sync CLI 冒烟测试。"""

import io
import json
import sys
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal

import pytest

from app.data.client import DailyPriceRow, EtfMasterRow, FakeAkshareClient
from app.data.sync import build_parser, cmd_etfs, cmd_prices, main
from app.db.session import SessionLocal


@pytest.fixture()
def stub_akshare(monkeypatch):
    """用 fake client 替换默认 HttpClient，测试无需网络。"""
    fake = FakeAkshareClient(
        etfs=[EtfMasterRow(code="510300", name="沪深300ETF", market="SH", category="指数")],
        prices={"510300": [
            DailyPriceRow(date=date(2024, 1, d), open=Decimal("1"),
                          high=Decimal("1"), low=Decimal("1"),
                          close=Decimal("1"), volume=1)
            for d in (1, 2)
        ]},
    )

    def _factory():
        return fake

    monkeypatch.setattr("app.data.sync._build_client", _factory)
    return fake


def test_parser_has_etfs_and_prices_subcommands():
    parser = build_parser()
    # etfs
    args = parser.parse_args(["etfs"])
    assert args.command == "etfs"
    # prices
    args = parser.parse_args([
        "prices", "--codes", "510300,510500",
        "--start", "2024-01-01", "--end", "2024-12-31", "--full",
    ])
    assert args.command == "prices"
    assert args.codes == "510300,510500"
    assert args.start == "2024-01-01"
    assert args.end == "2024-12-31"
    assert args.full is True


def test_cmd_etfs_prints_summary(stub_akshare, db_session, monkeypatch):
    monkeypatch.setattr("app.data.sync.SessionLocal", lambda: db_session)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cmd_etfs(None)
    assert code == 0
    assert json.loads(buf.getvalue()) == {"fetched": 1, "upserted": 1}


def test_cmd_prices_with_explicit_dates(stub_akshare, db_session, monkeypatch):
    monkeypatch.setattr("app.data.sync.SessionLocal", lambda: db_session)
    parser = build_parser()
    args = parser.parse_args([
        "prices", "--codes", "510300",
        "--start", "2024-01-01", "--end", "2024-01-02",
    ])
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cmd_prices(args)
    assert code == 0
    summary = json.loads(buf.getvalue())
    assert summary["succeeded"] == 1
    assert summary["rows_written"] == 2


def test_main_entry_with_etfs_subcommand(stub_akshare, db_session, monkeypatch):
    monkeypatch.setattr("app.data.sync.SessionLocal", lambda: db_session)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["etfs"])
    assert code == 0
    assert "fetched" in buf.getvalue()
