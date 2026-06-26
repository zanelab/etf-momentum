# Proposal: 回测引擎

## What
实现经典学术动量策略的回测引擎，把「数据 + 动量因子 + 调仓规则 + 净值跟踪」串成端到端流程：

- **`app/backtest/__init__.py`**：包入口
- **`app/backtest/engine.py`**：核心引擎
  - `BacktestParams` dataclass：参数容器（ETF 池、日期范围、动量窗口、top_n、调仓频率、初始资金）
  - `RebalanceFrequency` enum：`MONTHLY` / `QUARTERLY`
  - `RebalanceEvent` dataclass：单次调仓事件（date、scores、selected、weights）
  - `BacktestResult` dataclass：结果汇总（nav_series、rebalance_log、metrics）
  - `run_backtest(params, price_history) -> BacktestResult`：纯计算主入口（不读 DB）
- **`app/backtest/persistence.py`**：持久化层
  - `save_backtest_run(session, params, result) -> BacktestRun`：写入 ORM（拆开计算与持久化，单测可只测计算）
- **数据来源**：调用方传入 `price_history: dict[str, list[(date, Decimal)]]`（已按 code 排好序的 close 序列）；**不回查 DB**
- **复用**：`app/factors/momentum.compute_momentum_scores` + `rank_scores` 直接调用，不再重写动量逻辑
- **业绩指标**：本 change 仅算**总收益率 + 年化收益率 + 最大回撤 + 夏普比率**；不写 PerformanceTracker 之类可插拔框架
- **不写**：手续费、滑点、借贷约束、分红再投资等真实摩擦（MVP 不模拟）

## Why
阶段 2 核心能力第一项「动量因子」已完成。下一步是把「算分数」升级到「**用分数驱动交易**」——回测引擎就是这套机制的核心。它是：

- 业绩指标计算（下一 change）的数据源
- 实时信号计算的对照基准（看策略回测表现与当前信号是否一致）
- 前端 Backtest UI 的后端支撑

把回测引擎抽象成「输入参数 + 价格历史 → 输出净值曲线 + 业绩指标」的纯函数 + 持久化函数，好处：
- 计算逻辑可独立测试（无需 DB fixture）
- 与实时信号模块解耦，避免一边回测一边 IO
- 持久化单独成层，便于替换存储后端

## Scope
- [x] backend
- [ ] frontend

## Out of Scope（本 change 不做）
- 实时信号计算与持久化（后续「实时信号计算与排名」change）
- 业绩指标独立模块（本次内置在引擎里，后续 change 抽出）
- 手续费、滑点、印花税等摩擦建模
- 分红再投资（默认假设不复利分红）
- 多因子合成（仅动量单因子）
- 行业中性化、风险中性化
- 借贷 / 保证金 / 做空
- 调仓成本最小化（CVX 优化等）
- 指数基准对比（不计算相对沪深 300 的 alpha）
- 任务调度（不挂 cron，定时回测后续再说）

## Acceptance Criteria
- [ ] `app/backtest/__init__.py`、`app/backtest/engine.py`、`app/backtest/persistence.py` 文件存在
- [ ] `BacktestParams`：dataclass，含 `etf_pool: list[str]`、`start: date`、`end: date`、`initial_cash: Decimal`、`lookback: int = 252`、`skip: int = 21`、`top_n: int = 5`、`rebalance_freq: RebalanceFrequency = MONTHLY`
- [ ] `RebalanceFrequency`：`MONTHLY` / `QUARTERLY` 两档；按「**该月最后一个交易日**」找调仓日（QUARTERLY = 3/6/9/12 月最后交易日）
- [ ] `RebalanceEvent`：含 `date: date`、`scores: dict[str, Decimal | None]`、`selected: list[str]`、`weights: dict[str, Decimal]`（**等权**，权重 = 1/top_n；不足 top_n 时按比例摊分剩余）
- [ ] `BacktestResult`：含 `nav_series: list[tuple[date, Decimal]]`（按日期升序）、`rebalance_log: list[RebalanceEvent]`、`metrics: dict`
- [ ] `metrics` 包含至少：`total_return: Decimal`（总收益）、`annualized_return: Decimal`（年化）、`max_drawdown: Decimal`（最大回撤，正数表示回撤幅度）、`sharpe_ratio: Decimal | None`（无风险利率假设 0）
- [ ] `run_backtest(params, price_history)`：纯函数
  - 价格历史为 `dict[code, list[tuple[date, Decimal]]]`，按 code 内按日期升序
  - 价格不足（任意 ETF 在调仓日往前 lookback+skip+1 交易日的数据缺失）→ 跳过该次调仓
  - **等权**配置：`weights = {code: Decimal(1) / top_n for code in selected}`
  - 调仓当日按 close 成交（无滑点）
  - 两次调仓之间**每日**按 close 重估持仓总市值，生成完整 NAV 曲线
- [ ] `save_backtest_run(session, params, result)`：写 `BacktestRun` 行
  - `etf_pool` / `metrics` 序列化为 JSON
  - `start_date` / `end_date` / `created_at` 字段填写正确
  - 失败抛 `IntegrityError` 等异常，不静默
- [ ] 单只 ETF 死亡 / 退市（中间某天起无数据）：**最后有数据的一日按 close 卖出，资金转为现金**；下个调仓日从其他 ETF 中再选；NAV 保持连续
- [ ] pytest 套件：
  - 已知输入的 NAV 数值正确（手算预期值，3 只 ETF 月末调仓）
  - 边界：单只 ETF → 全部资金进一只
  - 边界：所有 ETF 数据都不足 → `rebalance_log = []`，NAV 始终等于 initial_cash，metrics.total_return = 0
  - 边界：日期范围太短（< lookback + skip + 1）→ 同上
  - 调仓频率：MONTHLY 与 QUARTERLY 触发次数不同
  - 业绩指标：总收益、annualized、max_drawdown、sharpe 在已知输入下正确（手算）
  - 价格不足跳过：中途某只 ETF 数据断 → 跳过该次调仓（rebalance_log 缺一条），NAV 仍连续
  - 退市 ETF：中间某 ETF 数据终止 → 卖出转现金 + 后续不选
  - 持久化：`save_backtest_run` 正确写 ORM（mock session 验证）
- [ ] README 增补「回测引擎」章节：参数说明、调用示例、业绩指标公式

## 设计决策（脑暴沉淀）
1. **权重策略**：等权（每个入选 ETF 拿 1/top_n 资金）；不足 top_n 时按比例摊分剩余
2. **调仓日**：MONTHLY = 「该月最后一个交易日」；QUARTERLY = 「3/6/9/12 月最后交易日」（A 股业界惯例）
3. **退市 ETF**：最后有数据的一日按 close 卖出，资金转为现金；下个调仓日从其他 ETF 中再选
4. **净值跟踪**：每日跟踪（用每日 close 重估持仓总市值），生成完整 NAV 曲线，便于 max_drawdown 计算

## Status
- [x] 提案已确认