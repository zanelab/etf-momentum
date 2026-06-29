# Spec: add-sync-progress-ui

## Context

`/dynamic-pool` 页面点击「同步 ETF 历史数据」后，用户只能看到禁用按钮 + 「同步中…」文本，看不到：
- 正在处理哪个 ETF 代码
- 该代码的日期范围
- 整体进度（X / Y 个 (code, date) 已完成）

后端 `sync_historical_for_pool` 当前只对每个 code 读「最新一根 K 线」就落盘汇总（`backend/app/services/daily_sync.py:43`），没有任何 in-progress 状态可供 UI 暴露。`trigger_sync` 也不接受日期范围参数（`backend/app/api/sync.py:102`）。

本变更：
- 后端把同步重构成「按 (code, date) 细粒度循环」，期间维护进程内 `SyncProgressTracker` 单例；`trigger_sync` 接受 from/to 日期范围；`status` 端点合并 in-progress
- 前端新增 `DateRangePicker` 弹窗；`DynamicPoolPage` 接入日期范围 + 顶部进度横幅 + 行内进度
- 复用 `useSyncStatus` 10s 轮询（现在终于有意义了）

详细设计见 `design.md`。本 spec 聚焦「需求 + Scenario」。

## ADDED Requirements

### Requirement: 同步 ETF 历史数据前必须选择日期范围

用户点击「同步 ETF 历史数据」按钮后，UI 必须弹出日期范围选择 Modal。Modal 必须包含：
- `from_date`：开始日期（`<input type="date">`）
- `to_date`：结束日期（`<input type="date">`）
- 「开始同步」和「取消」两个按钮

#### Scenario: Modal 默认值
- Given 用户在 `/dynamic-pool` 页面
- When 用户点击「同步 ETF 历史数据」按钮
- Then Modal 弹出
- And `from_date` 默认值为 today - 30 天
- And `to_date` 默认值为 today

#### Scenario: 校验 - from_date 晚于 to_date
- Given Modal 已打开
- When 用户把 `from_date` 改成晚于 `to_date`
- Then 「开始同步」按钮被禁用
- And Modal 内显示错误提示 `from_date 必须早于或等于 to_date`

#### Scenario: 校验 - 日期范围超过 730 天
- Given Modal 已打开
- When 用户选择的 from/to 跨度 > 730 天
- Then 「开始同步」按钮被禁用
- And Modal 内显示错误提示 `日期范围过大（最多 730 天）`

#### Scenario: 确认提交
- Given Modal 已打开且输入合法
- When 用户点击「开始同步」按钮
- Then 触发 `useTriggerSync.mutate({ from_date, to_date })`
- And POST 请求 URL 包含 `?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
- And Modal 保持打开（不可关闭）直到 mutation 结束

#### Scenario: 后端返回 400
- Given POST 返回 400
- When 响应到达
- Then Modal 内顶部显示错误详情
- And 「开始同步」按钮恢复可点
- And 用户可以修改日期后重试

#### Scenario: 同步完成
- Given mutation 成功
- When 响应到达
- Then Modal 自动关闭
- And `["sync-historical-status"]` 被 invalidate

### Requirement: 同步进行中必须显示细粒度进度

同步运行期间，UI 必须显示：
- 顶部进度横幅：总进度 X / Y + 当前处理的 code 及其在日期范围中的位置
- 表格内：当前正在处理的 code 行内显示行内进度条 + 日期范围

#### Scenario: 顶部进度横幅
- Given 同步正在运行（`is_running=true`，`in_progress` 非空）
- When 用户停留在 `/dynamic-pool` 页面
- Then 表格顶部显示进度横幅
- And 横幅包含：已完成的 (code, date) 总数 X / Y（百分比）
- And 横幅包含：当前正在处理的 code 名称及其 `current_date` / `total_days`

#### Scenario: 行内进度条
- Given 同步正在运行
- When `in_progress` 数组包含某个 code
- Then 该 code 对应表格行的「历史同步状态」列显示行内进度条
- And 文本显示 `current_date / total_days`（例如 `2024-01-15 / 31 天`）

#### Scenario: 同步完成清除进度
- Given 同步刚完成
- When `useSyncStatus` 轮询返回新数据
- And `is_running=false` 且 `in_progress=null`
- Then 顶部进度横幅消失
- And 所有行恢复显示 `SyncStatusBadge`（ok / failed / never）

#### Scenario: 多 tab 同步状态可见
- Given 用户在 `/dynamic-pool` 页面
- And 用户切到别的 tab 停留一会儿
- When 用户切回 `/dynamic-pool` tab
- Then `refetchOnWindowFocus` 触发 refetch
- And UI 显示最新的进度（不会因为离开 tab 而错过中间状态）

### Requirement: 同步期间按钮必须 disabled

`is_running=true` 期间，「同步 ETF」和「同步 ETF 历史数据」按钮必须都 disabled。

#### Scenario: 同步运行中点击按钮无效
- Given 同步正在运行（`is_running=true`）
- When 用户点击「同步 ETF」或「同步 ETF 历史数据」按钮
- Then 按钮不可点击（`disabled` 属性为 true）

#### Scenario: 同步完成恢复可点
- Given 同步刚完成
- When 轮询返回 `is_running=false`
- Then 两个按钮恢复可点

#### Scenario: 并发 trigger 防御
- Given 同步正在运行
- When 另一客户端（直接 curl / 别的 tab）POST `/api/sync/historical/trigger`
- Then 后端返回 400 `sync already running`

### Requirement: 修改不应破坏现有测试覆盖

#### Scenario: 前端 vitest 继续全绿
- Given 修改前 `npx vitest run` 输出 38 个测试全部通过
- When 实施本变更后跑 `npx vitest run`
- Then 既有 38 个测试继续全部通过（不修改既有断言）
- And 新增约 6 个测试也全部通过

#### Scenario: 后端 pytest 继续全绿
- Given 修改前 `uv run pytest -q` 输出 172 passed
- When 实施本变更后跑 `uv run pytest -q`
- Then 既有 172 个测试继续全部通过
- And 新增约 6 个测试也全部通过

#### Scenario: tsc / build / ruff 干净
- Given 修改前 `npx tsc --noEmit && npm run build` 干净
- And `uv run ruff check` 干净
- When 实施本变更后跑同样的命令
- Then 全部仍然干净

## MODIFIED Requirements

无。

## REMOVED Requirements

无。

## Cross-cutting

### 修改的文件清单

**Backend（新增 1，修改 4）**：
- `backend/app/services/sync_progress.py`（**新**）：`SyncProgressTracker` 单例 + `ProgressInfo` 模型
- `backend/app/services/daily_sync.py`（**改**）：
  - `sync_historical_for_pool(codes, from_date, to_date)` — 必填 from/to
  - 新增 `_read_bar_for_date(code, target_date)`
  - `sync_today(target_date)` 内部改为传 `from_date=to_date=target_date`
- `backend/app/api/sync.py`（**改**）：`trigger_sync` 接受 query params；`get_sync_status` 合并 in_progress
- `backend/app/schemas.py`（**改**）：`SyncStatusResponse` 加 `in_progress` / `is_running`；`SyncTriggerResult` 加 `from_date` / `to_date`
- `backend/app/main.py`（**改**）：startup hook 传入默认 30 天窗口

**Frontend（新增 3，修改 3）**：
- `frontend/src/components/DateRangePicker.tsx`（**新**）
- `frontend/src/components/SyncProgressBanner.tsx`（**新**）
- `frontend/src/components/RowProgressBar.tsx`（**新**）
- `frontend/src/api/hooks.ts`（**改**）：`useTriggerSync` 接受 `{from_date, to_date}` 变量
- `frontend/src/pages/DynamicPoolPage.tsx`（**改**）：接入 picker + 进度条
- `frontend/src/components/SyncStatusBadge.tsx`（**可能改**：仅当 in-progress code 需要不同渲染时调整；本期大概率不改）

### 不修改的文件

- `frontend/src/api/hooks.ts` 的 `useSyncStatus` 10s 轮询（保留）
- 其他 mutation hook 的 `onSuccess`（已正确）
- 其他合法轮询 hook（useScreeningToday / usePortfolio / useSignalsToday / useBacktestTask / useHealthStats）
- `useDynamicPool` 的 5s 轮询（独立 PR 处理）

### 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 同步跑太久，浏览器 timeout | 中 | mock fixture 读取快（每 (code, date) < 1ms），47 codes × 200 days ≈ 9400 ops，预计 < 10s；MAX_RANGE_DAYS=730 限制 |
| uvicorn --reload 丢状态 | 低 | 文档说明；reload 后状态清空但前端看到 `is_running=false` 后重置 |
| `SyncStatusResponse` 新字段破坏既有测试 | 低 | 新字段 Optional（`in_progress: list[ProgressInfo] \| None = None`），mock 旧 schema 仍合法 |
| `useTriggerSync` 入参变化破坏既有测试 | 中 | spec.md 已列出受影响测试（`DynamicPoolPage.test.tsx`），plan 中显式更新 |
| 真实数据源接入后性能 | 低 | 本期是 mock；真实数据源是 out-of-scope，单独 PR |

---

**确认后进入 executing 阶段。**
