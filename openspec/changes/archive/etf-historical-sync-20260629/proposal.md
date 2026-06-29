# Proposal: etf-historical-sync

## What

为策略池中的所有 ETF 同步历史数据（每只 ETF 最新一根 bar 的日期与 OHLCV），并在前端侧边栏新增"数据同步"页面，逐只 ETF 展示同步到的日期、状态以及支持手动触发同步。

具体行为：
- 后端在启动时 + 用户点击"立即同步"按钮时，遍历 `static_pool ∪ dynamic_pool` 去重后的所有 ETF，调用数据源读取最新一根 bar（mock 走 fixtures；akshare 走真实源），把每只 ETF 的 `{code, date, close, volume, money, status}` 持久化到 `backend/data/daily_sync/{YYYY-MM-DD}.json`。
- 新增 `GET /api/sync/historical/status` 返回每只 ETF 的最新同步信息（`code | name | last_synced_date | is_stale | status`）。
- 新增 `POST /api/sync/historical/trigger` 同步触发端点，返回 `{synced_count, run_at, etfs: [...]}`。
- 前端侧边栏新增一项"数据同步"（route `/sync`），表格展示所有 ETF 的同步状态，顶部一个"立即同步"按钮 + 上次同步时间。

## Why

当前 mock 同步已经能产出 `backend/data/daily_sync/{date}.json` 摘要，但：
- 摘要文件**没有 API 暴露**给前端，前端无法直接观察每只 ETF 同步到了哪一天。
- 摘要**不区分 ETF 状态**：失败/缺失/陈旧混在同一个数组里。
- 摘要**不含 ETF 名称**（仅有 code），需要前端再用 pool 做 name lookup。
- 触发方式只有启动时自动跑一次，没有手动按钮；当数据看起来"陈旧"时用户无处可点。

这些问题让"这只 ETF 是不是真的同步上了最新一天的数据？"无法回答——在 akshare 路径下，单元失败会被整体吞掉，前端只看到"今天没动"，但不知道是哪些 ETF 失败了。

## Scope

- [x] backend
- [x] frontend

后端具体：
- 改造 `backend/app/services/daily_sync.py`：输入改为 `codes: list[str]`，按 code 逐个拉最新 bar（保留失败信息：写入 `status: "ok" | "failed" | "missing"` 与 `error` 字段），输出 schema 与现状一致但 `rows` 字段允许带 `status: failed` 的项。
- 新增 `backend/app/api/sync.py`（或在 `market.py` 内加 router）：`GET /api/sync/historical/status` 与 `POST /api/sync/historical/trigger`。
- 新增 `backend/app/schemas.py` 子模型：`HistoricalSyncStatus`、`HistoricalSyncTriggerResult`。
- 在 `backend/app/main.py` 启动 lifespan 中，把现有的 `sync_today()` 替换为新的 `sync_historical_for_pool(static_pool, dynamic_pool)`（行为等价，因为默认 fixture 全在 pool 里）。
- 新增/更新测试：`test_daily_sync.py` 增补失败路径与按 code 过滤；新增 `test_sync_api.py` 覆盖两个端点。

前端具体：
- 新增 `frontend/src/pages/SyncStatus.tsx`：表格 + 立即同步按钮 + 上次同步时间；表头 `代码 | 名称 | 同步日期 | 状态 | 操作`。
- 在 `frontend/src/components/Sidebar.tsx` 与 `AppShell.tsx` 注册新入口"数据同步" → `/sync`（不动 top nav；2-entry 顶导已是 dashboard-flatten 的明确约束）。
- 在 `frontend/src/App.tsx` 注册 `<Route path="/sync" element={<SyncStatus />} />`。
- 在 `frontend/src/api/hooks.ts` 增补 `useSyncStatus()` 与 `useTriggerSync()`。
- 新增 `frontend/src/pages/__tests__/SyncStatus.test.tsx`：覆盖（a）表格渲染；（b）空 pool 状态；（c）触发同步后按钮 loading + 完成后刷新。

## Acceptance Criteria

- [ ] `POST /api/sync/historical/trigger` 在 5s 内返回（mock 路径），响应体含 `synced_count`、`run_at`、`etfs: [...]`。
- [ ] `GET /api/sync/historical/status` 返回的 etf 列表与 `static_pool ∪ dynamic_pool`（去重）一一对应；每项含 `code | name | last_synced_date | status`。
- [ ] 单只 ETF 拉取失败时，`status: "failed"` + `error` 字段被记录；其他 ETF 仍正常同步（不互相阻塞）。
- [ ] 启动期同步失败时服务**不崩溃**（lifespan 捕获异常、记录日志、继续启动）。
- [ ] 前端 `/sync` 页面表格行数 = 池子并集大小；每行展示同步日期（YYYY-MM-DD）+ 状态徽章（✓ 已同步 / ⚠ 失败 / — 缺失）。
- [ ] 点击"立即同步"按钮触发 POST，loading 期间按钮禁用；完成后自动 refetch status 表，UI 反映新结果。
- [ ] 池子为空时（dynamic = [] 且 static = []），页面显示 `暂无 ETF` 占位。
- [ ] 后端单测 ≥ 6 个（按 code 过滤 / 失败保留 / status 端点 / trigger 端点 / 启动失败容错 / 去重）。
- [ ] 前端单测 ≥ 3 个（表格 / 空态 / 触发后刷新）。
- [ ] `uv run pytest -q` 通过；`npm test` 通过；`tsc --noEmit` 通过；`ruff check` 通过。
- [ ] SPEC 与 devlog 同步（项目级 `spec/requirements.md` 与 `spec/devlog.md` 增补新条目）。

## Status

- [x] 提案已确认
