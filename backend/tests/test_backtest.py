"""Tests for the backtest engine and task lifecycle."""
from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data_sources.fixture import FixtureCSVSource
from app.services.backtest import (
    BacktestResult,
    NAVSeries,
    run_backtest,
)
from app.services.backtest_task import (
    create_task,
    get_task,
    mark_completed,
    mark_failed,
)
from app.services.screening import DEFAULT_DEFENSIVE_ETF
from app.services.types import StrategyParams

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def _market() -> FixtureCSVSource:
    return FixtureCSVSource(FIXTURES_DIR)


def _params(**overrides) -> StrategyParams:
    defaults = dict(
        stock_sum=1,
        momentum_days=25,
        volume_lookback=5,
        volume_threshold=2.5,
        ma_short=20,
        ma_long=60,
        enable_volume_check=True,
        enable_ma_filter=True,
        defensive_etf=DEFAULT_DEFENSIVE_ETF,
        enable_industry_diverse=False,
    )
    defaults.update(overrides)
    return StrategyParams(**defaults)


# ────────────── run_backtest service ──────────────


def test_run_backtest_returns_result_with_stats() -> None:
    market = _market()
    result = run_backtest(
        start=date(2026, 1, 1),
        end=date(2026, 3, 1),
        params=_params(stock_sum=2),
        market=market,
        static_pool=[etf.stem for etf in FIXTURES_DIR.glob("*.csv")],
        themes={},
        display_names={},
    )
    assert isinstance(result, BacktestResult)
    assert isinstance(result.nav_series, NAVSeries)
    assert len(result.nav_series.dates) > 0
    assert result.stats.initial_nav == pytest.approx(1.0)
    assert result.stats.final_nav > 0
    assert result.stats.trading_days == len(result.nav_series.dates)


def test_run_backtest_daily_returns_compound_to_final() -> None:
    """final_nav should approximately equal product(1 + daily_return)."""
    market = _market()
    result = run_backtest(
        start=date(2026, 1, 1),
        end=date(2026, 3, 1),
        params=_params(stock_sum=1),
        market=market,
        static_pool=["510300.XSHG"],
        themes={},
        display_names={},
    )
    compounded = 1.0
    for r in result.nav_series.daily_returns:
        compounded *= 1 + r
    assert compounded == pytest.approx(result.stats.final_nav, rel=1e-6)


def test_run_backtest_max_drawdown_is_non_positive() -> None:
    market = _market()
    result = run_backtest(
        start=date(2026, 1, 1),
        end=date(2026, 3, 1),
        params=_params(stock_sum=1),
        market=market,
        static_pool=["510300.XSHG"],
        themes={},
        display_names={},
    )
    assert result.stats.max_drawdown <= 0


def test_run_backtest_empty_window_returns_zero_days() -> None:
    market = _market()
    result = run_backtest(
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        params=_params(),
        market=market,
        static_pool=["510300.XSHG"],
        themes={},
        display_names={},
    )
    # Window may be 0 trading days (weekend/holiday); result should still be valid
    assert result.stats.trading_days >= 0
    assert result.stats.initial_nav == pytest.approx(1.0)


# ────────────── task lifecycle ──────────────


def test_task_create_writes_running_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.backtest_task.TASK_DIR", tmp_path)
    task_id = create_task(
        start=date(2026, 1, 1),
        end=date(2026, 2, 1),
        params=_params(),
        static_pool=["510300.XSHG"],
        themes={},
        display_names={},
    )
    task = get_task(task_id)
    assert task is not None
    assert task["status"] == "running"
    assert task["request"]["start"] == "2026-01-01"


def test_task_mark_completed_updates_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.backtest_task.TASK_DIR", tmp_path)
    task_id = create_task(
        start=date(2026, 1, 1),
        end=date(2026, 2, 1),
        params=_params(),
        static_pool=["510300.XSHG"],
        themes={},
        display_names={},
    )
    fake_result = {"final_nav": 1.05, "total_return": 0.05}
    mark_completed(task_id, fake_result)
    task = get_task(task_id)
    assert task["status"] == "completed"
    assert task["result"] == fake_result


def test_task_mark_failed_updates_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.backtest_task.TASK_DIR", tmp_path)
    task_id = create_task(
        start=date(2026, 1, 1),
        end=date(2026, 2, 1),
        params=_params(),
        static_pool=["510300.XSHG"],
        themes={},
        display_names={},
    )
    mark_failed(task_id, "boom")
    task = get_task(task_id)
    assert task["status"] == "failed"
    assert task["error"] == "boom"


def test_task_get_missing_returns_none(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.backtest_task.TASK_DIR", tmp_path)
    assert get_task("nonexistent") is None


# ────────────── HTTP endpoints ──────────────


def _client_with_taskdir(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.services.backtest_task.TASK_DIR", tmp_path)
    from app import db as db_module
    from app.main import app
    from app.seed import seed_if_empty

    db_module.init_db()
    seed_if_empty()
    return TestClient(app)


def test_backtest_post_returns_task_id(monkeypatch, tmp_path: Path) -> None:
    client = _client_with_taskdir(monkeypatch, tmp_path)
    resp = client.post(
        "/api/backtest",
        json={"start": "2026-01-01", "end": "2026-02-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "task_id" in body
    assert body["status"] == "running"


def test_backtest_post_rejects_window_over_one_year(monkeypatch, tmp_path: Path) -> None:
    client = _client_with_taskdir(monkeypatch, tmp_path)
    resp = client.post(
        "/api/backtest",
        json={"start": "2024-01-01", "end": "2026-01-01"},
    )
    assert resp.status_code == 400


def test_backtest_get_returns_completed_result(monkeypatch, tmp_path: Path) -> None:
    client = _client_with_taskdir(monkeypatch, tmp_path)
    resp = client.post(
        "/api/backtest",
        json={"start": "2026-02-01", "end": "2026-03-01"},
    )
    task_id = resp.json()["task_id"]
    # Poll for completion (BackgroundTask runs sync; wait briefly)
    deadline = time.time() + 10
    while time.time() < deadline:
        resp = client.get(f"/api/backtest/{task_id}")
        if resp.json()["status"] == "completed":
            break
        time.sleep(0.1)
    body = resp.json()
    assert body["status"] == "completed"
    assert body["result"] is not None
    assert "final_nav" in body["result"]["stats"]
    assert "nav_series" in body["result"]


def test_backtest_get_missing_returns_404(monkeypatch, tmp_path: Path) -> None:
    client = _client_with_taskdir(monkeypatch, tmp_path)
    resp = client.get("/api/backtest/does-not-exist")
    assert resp.status_code == 404
