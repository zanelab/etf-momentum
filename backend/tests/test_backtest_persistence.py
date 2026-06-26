"""Tests for app.backtest.persistence — save_backtest_run."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.backtest.engine import (
    BacktestParams,
    BacktestResult,
    RebalanceFrequency,
)
from app.backtest.persistence import save_backtest_run


@pytest.fixture
def params():
    return BacktestParams(
        etf_pool=["510300", "510500"],
        start=date(2024, 1, 1),
        end=date(2024, 6, 30),
        initial_cash=Decimal("100000"),
        lookback=252,
        skip=21,
        top_n=2,
        rebalance_freq=RebalanceFrequency.MONTHLY,
    )


@pytest.fixture
def result():
    return BacktestResult(
        nav_series=[
            (date(2024, 1, 1), Decimal("100000")),
            (date(2024, 6, 30), Decimal("120000")),
        ],
        rebalance_log=[],
        metrics={
            "total_return": Decimal("0.20"),
            "annualized_return": Decimal("0.40"),
            "max_drawdown": Decimal("0.10"),
            "sharpe_ratio": Decimal("1.5"),
        },
    )


class TestSaveBacktestRun:
    def test_writes_orm_row(self, params, result):
        session = MagicMock()
        run = save_backtest_run(session, params, result)
        # session.add called once with a BacktestRun
        assert session.add.call_count == 1
        added = session.add.call_args[0][0]
        assert added.__class__.__name__ == "BacktestRun"
        assert added.etf_pool == ["510300", "510500"]
        assert added.momentum_window == 252
        assert added.rebalance_freq == "monthly"
        assert added.start_date == date(2024, 1, 1)
        assert added.end_date == date(2024, 6, 30)
        # commit and refresh called
        session.commit.assert_called_once()
        session.refresh.assert_called_once_with(added)

    def test_metrics_contains_required_keys(self, params, result):
        session = MagicMock()
        save_backtest_run(session, params, result)
        added = session.add.call_args[0][0]
        m = added.metrics
        assert m["total_return"] == "0.20"
        assert m["annualized_return"] == "0.40"
        assert m["max_drawdown"] == "0.10"
        assert m["sharpe_ratio"] == "1.5"
        assert m["final_nav"] == "120000"

    def test_metrics_contains_params_snapshot(self, params, result):
        session = MagicMock()
        save_backtest_run(session, params, result)
        added = session.add.call_args[0][0]
        snap = added.metrics["params"]
        assert snap["lookback"] == 252
        assert snap["skip"] == 21
        assert snap["top_n"] == 2
        assert snap["initial_cash"] == "100000"
        assert snap["final_nav"] == "120000"

    def test_empty_nav_series(self, params):
        session = MagicMock()
        empty_result = BacktestResult(
            nav_series=[],
            rebalance_log=[],
            metrics={
                "total_return": Decimal("0"),
                "annualized_return": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "sharpe_ratio": None,
            },
        )
        save_backtest_run(session, params, empty_result)
        added = session.add.call_args[0][0]
        # final_nav should be None at top level + params snapshot
        assert added.metrics["final_nav"] is None
        assert added.metrics["params"]["final_nav"] is None
        # None metrics should serialize as None
        assert added.metrics["sharpe_ratio"] is None

    def test_propagates_commit_exception(self, params, result):
        session = MagicMock()
        session.commit.side_effect = IntegrityError("stmt", "params", Exception("orig"))
        with pytest.raises(IntegrityError):
            save_backtest_run(session, params, result)

    def test_quarterly_freq_serialized(self, params, result):
        params = BacktestParams(
            etf_pool=["a"],
            start=date(2024, 1, 1),
            end=date(2024, 6, 30),
            initial_cash=Decimal("100000"),
            rebalance_freq=RebalanceFrequency.QUARTERLY,
        )
        session = MagicMock()
        save_backtest_run(session, params, result)
        added = session.add.call_args[0][0]
        assert added.rebalance_freq == "quarterly"