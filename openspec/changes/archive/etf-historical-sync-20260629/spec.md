# Spec: etf-historical-sync

## ADDED Requirements

### Requirement: 后端按池子并集逐只 ETF 同步历史数据

后端 MUST 在启动期（FastAPI `lifespan`）以及响应手动触发时，遍历 `static_pool ∪ dynamic_pool`（去重）中的每一只 ETF，调用数据源读取该 ETF 的最新一根 bar（mock 走 fixtures；akshare 走真实源），并把每只 ETF 的同步结果持久化到 `backend/data/daily_sync/{YYYY-MM-DD}.json`。

每只 ETF 的同步结果 MUST 包含 `status` 字段，取值：
- `ok`：bar 拉取成功
- `failed`：bar 拉取失败（含 `error` 字符串）
- `missing`：ETF 不在任何数据源（fixture 缺失 / akshare 查不到）

单只 ETF 同步失败 MUST NOT 阻塞其他 ETF 的同步——失败的 ETF 仍写入 `status: failed` + `error` 字段，但不影响其他行的写入。启动期同步任一阶段抛错 MUST 被 `lifespan` 捕获、记录日志、**不**让应用崩溃。

#### Scenario: 启动期同步全部成功

- **WHEN** 后端在 `lifespan` 启动时执行 `sync_historical_for_pool(codes=[...池子并集])`
- **AND** 所有 ETF 在数据源中均可查到最新 bar
- **THEN** 写入 `backend/data/daily_sync/{YYYY-MM-DD}.json`，其 `rows` 数组每一项 `status === "ok"`、`date` 等于该 ETF 最新 bar 的日期
- **AND** `n_etfs` 等于池子并集大小

#### Scenario: 单只 ETF 同步失败不影响其他 ETF

- **WHEN** 后端执行 `sync_historical_for_pool(codes=[A, B, C])`
- **AND** A 拉取成功、B 在数据源中查不到、C 抛网络异常
- **THEN** `rows` 数组包含三项：`A.status="ok"`、`B.status="missing"`、`C.status="failed"` + `error` 字段
- **AND** `n_etfs === 3`（失败的也计入）

#### Scenario: 启动期同步失败不阻塞服务

- **WHEN** `sync_historical_for_pool(...)` 在 `lifespan` 中抛异常
- **THEN** 异常被记录到日志
- **AND** 应用继续启动，HTTP 服务可访问

### Requirement: 后端暴露历史数据同步状态与触发端点

后端 MUST 暴露两个 HTTP 端点：

- `GET /api/sync/historical/status`：返回当前池子并集中每只 ETF 的最新同步信息，响应 schema：
  ```
  {as_of: YYYY-MM-DD, etfs: [{code, name, last_synced_date, status, error?}, ...]}
  ```
  `name` 字段从 `static_pool` 或 `dynamic_pool` 查表得到；查不到时为 `null`。`last_synced_date` 取该 ETF 同步摘要 JSON 中的 `date` 字段；尚未同步过则为 `null`。

- `POST /api/sync/historical/trigger`：执行一次同步（与 `lifespan` 行为一致），同步完成后返回与 `status` 端点相同 schema 的响应，外加 `synced_count: int`（status==="ok" 的数量）与 `run_at: ISO8601 datetime`。

#### Scenario: status 端点返回池子并集的所有 ETF

- **WHEN** `static_pool` 含 `[A, B]`、`dynamic_pool` 含 `[B, C]`
- **AND** 已执行过至少一次同步
- **THEN** `GET /api/sync/historical/status` 返回的 `etfs` 长度 === 3
- **AND** 每项含 `code`、`name`、`last_synced_date`、`status`

#### Scenario: trigger 端点触发同步后返回最新状态

- **WHEN** 客户端调用 `POST /api/sync/historical/trigger`
- **THEN** 后端执行同步（≤ 5s 完成 mock 路径）
- **AND** 返回 `{synced_count, run_at, etfs: [...]}`，其中 `etfs` 反映同步后的最新状态

### Requirement: 前端侧边栏新增"数据同步"页面

前端 MUST 在 `Sidebar` 中新增一个入口"数据同步"（path `/sync`），并新增 `frontend/src/pages/SyncStatus.tsx` 页面。页面 MUST 包含：

- 一个表格，列：`代码 | 名称 | 同步日期 | 状态 | 操作`
- 每行展示一只 ETF 的同步日期（YYYY-MM-DD 或 `—`）+ 状态徽章：`✓ 已同步`（绿）/ `⚠ 失败`（红）/ `— 缺失`（灰）
- 表格顶部一个"立即同步"按钮，点击后调用 `POST /api/sync/historical/trigger`，loading 期间按钮禁用并显示 spinner；完成后 refetch status 表
- 表格上方一行"上次同步：{as_of} {HH:MM:SS}"（取自 `status` 响应）
- 池子为空（dynamic + static 都没有 ETF）时显示 `暂无 ETF` 占位

#### Scenario: 表格展示所有 ETF 的同步状态

- **WHEN** `GET /api/sync/historical/status` 返回 5 只 ETF
- **AND** 用户访问 `/sync`
- **THEN** 页面渲染 5 行表格
- **AND** 每行展示 code、name、last_synced_date、status 徽章
- **AND** 顶部"上次同步"行显示响应中的 `as_of`

#### Scenario: 点击"立即同步"刷新表格

- **WHEN** 用户点击"立即同步"按钮
- **THEN** 按钮显示 loading 状态并禁用
- **AND** 请求 `POST /api/sync/historical/trigger`
- **AND** 收到响应后 refetch status，表格行反映新数据
- **AND** "上次同步"行更新为新 `as_of`

#### Scenario: 池子为空时显示占位

- **WHEN** `static_pool` 与 `dynamic_pool` 都为空
- **AND** 用户访问 `/sync`
- **THEN** 页面显示 `暂无 ETF`，不渲染表格
