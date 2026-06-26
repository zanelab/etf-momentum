# Spec: 后端 REST API

## ADDED Requirements

### Requirement: ETF 列表
`GET /api/v1/etfs?limit=N&offset=M&category=...` 返回分页 ETF 列表。

#### Scenario: 空库
- Given ETF 表为空
- When 调用
- Then 200 + `{items: [], total: 0, limit: 50, offset: 0}`

#### Scenario: 分页
- Given ETF 表有 120 条
- When `?limit=50&offset=0`
- Then 200 + `{items: [前 50], total: 120, limit: 50, offset: 0}`

#### Scenario: category 过滤
- Given ETF 表混合 category
- When `?category=指数`
- Then 200 + items 全是该 category

#### Scenario: limit 越界 clamp
- Given 任意 ETF
- When `?limit=1000`
- Then limit 在响应里被 clamp 到 500

### Requirement: ETF 详情
`GET /api/v1/etfs/{code}` 返回单只 ETF。

#### Scenario: 存在
- Given ETF 510300 已存在
- When 调用
- Then 200 + ETF 详情

#### Scenario: 不存在
- Given ETF 999999 不存在
- When 调用
- Then 404

### Requirement: ETF 日线价格
`GET /api/v1/etfs/{code}/prices?start=...&end=...&limit=...` 返回日线历史。

#### Scenario: 完整日期范围
- Given ETF 510300 有 300 天历史
- When `?start=2024-01-01&end=2024-12-31&limit=500`
- Then 200 + prices 数组（按 date 升序）

#### Scenario: 默认 limit
- Given 1 万条历史
- When 不传 limit
- Then 默认返回前 500 条（按 date desc）

### Requirement: Signal 查询
`GET /api/v1/signals?date=YYYY-MM-DD` 与 `GET /api/v1/signals/latest` 返回 signal snapshot。

#### Scenario: 指定日期
- Given 2024-12-31 有 5 条 snapshot
- When `?date=2024-12-31`
- Then 200 + `{date, rows: [5 rows]}`

#### Scenario: 不传 date → 最新
- Given 2024-12-31 有 5 条，2024-12-30 有 3 条
- When 不传 date
- Then 200 + 2024-12-31 的 snapshot

#### Scenario: 无 snapshot
- Given DB 无任何 snapshot
- When 调用 latest
- Then 200 + `{date: null, rows: []}` 或 200 + empty

#### Scenario: 显式 latest
- Given 多日 snapshot
- When `/signals/latest`
- Then 200 + DB MAX(date) 的 snapshot

### Requirement: POST Backtest
`POST /api/v1/backtest` 提交新回测；同步执行 `run_backtest` + `save_backtest_run`；返回完整 BacktestRun JSON。

#### Scenario: happy path
- Given 3 只 ETF 池 + 完整历史 + 合法参数
- When POST
- Then 200 + 含 `id` + 完整 metrics + etf_pool

#### Scenario: etf_pool 为空
- Given 任何情况
- When POST `{etf_pool: []}`
- Then 422（Pydantic 校验）

#### Scenario: 数据不足
- Given 某只 ETF DB 无历史
- When POST
- Then 422（详细说明缺哪只 ETF）

#### Scenario: start > end
- Given 任何情况
- When POST `{start: 2024-12-31, end: 2024-01-01}`
- Then 422

### Requirement: GET Backtest 列表
`GET /api/v1/backtest?limit=N&offset=M` 返回 BacktestRun 列表（按 created_at desc）。

#### Scenario: 空库
- Given 无回测
- When 调用
- Then 200 + `{items: [], total: 0}`

#### Scenario: 分页
- Given 30 个回测
- When `?limit=10&offset=0`
- Then 200 + 前 10 条（最新优先）

### Requirement: GET Backtest 详情
`GET /api/v1/backtest/{id}` 返回单条 BacktestRun 含 metrics。

#### Scenario: 存在
- Given BacktestRun id=1
- When 调用
- Then 200 + 完整 JSON（含 metrics 字典）

#### Scenario: 不存在
- Given id=999 不存在
- When 调用
- Then 404

### Requirement: GET Backtest NAV
`GET /api/v1/backtest/{id}/nav` 返回 NAV 序列（前端画图用）。

#### Scenario: 存在
- Given BacktestRun id=1 有 100 天 NAV
- When 调用
- Then 200 + `{id: 1, nav_series: [{date, nav}, ...]}`

#### Scenario: 不存在
- Given id=999 不存在
- When 调用
- Then 404

### Requirement: POST Sync
`POST /api/v1/sync/etfs` 与 `POST /api/v1/sync/prices` 触发数据同步。

#### Scenario: sync etfs
- Given akshare 客户端可用
- When POST `/sync/etfs`
- Then 200 + `{upserted: N, fetched: M}`

#### Scenario: sync prices 完整参数
- Given 3 只 ETF 池
- When POST `/sync/prices {codes, start, end}`
- Then 200 + `{succeeded: 3, failed: 0}`

#### Scenario: sync prices 部分失败
- Given 5 只 ETF，2 只 akshare 抛错
- When POST `/sync/prices {codes: 5 只}`
- Then 200 + `{succeeded: 3, failed: 2}`

### Requirement: CORS
FastAPI 应用启用 CORS middleware，允许 Vite dev 来源。

#### Scenario: preflight OPTIONS
- Given 浏览器发起 preflight
- When OPTIONS 请求带 `Origin: http://localhost:5173`
- Then 200 + `Access-Control-Allow-Origin` 头

#### Scenario: 实际 GET 跨域
- Given 同源或 `Origin: localhost:5173`
- When GET `/api/v1/etfs`
- Then 200 + CORS 头

### Requirement: Decimal 序列化
所有 Pydantic response 中的 Decimal 字段序列化为 string。

#### Scenario: 价格序列化为 string
- Given ETF close = Decimal("4.123")
- When GET `/etfs/{code}/prices`
- Then JSON 中 `close: "4.123"`（string，不是 number）

#### Scenario: metrics 序列化为 string
- Given metrics total_return = Decimal("0.200000")
- When GET `/backtest/{id}`
- Then JSON 中 `total_return: "0.200000"`（string）

### Requirement: pytest 测试覆盖
新增 `tests/test_api_*.py` 至少 25 个端点测试 + 3 个 schema 单元测试。

#### Scenario: 全套通过
- Given backend 目录运行 `uv run pytest`
- When 收集所有 `tests/test_*.py`
- Then 全部通过（146 原有 + 新增 ≥ 28 = ≥ 174）

### Requirement: README 增补 REST API 章节
backend/README.md 新增「REST API」章节：端点表 + curl 示例 + 错误格式说明。

#### Scenario: README 含端点表
- Given 阅读 backend/README.md
- When 查找「REST API」章节
- Then 含完整端点表（method/path/用途/参数/response schema）+ 至少 2 个 curl 示例
