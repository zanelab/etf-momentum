# Spec: 回测引擎

## ADDED Requirements

### Requirement: 回测参数 BacktestParams
`BacktestParams` 是参数容器，冻结 dataclass。

#### Scenario: 构造与默认值
- Given `BacktestParams(etf_pool=["510300","510500"], start=date(2024,1,1), end=date(2024,12,31), initial_cash=Decimal("100000"))`
- When 实例化
- Then `lookback=252, skip=21, top_n=5, rebalance_freq=RebalanceFrequency.MONTHLY` 为默认值

#### Scenario: 不可变
- Given 已实例化的 `BacktestParams`
- When 尝试赋值 `params.top_n = 10`
- Then 抛 `FrozenInstanceError`（frozen dataclass）

### Requirement: 调仓频率枚举
`RebalanceFrequency` 提供 MONTHLY 与 QUARTERLY 两档。

#### Scenario: 枚举值
- Given `RebalanceFrequency.MONTHLY` 与 `RebalanceFrequency.QUARTERLY`
- When 取 `.value`
- Then 分别为 `"monthly"` 与 `"quarterly"`

### Requirement: 调仓事件与结果
`RebalanceEvent` / `BacktestResult` 是结果数据载体。

#### Scenario: RebalanceEvent 字段
- Given `RebalanceEvent(date=..., scores={"a": Decimal("0.1")}, selected=["a"], weights={"a": Decimal("1")})`
- When 检查字段
- Then 4 个字段类型与值正确

#### Scenario: BacktestResult 字段
- Given `BacktestResult(nav_series=[(d, v)], rebalance_log=[event], metrics={...})`
- When 检查
- Then 3 个字段类型与值正确

### Requirement: 纯函数主入口 run_backtest
`run_backtest(params, price_history) -> BacktestResult` 接受历史价格返回结果，**不读不写 DB**。

#### Scenario: 标准三只 ETF 月末调仓
- Given 3 只 ETF 各 300 个交易日的 close 序列，`start=date(2024,1,1), end=date(2024,3,31), top_n=2, MONTHLY`
- When 调用 `run_backtest(params, price_history)`
- Then `rebalance_log` 包含 3 条调仓事件（1/2/3 月最后交易日各一次）
- And 每条事件 `selected` 长度为 2，`weights` 为 `{code: Decimal("0.5")}`
- And `nav_series` 长度 = 区间内交易日数

#### Scenario: 单只 ETF
- Given `etf_pool=["a"], top_n=5`
- When 调用
- Then `selected=["a"]`，`weights={"a": Decimal("1")}`，资金 100% 进 a

#### Scenario: 数据不足跳过调仓
- Given 部分 ETF 在调仓日往前 273 交易日数据缺失
- When 调仓日到来
- Then 跳过该次调仓，`rebalance_log` 少一条，NAV 仍连续

#### Scenario: 完全无足够数据
- Given 所有 ETF 历史都 < 273 天
- When 调用
- Then `rebalance_log=[]`，`nav_series` 平直（每条 NAV = initial_cash），`metrics.total_return = Decimal("0")`

#### Scenario: 日期范围太短
- Given `start, end` 跨度 < 273 天
- When 调用
- Then 同上

#### Scenario: MONTHLY vs QUARTERLY 触发次数
- Given 12 个月的数据
- When `freq=MONTHLY` → 12 次调仓；`freq=QUARTERLY` → 4 次调仓（3/6/9/12 月）

#### Scenario: 调仓日 ETF 无 close 跳过
- Given selected top-N 中某只在调仓日无数据
- When 调仓日到来
- Then 该只不买入，剩余按比例摊分；不抛异常

#### Scenario: 退市 ETF 卖出转现金
- Given 某 ETF 在中间某天后无数据
- When 该 ETF 在持仓中
- Then 最后有数据的一日按 close 卖出，NAV 中该 ETF 贡献为 0，剩余为现金
- And 下次调仓日从其他 ETF 中重新选

#### Scenario: top_n 超过实际可用
- Given `top_n=5` 但有效 ETF 只有 3 只
- When 调仓
- Then `selected` 长度为 3，`weights = {c: Decimal("1")/3}`

#### Scenario: 等权严格验证
- Given 调仓事件 `event.weights`
- When 求和
- Then `sum(weights.values()) == Decimal("1")`（不足 top_n 时按实际入选数等分）

### Requirement: 业绩指标
`metrics` 包含 total_return / annualized_return / max_drawdown / sharpe_ratio。

#### Scenario: total_return 手算
- Given `initial_cash=100000, final_nav=120000`
- When 计算 metrics
- Then `total_return == Decimal("0.2")`

#### Scenario: annualized_return
- Given 365 天 +20% 收益
- When 计算
- Then `annualized_return ≈ Decimal("0.2")`（恰好 1 年）

#### Scenario: max_drawdown
- Given NAV 序列 `[100, 120, 60, 80]`
- When 计算
- Then `max_drawdown == Decimal("0.5")`（峰值 120，谷值 60，回撤 50%）

#### Scenario: sharpe_ratio
- Given 已知日收益序列
- When 计算
- Then `sharpe = mean / std * sqrt(252)`（无风险利率 = 0）

#### Scenario: sharpe 波动率为 0
- Given NAV 平直（无波动）
- When 计算
- Then `sharpe_ratio is None`（除零保护）

### Requirement: 持久化 save_backtest_run
`save_backtest_run(session, params, result)` 写 `BacktestRun` 行。

#### Scenario: 写入字段正确
- Given mock session
- When 调用 `save_backtest_run(session, params, result)`
- Then `session.add` 被调用一次，参数为 BacktestRun 实例
- And `etf_pool` 是 `list[str]`，`momentum_window == params.lookback`，`rebalance_freq == params.rebalance_freq.value`
- And `start_date / end_date` 与 params 一致
- And `metrics` 是 JSON dict，含 `total_return / annualized_return / max_drawdown / sharpe_ratio` + `params` 子字典

#### Scenario: 失败抛异常
- Given session.commit 抛 `IntegrityError`
- When 调用
- Then 异常向上传播（不静默）

### Requirement: pytest 测试覆盖
backend/tests/test_backtest_engine.py 覆盖所有分支；test_persistence.py 覆盖 save_backtest_run。

#### Scenario: pytest 全部通过
- Given backend 目录运行 `uv run pytest`
- When 收集所有 `tests/test_*.py`
- Then 全部通过；退出码 0

### Requirement: README 增补回测引擎章节
backend/README.md 新增「回测引擎」章节，说明参数、调用示例、业绩指标公式。

#### Scenario: README 含 API 用法
- Given 阅读 backend/README.md
- When 查找「回测引擎」章节
- Then 含 `run_backtest` / `save_backtest_run` 调用示例 + 业绩指标公式说明