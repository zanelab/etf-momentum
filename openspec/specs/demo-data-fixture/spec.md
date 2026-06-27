## ADDED Requirements

### Requirement: 演示数据集必须包含 15 只代表性 ETF

`backend/app/data/fixtures/demo_data.json` MUST 包含恰好 15 只 ETF 主数据，覆盖宽基 + 行业两类。

#### Scenario: 10 只宽基 ETF
- **WHEN** 解析 `etfs` 列表
- **THEN** MUST 包含以下 10 只宽基：510300 (沪深300) / 510500 (中证500) / 159915 (创业板) / 588000 (科创50) / 510880 (红利) / 510050 (上证50) / 159901 (深100) / 510330 (华夏300) / 510180 (上证180) / 159905 (深红利)

#### Scenario: 5 只行业 ETF
- **WHEN** 解析 `etfs` 列表
- **THEN** MUST 包含以下 5 只行业：512760 (半导体) / 512170 (医疗) / 512690 (酒) / 159928 (消费) / 518880 (黄金)

#### Scenario: ETF 总数校验
- **WHEN** 解析 `etfs` 列表长度
- **THEN** MUST 等于 15；不允许多也不允许少

### Requirement: 每只 ETF 必须包含足够长的日线历史

每只 ETF 的 `daily_prices[code]` MUST 包含至少 700 个交易日，覆盖最近 3 年。

#### Scenario: 日线数量下限
- **WHEN** 对每只 ETF 统计 `len(daily_prices[code])`
- **THEN** 每只 MUST ≥ 700 个交易日；fixture 中所有 ETF 的日线数允许 ±5% 差异（部分 ETF 在 akshare 上线较晚）

#### Scenario: 日线字段顺序一致
- **WHEN** 解析 `daily_prices[code]` 任意一行
- **THEN** MUST 按 `date` 升序排列；不要求日期连续（akshare 跳过停牌日）

### Requirement: Signal snapshot 必须覆盖 BUY / HOLD 两态

`signal_snapshot.rows` MUST 包含至少 1 个 BUY 与至少 1 个 HOLD 行。WATCH 行为数据依赖：当所有 15 只 ETF 都有 ≥ 273 个交易日时，WATCH 行为 0 个是正常预期。

#### Scenario: BUY / HOLD 覆盖
- **WHEN** 解析 `signal_snapshot.rows`
- **THEN** 15 行中 MUST 至少 1 行的 `action == "BUY"` 且至少 1 行 `action == "HOLD"`（top_n=5 → 5 BUY + 10 HOLD 是预期分布）

#### Scenario: WATCH 行（条件性）
- **WHEN** 任意行的 `action == "WATCH"`
- **THEN** `momentum_score == null` 且 `rank == null`
- **AND** 当 fixture 中每只 ETF 都有 ≥ 273 个交易日（演示数据集默认情况），WATCH 行为 0 个是允许的

### Requirement: 示例 pool 必须命名为「宽基三杰」

`pool` 字段 MUST 命名为「宽基三杰」，仅包含 3 只宽基 ETF（沪深300 + 中证500 + 创业板）。

#### Scenario: 池名称校验
- **WHEN** 解析 `pool.name`
- **THEN** MUST 等于 `"宽基三杰"`

#### Scenario: 池成员校验
- **WHEN** 解析 `pool.etf_codes`
- **THEN** MUST 等于 `["510300", "510500", "159915"]`（顺序可灵活，但 MUST 恰好包含这 3 个 code）