# Spec: 业绩指标计算模块

## ADDED Requirements

### Requirement: compute_metrics 公开 API
`compute_metrics(nav_series, initial_cash, *, risk_free_rate=Decimal("0"))` 返回 6 个指标的字典。

#### Scenario: 基础调用返回 6 个键
- Given `nav_series = [(date(2024,1,1), Decimal("100")), (date(2024,12,31), Decimal("120"))]`，`initial_cash = Decimal("100")`
- When 调用 `compute_metrics(nav_series, initial_cash)`
- Then 返回 dict 含 6 个键：`total_return` / `annualized_return` / `max_drawdown` / `sharpe_ratio` / `sortino_ratio` / `calmar_ratio`

#### Scenario: 空 NAV 序列
- Given `nav_series = []`
- When 调用
- Then `total_return = Decimal("0")` / `annualized_return = Decimal("0")` / `max_drawdown = Decimal("0")` / 其他三个 ratio 为 `None`

### Requirement: total_return
累计收益 = `(final / initial) - 1`。

#### Scenario: 20% 收益
- Given `nav_series` 起始 100、结束 120
- When 调用
- Then `total_return == Decimal("0.2")`

### Requirement: annualized_return
年化收益 = `(final/initial) ** (365/days) - 1`。

#### Scenario: 恰好 1 年 +20%
- Given 365 天 +20%
- When 调用
- Then `annualized_return` 在 `[0.15, 0.25]`（允许 365/366 天差异）

### Requirement: max_drawdown
最大回撤（正数）。

#### Scenario: 已知回撤 0.5
- Given NAV `[100, 150, 100]`
- When 调用
- Then `max_drawdown == Decimal("0.5")`

#### Scenario: 单调递增无回撤
- Given NAV `[100, 110, 120]`
- When 调用
- Then `max_drawdown == Decimal("0")`

### Requirement: sharpe_ratio
夏普比率，`mean(excess) / std(all_returns) * sqrt(252)`，无风险利率参数化。

#### Scenario: std = 0 返回 None
- Given 完全平稳 NAV
- When 调用
- Then `sharpe_ratio is None`

#### Scenario: 无风险利率 = 0 默认
- Given 已知日收益序列
- When 调用（不传 risk_free_rate）
- Then `sharpe_ratio` 按 `risk_free_rate = 0` 计算

#### Scenario: 无风险利率参数化生效
- Given 相同 nav_series
- When 分别传 `risk_free_rate=Decimal("0")` 与 `risk_free_rate=Decimal("0.02")`
- Then 两个 sharpe_ratio 不同

### Requirement: sortino_ratio
索提诺比率，`mean(excess) / std(negative_returns) * sqrt(252)`。

#### Scenario: 含负收益手算
- Given 日收益序列 `[-0.05, +0.03, -0.02]`，`risk_free_rate = 0`
- When 调用
- Then `sortino_ratio` 与手算预期值一致（mean = -0.0133, std(negatives) ≈ 0.0153, ratio ≈ -0.87）

#### Scenario: 全正收益返回 None
- Given 日收益 `[+0.01, +0.02, +0.03]`
- When 调用
- Then `sortino_ratio is None`（无下行波动）

#### Scenario: 单个负收益返回 None
- Given 日收益 `[-0.01, +0.05]`
- When 调用
- Then `sortino_ratio is None`（std 自由度不足）

### Requirement: calmar_ratio
Calmar 比率，`annualized_return / max_drawdown`。

#### Scenario: 已知比率
- Given 已知 NAV → annualized = 0.2，max_dd = 0.1
- When 调用
- Then `calmar_ratio == Decimal("2")`

#### Scenario: 无回撤返回 None
- Given 单调递增 NAV
- When 调用
- Then `calmar_ratio is None`

#### Scenario: 负 annualized（亏损）
- Given 净值从 100 跌到 80
- When 调用
- Then `calmar_ratio` 为负 Decimal

### Requirement: 引擎复用 compute_metrics
`app/backtest/engine.py` 删除内嵌 `_compute_metrics` / `_decimal_pow`，改用新模块。

#### Scenario: 现有 engine 测试不变
- Given 现有 24 个 engine 测试 + 6 个 persistence 测试
- When 运行 pytest
- Then 全部通过（行为不变）

#### Scenario: 引擎返回 metrics 与直接调一致
- Given 同一 nav_series
- When 分别 `run_backtest(...)` 与 `compute_metrics(nav, initial)`
- Then 两个 metrics dict 内容一致

### Requirement: 模块导出
`app.backtest.compute_metrics` 可被外部 import。

#### Scenario: import 路径生效
- Given `from app.backtest import compute_metrics`
- When 调用
- Then 正常返回 dict，不抛 ImportError

### Requirement: pytest 测试覆盖
新增 `tests/test_backtest_metrics.py`，至少 18 个测试覆盖所有指标与边界。

#### Scenario: 全套通过
- Given backend 目录运行 `uv run pytest`
- When 收集所有 `tests/test_*.py`
- Then 全部通过；退出码 0（116+ = 98 原有 + 18 新增）

### Requirement: README 增补业绩指标小节
backend/README.md 新增「业绩指标」章节。

#### Scenario: README 含 6 指标公式
- Given 阅读 backend/README.md
- When 查找「业绩指标」章节
- Then 含 6 个指标定义 + 公式 + 取值范围说明