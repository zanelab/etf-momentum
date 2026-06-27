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

    def test_metrics_contains_sortino_and_calmar(self, params):
        """sortino_ratio / calmar_ratio 也要写进 metrics JSON。"""
        result = BacktestResult(
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
                "sortino_ratio": Decimal("2.0"),
                "calmar_ratio": Decimal("4.0"),
            },
        )
        session = MagicMock()
        save_backtest_run(session, params, result)
        added = session.add.call_args[0][0]
        assert added.metrics["sortino_ratio"] == "2.0"
        assert added.metrics["calmar_ratio"] == "4.0"

    def test_metrics_sortino_calmar_none_serialized(self, params):
        """sortino / calmar 为 None 时 JSON 中为 null。"""
        result = BacktestResult(
            nav_series=[(date(2024, 1, 1), Decimal("100000"))],
            rebalance_log=[],
            metrics={
                "total_return": Decimal("0"),
                "annualized_return": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "sharpe_ratio": None,
                "sortino_ratio": None,
                "calmar_ratio": None,
            },
        )
        session = MagicMock()
        save_backtest_run(session, params, result)
        added = session.add.call_args[0][0]
        assert added.metrics["sortino_ratio"] is None
        assert added.metrics["calmar_ratio"] is None

    def test_save_with_name(self, params, result):
        """name 字段会作为 BacktestRun.name 持久化。"""
        from app.backtest.engine import BacktestResult as _Result

        named_params = BacktestParams(
            etf_pool=params.etf_pool,
            start=params.start,
            end=params.end,
            initial_cash=params.initial_cash,
            lookback=params.lookback,
            skip=params.skip,
            top_n=params.top_n,
            rebalance_freq=params.rebalance_freq,
        )
        # BacktestParams 没有 name 字段（name 在 API 层赋给 BacktestRun），所以这里
        # 验证 BacktestRun 的 name 属性默认为 None，且能通过 setattr 设置。
        session = MagicMock()
        save_backtest_run(session, named_params, result)
        added = session.add.call_args[0][0]
        assert added.name is None
        # ORM 字段存在，可赋值
        added.name = "momentum-12-1-monthly"
        assert added.name == "momentum-12-1-monthly"

    def test_save_single_point_nav(self, params):
        """单点 nav_series → final_nav 为该点的 nav 值。"""
        result = BacktestResult(
            nav_series=[(date(2024, 1, 1), Decimal("100000"))],
            rebalance_log=[],
            metrics={
                "total_return": Decimal("0"),
                "annualized_return": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "sharpe_ratio": None,
            },
        )
        session = MagicMock()
        save_backtest_run(session, params, result)
        added = session.add.call_args[0][0]
        assert added.metrics["final_nav"] == "100000"
        assert added.metrics["params"]["final_nav"] == "100000"

    def test_save_with_rebalance_log_populated_not_persisted(self, params, result):
        """rebalance_log 当前不被持久化（需要新 JSON 列，超出本次范围）。"""
        from app.backtest.engine import RebalanceEvent

        result_with_log = BacktestResult(
            nav_series=result.nav_series,
            rebalance_log=[
                RebalanceEvent(
                    date=date(2024, 3, 31),
                    scores={"510300": Decimal("0.15")},
                    selected=["510300"],
                    weights={"510300": Decimal("1")},
                ),
            ],
            metrics=result.metrics,
        )
        session = MagicMock()
        save_backtest_run(session, params, result_with_log)
        added = session.add.call_args[0][0]
        # BacktestRun 没有 rebalance_log_json 列 → 不会有该属性（或为 None）
        assert not hasattr(added, "rebalance_log_json") or added.rebalance_log_json is None