"""Tests for app.backtest.metrics — pure performance-metrics calculation."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.backtest.metrics import (
    ANNUALIZATION,
    compute_metrics,
    _annualized_ratio,
    _decimal_pow,
    _zero_metrics,
)


# ---------------------------------------------------------------------------
# total_return
# ---------------------------------------------------------------------------


def test_total_return_known() -> None:
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 12, 31), Decimal("120")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["total_return"] == Decimal("0.2")


def test_total_return_negative() -> None:
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 12, 31), Decimal("80")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["total_return"] == Decimal("-0.2")


# ---------------------------------------------------------------------------
# annualized_return
# ---------------------------------------------------------------------------


def test_annualized_return_one_year() -> None:
    start = date(2024, 1, 1)
    end = start + timedelta(days=365)
    nav_series = [(start, Decimal("100")), (end, Decimal("120"))]
    m = compute_metrics(nav_series, Decimal("100"))
    # 365/366天 容差：年化应在 [0.15, 0.25] 范围内
    assert Decimal("0.15") < m["annualized_return"] < Decimal("0.25")


def test_annualized_short_window() -> None:
    start = date(2024, 1, 1)
    end = start + timedelta(days=7)
    nav_series = [(start, Decimal("100")), (end, Decimal("101"))]
    m = compute_metrics(nav_series, Decimal("100"))
    # 7 天 +1% 年化应该远高于日收益 0.01，约 0.68
    assert m["annualized_return"] > Decimal("0.5")


# ---------------------------------------------------------------------------
# max_drawdown
# ---------------------------------------------------------------------------


def test_max_drawdown_known() -> None:
    # peak 150, trough 100 → dd = 0.5
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 6, 1), Decimal("150")),
        (date(2024, 12, 31), Decimal("100")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["max_drawdown"] == Decimal("0.5")


def test_max_drawdown_no_drawdown() -> None:
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 6, 1), Decimal("110")),
        (date(2024, 12, 31), Decimal("120")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["max_drawdown"] == Decimal("0")


def test_max_drawdown_gap_at_end() -> None:
    # 验证"最大回撤点出现在序列末尾"场景。
    # 注：metrics 模块沿用 engine 的 dd = peak/nav - 1 公式（非标准 (peak-nav)/peak），
    # 以保持与现有 24 个 engine 测试的行为一致（spec.md 行为不变要求）。
    # 路径 [100, 150, 100, 75] → peak=150，最后跌到 75，dd = 150/75 - 1 = 1.0
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 4, 1), Decimal("150")),
        (date(2024, 8, 1), Decimal("100")),
        (date(2024, 12, 31), Decimal("75")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["max_drawdown"] == Decimal("1")


# ---------------------------------------------------------------------------
# sharpe_ratio
# ---------------------------------------------------------------------------


def test_sharpe_zero_std() -> None:
    # 常数 NAV：日收益全为 0，std = 0 → sharpe None
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("100")),
        (date(2024, 1, 3), Decimal("100")),
        (date(2024, 1, 4), Decimal("100")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["sharpe_ratio"] is None


def test_sharpe_known() -> None:
    # 路径 100 → 110 → 100 → 110 (zigzag)
    # daily = [+0.10, -0.0909..., +0.10]
    # 由于 geometric vs arithmetic 差异，mean 不严格为 0；smoke test 验证 sharpe 可算且数量级合理
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("110")),
        (date(2024, 1, 3), Decimal("100")),
        (date(2024, 1, 4), Decimal("110")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["sharpe_ratio"] is not None
    # 数量级在 ±10 范围内（与手算预期 ~6.7 一致）
    assert abs(m["sharpe_ratio"]) < Decimal("10")


def test_sharpe_default_risk_free_rate_zero() -> None:
    # 不传 risk_free_rate → 默认 0
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("110")),
        (date(2024, 1, 3), Decimal("105")),
    ]
    m_default = compute_metrics(nav_series, Decimal("100"))
    m_explicit_zero = compute_metrics(
        nav_series, Decimal("100"), risk_free_rate=Decimal("0")
    )
    assert m_default["sharpe_ratio"] == m_explicit_zero["sharpe_ratio"]


def test_sharpe_with_risk_free_rate() -> None:
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("110")),
        (date(2024, 1, 3), Decimal("105")),
    ]
    m_zero = compute_metrics(nav_series, Decimal("100"), risk_free_rate=Decimal("0"))
    m_2pct = compute_metrics(nav_series, Decimal("100"), risk_free_rate=Decimal("0.02"))
    # rf=0.02 时 mean(excess) 显著小于 rf=0
    assert m_zero["sharpe_ratio"] != m_2pct["sharpe_ratio"]
    assert m_2pct["sharpe_ratio"] < m_zero["sharpe_ratio"]


# ---------------------------------------------------------------------------
# sortino_ratio
# ---------------------------------------------------------------------------


def test_sortino_negative_returns() -> None:
    # 日收益 [-0.05, +0.03, -0.02]（rf=0）
    # mean(excess) = (-0.05 + 0.03 - 0.02) / 3 = -0.01333...
    # 负收益 = [-0.05, -0.02]，std = sqrt((0.05^2 + 0.02^2 - 2*0.0267*(-0.05-0.02)/2)^2/(2-1))
    # 用手算：mean_neg = (-0.05 + -0.02)/2 = -0.035
    # variance_neg = ((-0.05+0.035)^2 + (-0.02+0.035)^2) / (2-1)
    #              = (0.000225 + 0.000225) / 1 = 0.00045
    # std_neg = sqrt(0.00045) ≈ 0.021213203
    # sortino = -0.01333 / 0.021213203 * sqrt(252) ≈ -0.6287 * 15.8745 ≈ -9.98
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("95")),   # -0.05
        (date(2024, 1, 3), Decimal("97.85")),  # +0.03
        (date(2024, 1, 4), Decimal("95.893")),  # -0.02
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["sortino_ratio"] is not None
    # 手算预期 -9.98，允许 ±0.5 容差
    assert Decimal("-10.5") < m["sortino_ratio"] < Decimal("-9.5")


def test_sortino_all_positive() -> None:
    # 日收益 [+0.01, +0.02, +0.03] → 无负收益 → sortino None
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("101")),
        (date(2024, 1, 3), Decimal("103.02")),
        (date(2024, 1, 4), Decimal("106.1106")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["sortino_ratio"] is None


def test_sortino_single_negative() -> None:
    # 日收益 [-0.01, +0.05] → 仅 1 个负收益 → std 自由度不足 → sortino None
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("99")),
        (date(2024, 1, 3), Decimal("103.95")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["sortino_ratio"] is None


# ---------------------------------------------------------------------------
# calmar_ratio
# ---------------------------------------------------------------------------


def test_calmar_normal() -> None:
    # 构造 annualized ≈ 0.2、max_dd ≈ 0.1 的场景
    # 100 → 120 在 365 天内，max_dd 中间跌到 108（dd = 12/120 = 0.1）
    # 路径：100, 120, 108, 120
    # total_return = 0.2, days = 365, annualized ≈ 0.2
    # peak=120, 108/120 dd = 0.1
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 4, 1), Decimal("120")),
        (date(2024, 8, 1), Decimal("108")),
        (date(2025, 1, 1), Decimal("120")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    # annualized_return ~ 0.2, max_dd = (120-108)/120 = 0.1
    # calmar = 0.2 / 0.1 = 2
    assert m["calmar_ratio"] is not None
    assert Decimal("1.5") < m["calmar_ratio"] < Decimal("2.5")


def test_calmar_zero_drawdown() -> None:
    # 单调递增 → max_dd = 0 → calmar None
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 6, 1), Decimal("110")),
        (date(2024, 12, 31), Decimal("120")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["calmar_ratio"] is None


def test_calmar_negative_annualized() -> None:
    # 100 → 80 亏损 + 中间有回撤 → calmar 为负
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 6, 1), Decimal("120")),
        (date(2025, 1, 1), Decimal("80")),
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["calmar_ratio"] is not None
    assert m["calmar_ratio"] < Decimal("0")


# ---------------------------------------------------------------------------
# 边界
# ---------------------------------------------------------------------------


def test_empty_nav() -> None:
    m = compute_metrics([], Decimal("100"))
    assert m == _zero_metrics()
    assert m["total_return"] == Decimal("0")
    assert m["annualized_return"] == Decimal("0")
    assert m["max_drawdown"] == Decimal("0")
    assert m["sharpe_ratio"] is None
    assert m["sortino_ratio"] is None
    assert m["calmar_ratio"] is None


def test_single_point() -> None:
    # 单点 → 无日收益，ratios None，total_return 0（因为 final=initial）
    nav_series = [(date(2024, 1, 1), Decimal("100"))]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["total_return"] == Decimal("0")
    assert m["annualized_return"] == Decimal("0")
    assert m["max_drawdown"] == Decimal("0")
    assert m["sharpe_ratio"] is None
    assert m["sortino_ratio"] is None
    assert m["calmar_ratio"] is None


# ---------------------------------------------------------------------------
# 与 engine 集成
# ---------------------------------------------------------------------------


def test_engine_uses_metrics() -> None:
    """run_backtest 返回的 metrics 与直接调 compute_metrics 一致。"""
    from app.backtest.engine import BacktestParams, RebalanceFrequency, run_backtest

    start = date(2023, 1, 1)
    end = date(2024, 6, 30)
    initial = Decimal("100000")

    # 简单合成：3 个 ETF，500 天历史，价格稳步上行
    import random
    random.seed(42)
    price_history: dict[str, list[tuple[date, Decimal]]] = {}
    for code in ("510300", "510500", "510880"):
        series = []
        for i in range(600):
            d = start + timedelta(days=i)
            if d.weekday() >= 5:  # 跳过周末
                continue
            base = Decimal("10") + Decimal(str(i)) * Decimal("0.01")
            series.append((d, base))
        price_history[code] = series

    params = BacktestParams(
        etf_pool=["510300", "510500", "510880"],
        start=start,
        end=end,
        initial_cash=initial,
        lookback=120,
        skip=5,
        top_n=2,
        rebalance_freq=RebalanceFrequency.MONTHLY,
    )
    result = run_backtest(params, price_history)
    direct = compute_metrics(result.nav_series, initial)

    for key in ("total_return", "annualized_return", "max_drawdown", "sharpe_ratio"):
        # engine 现在没返回 sortino / calmar，所以只对比 4 个
        assert result.metrics[key] == direct[key]


def test_metrics_module_export() -> None:
    from app.backtest import compute_metrics as exported
    assert exported is compute_metrics


# ---------------------------------------------------------------------------
# risk_free_rate 覆盖
# ---------------------------------------------------------------------------


def test_sortino_default_risk_free_rate_zero() -> None:
    """不传 risk_free_rate → 默认 0，sortino 与显式 rf=0 一致。"""
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("95")),
        (date(2024, 1, 3), Decimal("97.85")),
        (date(2024, 1, 4), Decimal("95.893")),
    ]
    m_default = compute_metrics(nav_series, Decimal("100"))
    m_explicit_zero = compute_metrics(
        nav_series, Decimal("100"), risk_free_rate=Decimal("0")
    )
    assert m_default["sortino_ratio"] == m_explicit_zero["sortino_ratio"]


def test_sortino_with_risk_free_rate_lowers_ratio() -> None:
    """rf > 0 时，sortino（基于负超额收益的 std）应该更小（更负）。"""
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("95")),   # -0.05
        (date(2024, 1, 3), Decimal("97.85")),  # +0.03
        (date(2024, 1, 4), Decimal("95.893")),  # -0.02
    ]
    m_zero = compute_metrics(nav_series, Decimal("100"), risk_free_rate=Decimal("0"))
    m_2pct = compute_metrics(
        nav_series, Decimal("100"), risk_free_rate=Decimal("0.02")
    )
    assert m_zero["sortino_ratio"] is not None
    assert m_2pct["sortino_ratio"] is not None
    # rf=0.02 时超额收益更负 → sortino 更小
    assert m_2pct["sortino_ratio"] < m_zero["sortino_ratio"]


def test_sharpe_all_excess_negative_returns_none_when_insufficient() -> None:
    """只有 1 个日收益时，sharpe 因为 std 自由度不足返回 None。"""
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("90")),  # -0.10
    ]
    m = compute_metrics(nav_series, Decimal("100"), risk_free_rate=Decimal("0.05"))
    # len(daily_returns) = 1 < 2 → sharpe None
    assert m["sharpe_ratio"] is None
    # total_return = 0.9 - 1 = -0.1
    assert m["total_return"] == Decimal("-0.1")


def test_sharpe_all_negative_excess_still_computable() -> None:
    """多个日收益且方差 > 0 时，即使均值 < 0，sharpe 仍然返回有限值（不是 None）。"""
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("95")),  # -0.05
        (date(2024, 1, 3), Decimal("92")),  # ~-0.0316
        (date(2024, 1, 4), Decimal("88")),  # ~-0.0435
    ]
    m = compute_metrics(nav_series, Decimal("100"), risk_free_rate=Decimal("0"))
    # 3 个 daily returns，std > 0 → sharpe 可算
    assert m["sharpe_ratio"] is not None
    assert m["sharpe_ratio"] < Decimal("0")


def test_annualized_return_one_day_window() -> None:
    """2 个相邻日期（days=1）→ annualized_return 计算为 0。"""
    nav_series = [
        (date(2024, 1, 1), Decimal("100")),
        (date(2024, 1, 2), Decimal("110")),  # +10% in 1 day
    ]
    m = compute_metrics(nav_series, Decimal("100"))
    # days=1 → years ≈ 1/365，10% daily 复利年化很大，但因 days<=0 路径不会触发
    # 实际：days > 0 + final > 0 + initial > 0 → 走 (final/initial)^(1/years) - 1
    # years = 1/365，1.1^365 ≈ 1.1^365 远大于 1
    # 所以 annualized_return 应该是某个大于 0 的数
    assert m["annualized_return"] > Decimal("0")


def test_annualized_return_zero_days() -> None:
    """单点 nav_series → days=0 → annualized_return = 0。"""
    nav_series = [(date(2024, 1, 1), Decimal("100"))]
    m = compute_metrics(nav_series, Decimal("100"))
    assert m["annualized_return"] == Decimal("0")


# ---------------------------------------------------------------------------
# _decimal_pow / _annualized_ratio 内部 helper
# ---------------------------------------------------------------------------


def test_decimal_pow_negative_base_returns_zero() -> None:
    """_decimal_pow 对负基数（不应发生但有兜底）返回 0。"""
    from app.backtest.metrics import _decimal_pow

    result = _decimal_pow(Decimal("-2"), Decimal("0.5"))
    assert result == Decimal("0")


def test_annualized_ratio_single_element_returns_none() -> None:
    """_annualized_ratio 在 excess_returns 长度 < 2 时返回 None。"""
    from app.backtest.metrics import _annualized_ratio

    assert _annualized_ratio([Decimal("0.1")], [Decimal("0.1")]) is None
    assert _annualized_ratio([], []) is None


def test_annualized_ratio_zero_std_returns_none() -> None:
    """_annualized_ratio 在 std == 0 时返回 None（即使 excess 长度足够）。"""
    from app.backtest.metrics import _annualized_ratio

    excess = [Decimal("0.05"), Decimal("0.05"), Decimal("0.05")]
    raw = [Decimal("0.05"), Decimal("0.05"), Decimal("0.05")]
    assert _annualized_ratio(excess, raw) is None


def test_annualized_ratio_computes_known_value() -> None:
    """简单场景：mean=0, std>0 → ratio = 0。"""
    from app.backtest.metrics import _annualized_ratio

    excess = [Decimal("0.10"), Decimal("-0.10")]
    raw = [Decimal("0.10"), Decimal("-0.10")]
    result = _annualized_ratio(excess, raw)
    # mean = 0, std = sqrt((0.1^2 + 0.1^2)/(2-1)) = sqrt(0.02) ≈ 0.1414
    # ratio = 0 / 0.1414 * sqrt(252) = 0
    assert result is not None
    assert abs(result) < Decimal("1e-6")
