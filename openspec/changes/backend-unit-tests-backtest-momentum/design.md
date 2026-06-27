# Design — Backend Unit Tests (Backtest Engine + Momentum)

## Context

`backend/app/` 下四个纯函数模块目前是 v1.0 阶段 4 质量门控的关键路径：

| 模块 | 现状 | 现有测试 |
|------|------|---------|
| `app/factors/momentum.py` | 3 个 pure function（compute_momentum_score / scores / rank_scores） | 22 tests |
| `app/backtest/engine.py` | run_backtest + 6 个 helper（_validate_params / _build_calendar / _find_rebalance_dates / _build_close_lookup / _slice_closes_for_momentum / _compute_scores） | 28 tests（happy path 强、validation 弱） |
| `app/backtest/metrics.py` | compute_metrics + 3 个 helper（_decimal_pow / _annualized_ratio / _zero_metrics） | 20 tests |
| `app/backtest/persistence.py` | save_backtest_run（写 ORM 行 + 序列化 metrics JSON） | 6 tests（只验 4 个指标） |

本次变更只补测试。所有现有 helper（`make_linear_series` / `make_history` / `_make_history` / `MagicMock` session）已经够用，不需要新增 fixture。

## Goals / Non-Goals

**Goals:**
- 显式锁定 `_validate_params` 7 个 `ValueError` 分支的错误信息。
- 覆盖「不变量」类断言：`sum(weights) == 1`、NAV 单调性、weight 量化残差规则。
- 验证 `metrics` JSON 中 6 个指标（`sortino_ratio` / `calmar_ratio` 也要 round-trip）。
- 把所有新测试按主题归类到现有 TestXxx class，方便 diff review。

**Non-Goals:**
- 不引入 `pytest-cov` / `hypothesis` / `freezegun` 等新依赖。
- 不改 `conftest.py`、不新增共享 fixture。
- 不写集成测试（FastAPI 路由层已有 `test_api_backtest.py`）。
- 不为 `rebalance_log` 增加持久化（需要在 `BacktestRun` 上新增 JSON 列，超出本次范围；保留一条 negative assertion 标记这个 gap）。

> **关于应用代码改动**：为了让 `test_metrics_contains_sortino_and_calmar` / `test_metrics_sortino_calmar_none_serialized` 这两条测试有意义，`app/backtest/persistence.py` 会同步加 2 行（把 `result.metrics["sortino_ratio"]` 和 `result.metrics["calmar_ratio"]` 写进 `metrics_payload`）。数据本来就被 `compute_metrics` 计算出来，只是没存——这是「补全」而非「改行为」。`rebalance_log` 的持久化不在本次范围。

## Decisions

### 1. 新增一个 `test_engine_validation.py`，而不是把 validation 用例塞进 `test_backtest_engine.py`

**理由**：`test_backtest_engine.py` 已经 480 行；新加的 validation 用例会显著拉长且属于「模块级契约」一类，和「端到端回测流程」关注点不同。拆文件让 review 时两类测试一目了然。

**替代方案**：在 `test_backtest_engine.py` 内新增 `TestValidation` class。否决：单文件太长不利于 review；拆分文件零成本。

### 2. Metrics / persistence 的扩展用例追加到现有文件，不开新文件

**理由**：现有 `test_backtest_metrics.py` / `test_backtest_persistence.py` 已经按函数 + 边界 class 组织好风格；新加 4-6 个用例追加 class 即可。

**替代方案**：拆出 `test_metrics_sortino.py` / `test_persistence_json.py`。否决：拆得过于细，单文件 20-30 行 pytest 启动开销反而变大。

### 3. 动量边界用例追加到 `test_momentum.py` 现有 class

**理由**：lookback=0 / skip=0 / 自定义参数这些都属于 `compute_momentum_score` / `compute_momentum_scores` 的行为契约，复用现有 helper 即可。

**替代方案**：开 `test_momentum_edges.py`。否决：场景太少，不值得。

### 4. 不引入 `pytest.mark.parametrize` 来展开矩阵

**理由**：现有 90 个测试都用手写断言，没有用 parametrize；保持风格一致。如果某个 class 里有 4-5 个相似 case，可以单独决定是否上 parametrize，但默认不上。

**替代方案**：用 parametrize 把 7 个 ValueError 分支折成 1 个测试。否决：错误信息不同，parametrize 后失败信息反而模糊。

## Risks / Trade-offs

- **[Risk] 新断言锁定的实现细节后续会变**（例如 `_validate_params` 错误文案微调）→ **Mitigation**：每条 ValueError 测试只断言关键词（`match="end"` / `match="initial_cash"` 等），不锁死完整字符串。
- **[Risk] `compute_momentum_score(closes, lookback=0)` 当前返回什么没明确文档** → **Mitigation**：先跑一遍看实际行为再写测试；如果行为不合理（除零等），先在 `momentum.py` 边界处补一行（但这属于产品行为变更，需用户确认，本变更按现状锁定）。
- **[Risk] `engine.py` 中 `last_close` 取的是 `< current_date` 的最后一个 close，可能和直觉不符** → **Mitigation**：在测试中显式构造「delist on day 1」场景锁定行为，注释里说明设计意图。

## Migration Plan

无。本变更只动测试文件，无需迁移。

## Open Questions

- 是否需要给 `pytest` 加最小覆盖率门槛（`--cov-fail-under=80`）？当前仓库没 CI，倾向 **不引入**，留到 v1.0 演示数据预置之后再开 CI 时一并处理。
