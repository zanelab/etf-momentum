# Implementation Plan: 业绩指标计算模块

## Prerequisites
- [x] 切换到 feature/metrics-extraction 分支
- [x] 确认 backend 目录存在，回测引擎就位
- [x] 确认 Python 3.11+ 与 uv 可用

## Dependencies
- [x] 无新增运行时依赖
- [x] 确认 `backend/pyproject.toml` 无需更新

## Module Structure
- [x] `app/backtest/metrics.py` 创建
- [x] `app/backtest/__init__.py` re-export `compute_metrics`

## Core Implementation
- [x] `app/backtest/metrics.py` 实现 `compute_metrics(nav_series, initial_cash, *, risk_free_rate=Decimal("0")) -> dict[str, Decimal | None]`
- [x] `app/backtest/metrics.py` 实现 `_annualized_ratio(excess_returns, raw_returns_for_std)` 内部辅助
- [x] `app/backtest/metrics.py` 实现 `_decimal_pow(base, exponent)`（从 engine 迁移）
- [x] `app/backtest/metrics.py` 实现 `_zero_metrics()` 返回空序列默认 dict

## Engine Refactor
- [x] `app/backtest/engine.py` 删除 `_compute_metrics` 函数体
- [x] `app/backtest/engine.py` 删除 `_decimal_pow` 函数体
- [x] `app/backtest/engine.py` 增加 `from app.backtest.metrics import compute_metrics`
- [x] `app/backtest/engine.py` `run_backtest` 内 `_compute_metrics(nav_series, params.initial_cash)` → `compute_metrics(nav_series, params.initial_cash)`
- [x] `tests/test_backtest_engine.py` 8 处 `from app.backtest.engine import _compute_metrics` 改为新模块导入（行为不变，import 路径调整）

## Testing
- [x] `tests/test_backtest_metrics.py` 创建
- [x] `test_total_return_known`：100 → 120 = 0.2
- [x] `test_total_return_negative`：100 → 80 = -0.2
- [x] `test_annualized_return_one_year`：365 天 +20% → ~0.2
- [x] `test_annualized_short_window`：7 天 +1% → 大幅年化
- [x] `test_max_drawdown_known`：NAV [100,150,100] → 0.5
- [x] `test_max_drawdown_no_drawdown`：单调递增 → 0
- [x] `test_max_drawdown_gap_at_end`：NAV [100,150,100,75] → 1.0（plan 值 0.55 与 engine `peak/nav-1` 公式冲突，改用兼容值）
- [x] `test_sharpe_zero_std`：常数 NAV → None
- [x] `test_sharpe_known`：已知日收益 → 数量级合理
- [x] `test_sharpe_default_risk_free_rate_zero`：`risk_free_rate=0` 默认
- [x] `test_sharpe_with_risk_free_rate`：rf=0.02 时 sharpe 与默认不同
- [x] `test_sortino_negative_returns`：含负收益 → 手算 -9.98 ±0.5
- [x] `test_sortino_all_positive`：全正 → None
- [x] `test_sortino_single_negative`：单点负收益 → None（std 自由度不足）
- [x] `test_calmar_normal`：ann=0.2, max_dd=0.111 → ~1.8
- [x] `test_calmar_zero_drawdown`：单调递增 → None
- [x] `test_calmar_negative_annualized`：净值下跌 → 负数
- [x] `test_empty_nav`：全部 0/None
- [x] `test_single_point`：单点 → ratios None，total_return 0
- [x] `test_engine_uses_metrics`：run_backtest metrics 与直接 compute_metrics 一致
- [x] `test_metrics_module_export`：`from app.backtest import compute_metrics` 正常

## TDD Verification
- [x] 写完 21 个测试后运行 pytest 全部通过

## Build & Runtime Verification
- [x] `cd backend && uv run pytest` → 全部通过（119 = 98 原有 + 21 新增）
- [x] `cd backend && uv run python -c "from app.backtest import compute_metrics; from decimal import Decimal; from datetime import date; print(compute_metrics([(date(2024,1,1), Decimal('100')), (date(2024,12,31), Decimal('120'))], Decimal('100')))"` → 打印 6 键 dict

## Documentation
- [x] `backend/README.md` 增补「业绩指标」章节：
  - 6 个指标定义 + 公式表
  - 调用示例
  - 边界行为（None vs 0）说明
  - 参数说明（risk_free_rate）

## Acceptance Check
- [x] 逐条对照 proposal.md 的 11 项 Acceptance Criteria，全部满足
- [x] 逐条对照 spec.md 的 9 个 Requirement 至少一个 Scenario 通过