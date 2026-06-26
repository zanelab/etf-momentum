# Design: 业绩指标计算模块

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 4 项关键决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 模块位置 | `app/backtest/metrics.py`（与 backtest 同包） | nav_series 是 backtest 概念，先同包；未来如需跨包复用再提到 `app/metrics/` |
| 风险利率 | 参数化 `risk_free_rate`，默认 `Decimal("0")` | MVP 保持现状，调用方按需传入实际利率 |
| 年化因子 | 252（标准 1 年交易日数） | 与 AQR / Carhart 等学术文献一致 |
| 新增指标范围 | 仅 Sortino + Calmar | YAGNI：业界标配即可，避免一次引入过多指标 |
| Decimal 精度 | 全程 Decimal；sqrt 用 `Decimal.sqrt()` (Py 3.11+) | 与 DailyPrice.Numeric(10,4) 同族 |
| 接口形态 | `compute_metrics(nav_series, initial_cash, *, risk_free_rate=...) -> dict` | 关键字参数收 risk_free_rate；保留 `initial_cash` 位置参数便于 IDE 自动补全 |
| 边界处理 | std=0 → None；空序列 → 全部 0/None；除零保护 | 与原版 `_compute_metrics` 一致 |
| 函数位置 | 不需要 class/Protocol；纯函数 + 静态导入 | 单测简单；无状态 |

## 模块结构

```
backend/app/backtest/
├── __init__.py             # re-export compute_metrics（新增）
├── engine.py               # 删除 _compute_metrics / _decimal_pow；改用 compute_metrics
├── metrics.py              # 新增：compute_metrics
└── persistence.py
```

## API 设计

```python
from decimal import Decimal
from datetime import date

def compute_metrics(
    nav_series: list[tuple[date, Decimal]],
    initial_cash: Decimal,
    *,
    risk_free_rate: Decimal = Decimal("0"),
) -> dict[str, Decimal | None]:
    """计算 6 个业绩指标。

    返回字典：
    - total_return: 累计收益
    - annualized_return: 年化收益
    - max_drawdown: 最大回撤（正数）
    - sharpe_ratio: 夏普比率（None if std = 0）
    - sortino_ratio: 索提诺比率（None if 无下行波动）
    - calmar_ratio: Calmar 比率（None if max_drawdown = 0）

    当 nav_series 为空时，所有指标返回 0 或 None。
    """
```

## 指标公式

| 指标 | 公式 | 边界处理 |
|------|------|---------|
| `total_return` | `(final_nav / initial_cash) - 1` | 空序列 → `0` |
| `annualized_return` | `(final/initial) ** (365/days) - 1`，`days = (last-first).days` | `days <= 0` → `0` |
| `max_drawdown` | `max over t of (peak(t) / nav(t) - 1)`，`peak(t) = max(nav[0..t])` | 空序列 → `0` |
| `sharpe_ratio` | `mean(excess_return) / std(all_returns) * sqrt(252)`，`excess = r - rf/252` | `std = 0` 或 `< 2 returns` → `None` |
| `sortino_ratio` | `mean(excess_return) / std(negative_returns) * sqrt(252)` | 无负收益或 `< 2 returns` → `None` |
| `calmar_ratio` | `annualized_return / max_drawdown` | `max_drawdown = 0` → `None` |

**年化因子**：日收益→年化的乘数 = `sqrt(252)`（annualized vol/sharpe/sortino）。
**日收益**：`(nav[i] / nav[i-1]) - 1`，从 i=1 开始。

## 实现要点

```python
import math
from decimal import Decimal
from datetime import date

ANNUALIZATION = Decimal(252).sqrt()  # sqrt(252) ≈ 15.8745


def compute_metrics(nav_series, initial_cash, *, risk_free_rate=Decimal("0")):
    if not nav_series:
        return _zero_metrics()
    
    initial = initial_cash
    final = nav_series[-1][1]
    total_return = final / initial - Decimal("1")
    
    days = (nav_series[-1][0] - nav_series[0][0]).days
    if days > 0 and final > 0 and initial > 0:
        years = Decimal(days) / Decimal("365")
        annualized_return = _decimal_pow(final / initial, Decimal(1) / years) - Decimal("1")
    else:
        annualized_return = Decimal("0")
    
    # Max drawdown
    peak = nav_series[0][1]
    max_dd = Decimal("0")
    for _, nav in nav_series:
        if nav > peak:
            peak = nav
        if peak > 0:
            dd = peak / nav - Decimal("1")
            if dd > max_dd:
                max_dd = dd
    
    # Daily returns + excess returns
    daily_returns = []
    for i in range(1, len(nav_series)):
        prev = nav_series[i-1][1]
        curr = nav_series[i][1]
        if prev > 0:
            daily_returns.append(curr / prev - Decimal("1"))
    
    daily_rf = risk_free_rate / Decimal("252")
    excess_returns = [r - daily_rf for r in daily_returns]
    
    # Sharpe
    sharpe = _annualized_ratio(excess_returns, daily_returns)
    
    # Sortino (only negative excess returns in denominator)
    negative_returns = [r for r in excess_returns if r < 0]
    sortino = _annualized_ratio(excess_returns, negative_returns)
    
    # Calmar
    if max_dd > 0:
        calmar = annualized_return / max_dd
    else:
        calmar = None
    
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
    }


def _annualized_ratio(excess_returns, raw_returns_for_std):
    """Standard annualized ratio: mean(excess) / std(raw) * sqrt(252)."""
    if len(excess_returns) < 2 or len(raw_returns_for_std) < 2:
        return None
    mean_excess = sum(excess_returns, Decimal("0")) / Decimal(len(excess_returns))
    variance = sum((r - mean_excess) ** 2 for r in excess_returns) / Decimal(len(excess_returns) - 1)
    std = variance.sqrt()
    if std == 0:
        return None
    return (mean_excess / std) * ANNUALIZATION
```

## 测试策略

- **test_total_return**：基础计算
- **test_annualized_return_one_year**：已知日期范围
- **test_max_drawdown_known**：已知 NAV 序列
- **test_sharpe_zero_std**：常数序列 → None
- **test_sharpe_known**：已知日收益 → 手算
- **test_sharpe_with_risk_free_rate**：rf=0.02 时 sharpe 与 rf=0 不同
- **test_sortino_negative_returns**：含负收益 → 手算
- **test_sortino_all_positive**：全正收益 → None
- **test_sortino_zero_std_negative**：仅一个负收益 → None（std 单点无法算）
- **test_calmar_normal**：年化 / max_dd → 手算
- **test_calmar_zero_drawdown**：单调递增 → None
- **test_calmar_negative_annualized**：亏钱 + 有回撤 → 负数
- **test_empty_nav**：全部 0/None
- **test_single_point**：单点 → None for ratios
- **test_two_points**：两点 → 可算
- **test_engine_uses_metrics**：run_backtest 调用后 metrics 与 compute_metrics 一致
- **test_metrics_module_export**：app.backtest.compute_metrics 可导入
- **test_metrics_does_not_modify_input**：原 nav_series 不变
- **test_metrics_decimal_precision**：返回 Decimal 类型

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| Decimal.sqrt 性能 | 单次 metrics 调用 < 1000 NAV 点，Py 3.11 Decimal sqrt ~ms 级 |
| `mean / std` 零除保护 | std == 0 → None |
| 日收益空（< 2 点） | sharpe / sortino → None |
| annualized ** 浮点精度 | _decimal_pow 已用；保留原实现 |
| Calmar 负数 | 不阻止，calmar 允许为负（亏钱 + 回撤） |
| 退市 / 数据中断 | 沿用 engine 现有的「持有最后 close」逻辑，metrics 模块只看 nav_series |

## 不在本 change 范围

- annualized_volatility、win_rate（YAGNI）
- 与基准对比的 alpha / beta / 信息比率
- 月度 / 年度收益矩阵
- VaR / CVaR
- 业绩归因（Brinson）
- 移到顶层 `app/metrics/`
- 前端可视化