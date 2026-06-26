# Proposal: 业绩指标计算模块

## What
把 `app/backtest/engine.py` 内嵌的 `_compute_metrics` 抽出为独立模块 `app/backtest/metrics.py`，并补充 Sortino / Calmar 两个业界常用指标：

- **`app/backtest/metrics.py`**：纯计算
  - `compute_metrics(nav_series: list[tuple[date, Decimal]], initial_cash: Decimal, *, risk_free_rate: Decimal = Decimal("0")) -> dict[str, Decimal | None]`
  - 返回字典包含 6 个键：
    - `total_return`: 累计收益 `(final / initial) - 1`
    - `annualized_return`: 年化收益
    - `max_drawdown`: 最大回撤（正数表示回撤幅度）
    - `sharpe_ratio`: 夏普比率（无风险利率参数化）
    - `sortino_ratio`: 索提诺比率（仅下行波动率，业界区分「好坏波动」）
    - `calmar_ratio`: Calmar 比率（年化收益 / 最大回撤）
- **`app/backtest/engine.py`**：改用 `from app.backtest.metrics import compute_metrics`，删除内嵌 `_compute_metrics` / `_decimal_pow`
- **`app/backtest/__init__.py`**：re-export `compute_metrics` 便于调用方使用

## Why
当前业绩指标内嵌在 `app/backtest/engine.py` 的私有函数 `_compute_metrics` 里，几个问题：

1. **不可复用**：未来实时信号模块（live signal）也需要对当日模拟持仓算指标，私有函数无法 import
2. **指标偏少**：只有 total / annualized / max_dd / sharpe。业界标配至少还要 Sortino（区分下行波动）、Calmar（年化收益 / 回撤）
3. **Sharpe 假定无风险利率 = 0**：虽然 MVP 简化合理，但应该参数化以便未来对比国债 / 理财基准
4. **测试粒度**：与 engine 耦合，单测得跑整个 backtest 才能覆盖指标路径

抽出后：
- 计算逻辑独立测试，覆盖率更高
- 实时信号模块可直接复用
- 添加新指标不需改 engine

## Scope
- [x] backend
- [ ] frontend

## Out of Scope（本 change 不做）
- 业绩指标可视化（前端 change）
- 与基准（如沪深 300）的 alpha / beta / 信息比率
- 月度 / 年度收益矩阵
- 持仓分布 / 行业暴露分析
- 风险价值 VaR / CVaR
- 业绩归因（Brinson 模型）
- 把 `app/backtest/metrics.py` 进一步提到顶层 `app/metrics/`（视使用情况决定）

## Acceptance Criteria
- [ ] `app/backtest/metrics.py` 文件存在，导出 `compute_metrics`
- [ ] `compute_metrics(nav_series, initial_cash, *, risk_free_rate=Decimal("0")) -> dict[str, Decimal | None]`
- [ ] 返回字典包含 6 个键：`total_return` / `annualized_return` / `max_drawdown` / `sharpe_ratio` / `sortino_ratio` / `calmar_ratio`
- [ ] 当日收益序列无法计算时（如波动率为 0、空序列），返回 `None` 而非 0（与原版行为一致）
- [ ] `sharpe_ratio` 计算公式：`mean(excess_return) / std(all_returns) * sqrt(252)`，其中 `excess_return = return - risk_free_rate / 252`
- [ ] `sortino_ratio` 计算公式：`mean(excess_return) / std(negative_returns) * sqrt(252)`；当无负收益时返 `None`
- [ ] `calmar_ratio` 计算公式：`annualized_return / max_drawdown`；`max_drawdown = 0` 时返 `None`
- [ ] 引擎 `app/backtest/engine.py` 删除 `_compute_metrics` / `_decimal_pow`，改用 `from app.backtest.metrics import compute_metrics`
- [ ] `app/backtest/__init__.py` re-export `compute_metrics`
- [ ] 现有 24 个 engine 测试 + 6 个 persistence 测试全部仍然通过（行为不变）
- [ ] 新增 `tests/test_backtest_metrics.py`，至少 18 个测试覆盖：
  - 6 个指标各自在已知输入下的手算预期值
  - 边界：空 NAV → 全部 0 / None
  - 边界：单调递增 NAV → max_drawdown = 0，calmar = None
  - 边界：完全平稳 NAV → sharpe / sortino 均为 None（std = 0）
  - 边界：全部正收益 → sortino = None（无下行波动）
  - 风险利率参数化：`risk_free_rate=Decimal("0.02")` 时 sharpe 与默认不同
  - 与 engine 集成：`run_backtest` 返回的 metrics 与直接调 `compute_metrics` 一致
- [ ] README 增补「业绩指标」小节：6 个指标定义 + 公式 + 取值范围

## 设计决策（脑暴沉淀）
1. **模块位置**：`app/backtest/metrics.py`（与 backtest 同包），nav_series 是 backtest 概念先放一起；未来如需跨包复用再提到 `app/metrics/`
2. **风险利率**：参数化 `risk_free_rate`，默认 `Decimal("0")`，保持 MVP 行为
3. **年化因子**：252（标准 1 年交易日数，与学术文献一致）
4. **新增指标范围**：MVP 仅加 Sortino + Calmar，不加 annualized_volatility 与 win_rate（YAGNI，后续需要再加）

## Status
- [x] 提案已确认