# 后端单元测试（回测引擎 + 动量计算）

## Why

`spec/tasks.md` 阶段 4「质量与交付」明确要求补全后端单元测试（回测引擎、动量计算）。当前 90 个测试覆盖了核心计算路径，但仍有以下空白：

1. **`run_backtest` 的输入校验完全没测** — `_validate_params` 7 个 `ValueError` 分支（end<start、initial_cash≤0、top_n<1、lookback<1、skip<0、池为空、池代码缺失）目前只能间接通过 happy path 验证。
2. **回测引擎边界场景** — 空日历、稀疏数据、跨年调仓、调仓日全部 ETF 无收盘、调仓日全 None 分数、单一交易日窗口、weight 量化残差分配等都没有显式测试。
3. **业绩指标的 risk_free_rate 覆盖不全** — 已有测试只验证了 `sharpe_ratio` 跟 rf 的关系，`sortino_ratio` + rf、sharpe 全负超额 → None 等组合没有测。
4. **持久化层只验证 4 个指标** — `save_backtest_run` 的 metrics JSON 包含 6 个指标，但只对 `total_return` / `annualized_return` / `max_drawdown` / `sharpe_ratio` 做了断言，`sortino_ratio` / `calmar_ratio` 的序列化没有 round-trip 验证。
5. **动量因子边界** — `lookback=0` / `skip=0`、自定义 `lookback`/`skip` 在 `compute_momentum_scores` 批处理路径下的传播、大数价格都没显式测试。

这些空白的实际风险：未来重构 `_validate_params` / `_find_rebalance_dates` / `_annualized_ratio` 时，没有测试守住约束，重构很容易引入回归。

## What Changes

仅新增后端单元测试（`backend/tests/` 下四个目标文件 + 一个新的 `test_engine_validation.py`），不修改任何业务代码。

| 目标 | 新增用例数 | 重点 |
|------|-----------|------|
| `test_engine_validation.py` (新) | ~10 | 7 个 ValueError 分支各一条 + 错误信息断言 |
| `test_backtest_engine.py` (扩展) | ~12 | 空日历 / 跨年 / 调仓日无收盘 / 全 None 分数 / 单日窗口 / weight 求和=1 / 单一 ETF weight=1 / 净值无变化（sell-then-rebuy） / 已退市 ETF 仍被持有 |
| `test_backtest_metrics.py` (扩展) | ~6 | sortino + risk_free_rate / sharpe 全负超额 None / days=1 年化 / _decimal_pow 负基数 / _annualized_ratio 单元素 None / negative 累计不归零 |
| `test_backtest_persistence.py` (扩展) | ~4 | sortino/calmar 序列化 / rebalance_log_json / name 字段 / 单点 nav |
| `test_momentum.py` (扩展) | ~5 | lookback=0 / skip=0 / 显式 lookback+skip 在 scores 批处理中传播 / 大价格 / 混合类型 |

预期：测试总数从 90 → 约 130；目标模块（`engine` / `momentum` / `metrics` / `persistence`）行覆盖率达到 ≥ 90%。

不引入：
- 不新增 pytest 插件（不引入 `pytest-cov`，CI 还没要求）
- 不改业务代码
- 不改 `conftest.py`（现有 fixture 已够用）
- 不改 API schema、ORM、CLI 入口

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- (none)

> 本次变更只补测试、不改产品行为，因此不引入新 capability，也不对现有 capability 写 delta spec。`openspec/specs/` 无变化。

## Impact

- **代码**：仅 `backend/tests/test_backtest_engine.py` / `test_backtest_metrics.py` / `test_backtest_persistence.py` / `test_momentum.py` 和新增的 `test_engine_validation.py`。
- **API / DB / CLI**：无。
- **依赖**：仍用 `pytest` + `unittest.mock.MagicMock`（persistence 测试沿用现有约定），不引入新依赖。
- **CI**：当前仓库无 `.github/workflows/`，新增测试通过 `pytest backend/tests` 跑即可。
- **风险**：所有新断言都是「已有行为 → 显式锁定」，不涉及规范变更，因此不会破坏现有调用方。
