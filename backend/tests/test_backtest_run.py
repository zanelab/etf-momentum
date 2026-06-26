"""BacktestRun model CRUD 测试。"""

from datetime import date

from app.models.backtest_run import BacktestRun


def test_insert_backtest_run_with_metrics(db_session):
    metrics = {
        "annual_return": 0.123,
        "sharpe": 1.5,
        "max_drawdown": -0.18,
    }
    run = BacktestRun(
        name="test-run",
        etf_pool=["510300", "510500"],
        momentum_window=12,
        rebalance_freq="monthly",
        start_date=date(2020, 1, 1),
        end_date=date(2025, 12, 31),
        metrics=metrics,
    )
    db_session.add(run)
    db_session.commit()

    assert run.id is not None
    db_session.refresh(run)
    assert run.metrics == metrics
    assert run.etf_pool == ["510300", "510500"]
