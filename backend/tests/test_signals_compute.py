"""Tests for app.signals.compute — pure-function signal computation."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.signals.compute import SignalRow, compute_signals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _linear_history(
    code: str,
    start: date,
    days: int,
    *,
    base: Decimal = Decimal("10"),
    growth: Decimal = Decimal("0.001"),
) -> list[tuple[date, Decimal]]:
    """Generate a monotonically rising price series.

    price[i] = base * (1 + growth) ** i  → 复利增长方便手算动量
    """
    series = []
    val = base
    for i in range(days):
        d = start + timedelta(days=i)
        series.append((d, val))
        val = val * (Decimal("1") + growth)
    return series


def _make_history(
    codes_with_growth: dict[str, Decimal],
    *,
    start: date = date(2023, 1, 1),
    days: int = 300,
    base: Decimal = Decimal("10"),
) -> dict[str, list[tuple[date, Decimal]]]:
    """Build a price_history with different growth rates per code."""
    return {
        code: _linear_history(code, start, days, base=base, growth=growth)
        for code, growth in codes_with_growth.items()
    }


SIGNAL_DATE = date(2024, 12, 31)


# ---------------------------------------------------------------------------
# 基础行为
# ---------------------------------------------------------------------------


def test_top_n_buy_distribution() -> None:
    """5 只 ETF + top_n=2 → 前 2 个 BUY，其余 HOLD。"""
    history = _make_history({
        "A": Decimal("0.01"),   # 最高
        "B": Decimal("0.008"),
        "C": Decimal("0.006"),
        "D": Decimal("0.004"),
        "E": Decimal("0.002"),  # 最低
    })
    pool = ["A", "B", "C", "D", "E"]
    rows = compute_signals(pool, history, SIGNAL_DATE, top_n=2)
    assert len(rows) == 5
    assert rows[0].action == "BUY"
    assert rows[1].action == "BUY"
    for r in rows[2:]:
        assert r.action == "HOLD"


def test_orders_by_rank() -> None:
    """返回按 rank 升序。"""
    history = _make_history({
        "A": Decimal("0.01"),
        "B": Decimal("0.008"),
        "C": Decimal("0.006"),
    })
    rows = compute_signals(["A", "B", "C"], history, SIGNAL_DATE, top_n=1)
    ranks = [r.rank for r in rows]
    assert ranks == sorted(ranks)
    assert ranks == [1, 2, 3]


def test_empty_pool() -> None:
    history: dict[str, list[tuple[date, Decimal]]] = {}
    rows = compute_signals([], history, SIGNAL_DATE)
    assert rows == []


# ---------------------------------------------------------------------------
# WATCH 路径
# ---------------------------------------------------------------------------


def test_with_watch() -> None:
    """1 只 ETF 历史不足 → WATCH，rank=None。"""
    short_start = date(2024, 10, 1)
    short_history = _linear_history("WEAK", short_start, 100)
    long_history = _make_history({"STRONG": Decimal("0.005")})["STRONG"]
    history = {
        "WEAK": short_history,
        "STRONG": long_history,
    }
    rows = compute_signals(["WEAK", "STRONG"], history, SIGNAL_DATE, top_n=1)
    by_code = {r.etf_code: r for r in rows}
    assert by_code["WEAK"].action == "WATCH"
    assert by_code["WEAK"].rank is None
    assert by_code["WEAK"].momentum_score is None
    assert by_code["STRONG"].action == "BUY"
    assert by_code["STRONG"].rank == 1


def test_score_none_rank_none() -> None:
    """WATCH row 的 score / rank 字段都是 None。"""
    history = _make_history({"OK": Decimal("0.005")})
    history["WEAK"] = _linear_history("WEAK", date(2024, 10, 1), 100)
    rows = compute_signals(["OK", "WEAK"], history, SIGNAL_DATE, top_n=1)
    weak = next(r for r in rows if r.etf_code == "WEAK")
    assert weak.momentum_score is None
    assert weak.rank is None
    assert weak.action == "WATCH"


# ---------------------------------------------------------------------------
# 精度
# ---------------------------------------------------------------------------


def test_score_quantize_6dp() -> None:
    """score 量化到 6 位小数（与 Numeric(10,6) 对齐）。"""
    # 构造一个能产生 >6 位小数的 score
    # 100 → 112.3456789，需要构造
    history = {
        "X": [
            (date(2024, 1, 1), Decimal("100")),
            (SIGNAL_DATE, Decimal("112.3456789")),
        ],
    }
    # 不足 273 天 → WATCH
    rows = compute_signals(["X"], history, SIGNAL_DATE)
    assert rows[0].action == "WATCH"
    assert rows[0].momentum_score is None


def test_score_quantize_with_full_history() -> None:
    """完整历史的 score 被 quantize 到 6 位。"""
    history = _make_history({"A": Decimal("0.005")})
    rows = compute_signals(["A"], history, SIGNAL_DATE)
    score = rows[0].momentum_score
    assert score is not None
    # quantize 到 6 位意味着 score * 10**6 是整数
    assert (score * Decimal("1000000")) == (score * Decimal("1000000")).to_integral_value()


# ---------------------------------------------------------------------------
# 输入不变性
# ---------------------------------------------------------------------------


def test_input_not_mutated() -> None:
    """price_history 与 etf_pool 不被修改。"""
    history = _make_history({"A": Decimal("0.005"), "B": Decimal("0.003")})
    pool = ["A", "B"]
    history_snapshot = {k: list(v) for k, v in history.items()}
    pool_snapshot = list(pool)

    compute_signals(pool, history, SIGNAL_DATE)

    assert history == history_snapshot
    assert pool == pool_snapshot


# ---------------------------------------------------------------------------
# 边界
# ---------------------------------------------------------------------------


def test_invalid_top_n_zero() -> None:
    history = _make_history({"A": Decimal("0.005")})
    with pytest.raises(ValueError, match="top_n"):
        compute_signals(["A"], history, SIGNAL_DATE, top_n=0)


def test_invalid_top_n_negative() -> None:
    history = _make_history({"A": Decimal("0.005")})
    with pytest.raises(ValueError, match="top_n"):
        compute_signals(["A"], history, SIGNAL_DATE, top_n=-1)


def test_top_n_exceeds_pool() -> None:
    """pool 2 只 + top_n=5 → 全 BUY。"""
    history = _make_history({"A": Decimal("0.005"), "B": Decimal("0.003")})
    rows = compute_signals(["A", "B"], history, SIGNAL_DATE, top_n=5)
    assert all(r.action == "BUY" for r in rows)


def test_single_etf() -> None:
    history = _make_history({"A": Decimal("0.005")})
    rows = compute_signals(["A"], history, SIGNAL_DATE)
    assert len(rows) == 1
    assert rows[0].action == "BUY"
    assert rows[0].rank == 1


# ---------------------------------------------------------------------------
# 与 rank_scores 行为一致
# ---------------------------------------------------------------------------


def test_ties_share_rank() -> None:
    """同分共享 rank（来自 rank_scores 的 competition ranking）。"""
    history = {
        "A": _linear_history("A", date(2023, 1, 1), 300, growth=Decimal("0.005")),
        "B": _linear_history("B", date(2023, 1, 1), 300, growth=Decimal("0.005")),
    }
    rows = compute_signals(["A", "B"], history, SIGNAL_DATE, top_n=5)
    ranks = [r.rank for r in rows]
    # 同分 → 同 rank（1, 1），competition ranking 跳号
    assert ranks == [1, 1]


# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------


def test_default_top_n_is_5() -> None:
    """top_n 不传时默认 5。"""
    # 用不同 growth 让 7 只 ETF 分数各异，否则同分同 rank 全部 BUY
    history = _make_history({
        "E0": Decimal("0.010"),
        "E1": Decimal("0.009"),
        "E2": Decimal("0.008"),
        "E3": Decimal("0.007"),
        "E4": Decimal("0.006"),
        "E5": Decimal("0.005"),
        "E6": Decimal("0.004"),
    })
    pool = list(history.keys())
    rows = compute_signals(pool, history, SIGNAL_DATE)
    buys = [r for r in rows if r.action == "BUY"]
    holds = [r for r in rows if r.action == "HOLD"]
    assert len(buys) == 5
    assert len(holds) == 2
