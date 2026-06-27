"""Tests for app.data.seed_demo — demo data loader."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.data.seed_demo import (
    DEFAULT_FIXTURE_PATH,
    SUPPORTED_VERSION,
    _parse_signal_row,
    load_demo_data,
)
from app.db.base import Base
# Import all models so Base.metadata includes EtfPool + EtfPoolMember tables.
from app.models import (  # noqa: F401
    BacktestRun,
    DailyPrice,
    ETF,
    EtfPool,
    EtfPoolMember,
    SignalSnapshot,
)


FIXTURE_PATH = DEFAULT_FIXTURE_PATH


@pytest.fixture()
def engine():
    """每个测试一个全新的内存 SQLite engine（含 EtfPool / EtfPoolMember 表）。"""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Session:
    """隔离的 Session 实例。"""
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Fixture-level sanity (real fixture shipped in repo)
# ---------------------------------------------------------------------------


class TestFixtureIntegrity:
    """Verify the shipped demo_data.json satisfies its own contract."""

    def test_fixture_exists(self):
        assert FIXTURE_PATH.exists(), f"fixture missing: {FIXTURE_PATH}"

    def test_fixture_version_is_supported(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert raw["version"] == SUPPORTED_VERSION

    def test_fixture_has_required_top_level_keys(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for key in ("version", "generated_at", "source_note", "etfs", "daily_prices", "signal_snapshot", "pool"):
            assert key in raw, f"missing top-level key: {key}"

    def test_fixture_contains_15_etfs(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        assert len(raw["etfs"]) == 15

    def test_fixture_etfs_have_required_fields(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for etf in raw["etfs"]:
            assert {"code", "name", "market", "category"} <= set(etf.keys())

    def test_fixture_daily_prices_have_minimum_length(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for code, rows in raw["daily_prices"].items():
            assert len(rows) >= 700, f"{code} only has {len(rows)} rows"

    def test_fixture_daily_prices_have_required_fields(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        sample = next(iter(raw["daily_prices"].values()))[0]
        assert {"date", "open", "high", "low", "close", "volume"} <= set(sample.keys())

    def test_fixture_signal_snapshot_covers_buy_and_hold(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        rows = raw["signal_snapshot"]["rows"]
        actions = {r["action"] for r in rows}
        assert "BUY" in actions
        assert "HOLD" in actions

    def test_fixture_pool_is_宽基三杰(self):
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        pool = raw["pool"]
        assert pool["name"] == "宽基三杰"
        assert set(pool["etf_codes"]) == {"510300", "510500", "159915"}

    def test_fixture_file_size_under_5mb(self):
        size = FIXTURE_PATH.stat().st_size
        assert size < 5 * 1024 * 1024, f"fixture too large: {size} bytes"


# ---------------------------------------------------------------------------
# _parse_signal_row
# ---------------------------------------------------------------------------


class TestParseSignalRow:
    def test_basic(self):
        d = {"etf_code": "510300", "momentum_score": "0.123456", "rank": 1, "action": "BUY"}
        row = _parse_signal_row(d)
        assert row.etf_code == "510300"
        assert row.momentum_score == Decimal("0.123456")
        assert row.rank == 1
        assert row.action == "BUY"

    def test_watch_row_with_null_score(self):
        d = {"etf_code": "512760", "momentum_score": None, "rank": None, "action": "WATCH"}
        row = _parse_signal_row(d)
        assert row.momentum_score is None
        assert row.rank is None
        assert row.action == "WATCH"


# ---------------------------------------------------------------------------
# load_demo_data
# ---------------------------------------------------------------------------


class TestLoadDemoData:
    def test_first_load_inserts_everything(self, session):
        before_etfs = session.execute(text("SELECT COUNT(*) FROM etfs")).scalar()
        before_prices = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()

        summary = load_demo_data(session, FIXTURE_PATH)

        etfs_now = session.execute(text("SELECT COUNT(*) FROM etfs")).scalar()
        prices_now = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
        signals_now = session.execute(text("SELECT COUNT(*) FROM signal_snapshots")).scalar()
        pools_now = session.execute(text("SELECT COUNT(*) FROM etf_pools")).scalar()

        # Demo adds ≥ 15 etfs and ≥ ~11000 prices
        assert summary["etfs"] == 15
        assert summary["daily_prices"] >= 15 * 700
        assert summary["signals"] == 15
        assert summary["pool"] == "宽基三杰"

        assert etfs_now - before_etfs == 15
        assert prices_now - before_prices >= 15 * 700
        assert signals_now == 15
        assert pools_now >= 1

    def test_second_load_is_idempotent(self, session):
        load_demo_data(session, FIXTURE_PATH)
        etfs_after_first = session.execute(text("SELECT COUNT(*) FROM etfs")).scalar()
        prices_after_first = session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
        signals_after_first = session.execute(text("SELECT COUNT(*) FROM signal_snapshots")).scalar()
        pools_after_first = session.execute(text("SELECT COUNT(*) FROM etf_pools")).scalar()

        # 第二次执行 — 行数不应增长
        load_demo_data(session, FIXTURE_PATH)

        assert session.execute(text("SELECT COUNT(*) FROM etfs")).scalar() == etfs_after_first
        assert session.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar() == prices_after_first
        assert session.execute(text("SELECT COUNT(*) FROM signal_snapshots")).scalar() == signals_after_first
        assert session.execute(text("SELECT COUNT(*) FROM etf_pools")).scalar() == pools_after_first

    def test_missing_fixture_raises(self, session):
        with pytest.raises(FileNotFoundError):
            load_demo_data(session, Path("/nonexistent/demo_data.json"))

    def test_unsupported_version_raises(self, session, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"version": 999, "etfs": [], "daily_prices": {}, "signal_snapshot": {}, "pool": {}}))
        with pytest.raises(ValueError, match="Unsupported demo data version"):
            load_demo_data(session, bad)

    def test_signal_snapshot_dates_match(self, session):
        load_demo_data(session, FIXTURE_PATH)
        rows = session.execute(text("SELECT DISTINCT date FROM signal_snapshots")).scalars().all()
        assert len(rows) == 1  # snapshot 只覆盖 1 天
        # SQLite Date column stores ISO strings; coerce to date for comparison
        assert date.fromisoformat(rows[0]) >= date(2024, 1, 1)

    def test_pool_has_3_members(self, session):
        load_demo_data(session, FIXTURE_PATH)
        pool_name = "宽基三杰"
        result = session.execute(
            text("SELECT m.etf_code FROM etf_pool_members m "
                 "JOIN etf_pools p ON p.id = m.pool_id "
                 "WHERE p.name = :name ORDER BY m.position"),
            {"name": pool_name},
        ).scalars().all()
        assert set(result) == {"510300", "510500", "159915"}


# ---------------------------------------------------------------------------
# CLI main() — exit codes
# ---------------------------------------------------------------------------


class TestCli:
    def test_main_success(self, capsys):
        from app.data.seed_demo import main
        # Use default fixture (which is what main does); session.db may have data already.
        # The point is the CLI doesn't crash and prints summary.
        rc = main(["--fixture", str(FIXTURE_PATH)])
        out = capsys.readouterr().out
        assert "loaded:" in out
        # rc may be 0 (success) — even with pre-existing data, idempotent
        assert rc == 0

    def test_main_missing_fixture(self, capsys):
        from app.data.seed_demo import main
        rc = main(["--fixture", "/nonexistent/path.json"])
        assert rc == 2
        err = capsys.readouterr().err
        assert "fixture not found" in err