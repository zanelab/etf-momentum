"""Tests for app.data.signal — CLI entry point."""

import argparse
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.data import signal
from app.models.signal_snapshot import SignalSnapshot


# ---------------------------------------------------------------------------
# run subcommand
# ---------------------------------------------------------------------------


def test_run_happy_path(db_session, capsys) -> None:
    """run 从 DB 读 history → 算 → 写。"""
    # 准备 daily_prices: 1 只 ETF，300 天复利 0.005
    from app.models.daily_price import DailyPrice

    start = date(2023, 1, 2)
    val = Decimal("10")
    for i in range(300):
        d = start + _days(i)
        db_session.add(DailyPrice(
            code="510300", date=d,
            open=val, high=val, low=val, close=val, volume=1000,
        ))
        val = val * (Decimal("1") + Decimal("0.005"))
    db_session.commit()

    with patch("app.data.signal.SessionLocal", return_value=db_session):
        rc = signal.main([
            "run", "--date", "2024-12-31", "--pool", "510300",
        ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "wrote 1" in out
    assert db_session.query(SignalSnapshot).count() == 1


def test_run_missing_date_exits_2(capsys) -> None:
    """缺 --date → argparse 退出码 2。"""
    with pytest.raises(SystemExit) as exc:
        signal.main(["run", "--pool", "510300"])
    assert exc.value.code == 2


def test_run_missing_pool_exits_2(capsys) -> None:
    """缺 --pool → argparse 退出码 2。"""
    with pytest.raises(SystemExit) as exc:
        signal.main(["run", "--date", "2024-12-31"])
    assert exc.value.code == 2


def test_run_force_flag_overwrites(db_session, capsys) -> None:
    """--force 触发 overwrite=True；已有快照被覆盖。"""
    from app.models.daily_price import DailyPrice

    # 准备历史
    start = date(2023, 1, 2)
    val = Decimal("10")
    for i in range(300):
        d = start + _days(i)
        db_session.add(DailyPrice(
            code="510300", date=d,
            open=val, high=val, low=val, close=val, volume=1000,
        ))
        val = val * (Decimal("1") + Decimal("0.005"))
    db_session.commit()

    # 第一次 run（不带 --force）
    with patch("app.data.signal.SessionLocal", return_value=db_session):
        signal.main(["run", "--date", "2024-12-31", "--pool", "510300"])
        # 手动改 score
        snap = db_session.query(SignalSnapshot).one()
        snap.momentum_score = Decimal("0.999999")
        db_session.commit()

    # 第二次 run（带 --force）
    with patch("app.data.signal.SessionLocal", return_value=db_session):
        signal.main(["run", "--date", "2024-12-31", "--pool", "510300", "--force"])

    db_session.expire_all()
    snap = db_session.query(SignalSnapshot).one()
    # score 被重算覆盖（不再是 0.999999）
    assert snap.momentum_score != Decimal("0.999999")


# ---------------------------------------------------------------------------
# show subcommand
# ---------------------------------------------------------------------------


def test_show_no_data(db_session, capsys) -> None:
    """show 在无数据时打印友好消息，退出 0。"""
    with patch("app.data.signal.SessionLocal", return_value=db_session):
        rc = signal.main(["show", "--date", "2024-12-31"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No snapshot" in out


def test_show_happy_path(db_session, capsys) -> None:
    """show 按 rank 升序打印。"""
    db_session.add(SignalSnapshot(
        date=date(2024, 12, 31), etf_code="510300",
        momentum_score=Decimal("0.100000"), rank=1, action="BUY",
    ))
    db_session.add(SignalSnapshot(
        date=date(2024, 12, 31), etf_code="510500",
        momentum_score=Decimal("0.050000"), rank=2, action="HOLD",
    ))
    db_session.add(SignalSnapshot(
        date=date(2024, 12, 31), etf_code="510880",
        momentum_score=None, rank=None, action="WATCH",
    ))
    db_session.commit()

    with patch("app.data.signal.SessionLocal", return_value=db_session):
        rc = signal.main(["show", "--date", "2024-12-31"])
    assert rc == 0
    out = capsys.readouterr().out
    # 顺序: 510300 (rank 1) → 510500 (rank 2) → 510880 (rank None, WATCH)
    pos_300 = out.index("510300")
    pos_500 = out.index("510500")
    pos_880 = out.index("510880")
    assert pos_300 < pos_500 < pos_880


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _days(n: int):
    from datetime import timedelta
    return timedelta(days=n)
