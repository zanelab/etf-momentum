# Spec: sync-cancel

## Context

M14 加的「同步 ETF 历史数据」按钮点了之后会触发一次 (code × date) 的循环同步。**目前没有取消机制**——一旦点了「开始同步」，前端只能看到顶部横幅的进度数字在涨，等它跑完才能做别的事。

后端当前实现：`trigger_sync` 是**同步阻塞**的（`backend/app/api/sync.py:135`），HTTP 请求要等 `sync_historical_for_pool` 返回才释放。客户端在这段时间内**无法发送第二个 HTTP 请求**——这是取消功能的核心约束。

本变更：
- 后端：用 FastAPI `BackgroundTasks` 把 sync 移到后台执行；trigger 立即返回；新增 `POST /cancel` 端点 + tracker cancel flag
- 前端：新增「取消」按钮 + `useCancelSync` mutation + 取消后 banner 变红

## ADDED Requirements

### Requirement: 同步必须能在中途取消

用户在同步进行中可以点击「取消」按钮中止当前 sync。下次 `useSyncStatus` 轮询返回 `is_running=false`、`in_progress=null`。

#### Scenario: 取消按钮在同步运行时显示
- Given 同步正在运行（`is_running=true`）
- When 用户停留在 `/dynamic-pool` 页面
- Then 「取消」按钮可见且可点

#### Scenario: 点击取消后状态清空
- Given 同步正在运行
- When 用户点击「取消」按钮
- Then 前端发送 `POST /api/sync/historical/cancel`
- And 后端返回 `{cancelled: true}` 200
- And 后端 sync 循环在下一个 (code, date) 边界停止
- And 下次 status 轮询（10s 内）看到 `is_running=false`
- And 顶部 banner 变为「已取消 — 已同步 X / Y」红色样式

#### Scenario: 取消后立刻可重新同步
- Given 用户刚取消了一次 sync
- When 用户重新选择日期范围点「开始同步」
- Then 新的 sync 立即开始（不被并发防御拦）
- And `tracker` 状态正确（cancel flag 清除，in_progress 重新填充）

#### Scenario: 同步未运行时调 cancel
- Given 当前无 sync 运行（`is_running=false`）
- When 客户端发送 `POST /api/sync/historical/cancel`
- Then 后端返回 400 `{"detail": "no sync running"}`

### Requirement: trigger 必须立即返回（不再阻塞）

`POST /api/sync/historical/trigger` 必须立即返回 200，sync 在后台任务中执行。

#### Scenario: trigger 响应时间 < 1s
- Given 用户点了「开始同步」
- When 后端收到 `POST /api/sync/historical/trigger`
- Then 后端在 1s 内返回响应（仅做验证 + 添加 BackgroundTask，不阻塞等 sync 完成）
- And 客户端立即关闭 Modal
- And 后台 sync 继续运行

#### Scenario: trigger 响应中 is_running=true
- Given 用户点了「开始同步」
- When 后端返回 trigger 响应
- Then 响应 `is_running=true` 且 `in_progress` 为空数组（`[]`）
- And `synced_count=0`（还没完成任何 bar）
- And `run_at` / `from_date` / `to_date` 字段正常

### Requirement: 取消后数据状态正确

取消时，sync 循环在 (code, date) 边界停止；落盘的 summary JSON 反映已完成的 rows。

#### Scenario: summary JSON 部分写入
- Given 同步运行到第 N / total 步时被取消
- When sync 循环 break
- Then summary JSON 写入 `backend/data/daily_sync/{to_date}.json`（与正常完成同路径）
- And JSON 包含已完成的 N 行
- And `n_etfs` 等于 N（不是 total）

#### Scenario: status 端点反映部分完成
- Given 同步被取消
- When 客户端 GET `/api/sync/historical/status`
- Then 返回的 `etfs` 列表里，已完成 code 显示 `status=ok` 或 `missing`（按 row 状态）
- And 未开始 code 显示 `status=never`（因为 summary JSON 不包含它们）

### Requirement: 修改不应破坏现有测试覆盖

#### Scenario: 前端 vitest 继续全绿
- Given 修改前 `npx vitest run` 58 个测试全部通过
- When 实施本变更后跑 `npx vitest run`
- Then 既有 58 个测试继续全部通过
- And 新增 ~3 个测试也通过

#### Scenario: 后端 pytest 继续全绿
- Given 修改前 `uv run pytest -q` 191 passed
- When 实施本变更后跑 `uv run pytest -q`
- Then 既有 191 个测试继续全部通过
- And 新增 ~6 个测试也通过

#### Scenario: tsc / build / ruff 干净
- Given 修改前所有 CI 命令干净
- When 实施本变更后跑同样命令
- Then 全部仍然干净

## MODIFIED Requirements

无。

## REMOVED Requirements

无。

## Cross-cutting

### 修改的文件清单

**Backend**：
- `backend/app/services/sync_progress.py`（**改**）：`_cancel_requested: bool` + `cancel()` / `is_cancel_requested()` / `reset_cancel()` 方法 + 既有测试覆盖新方法
- `backend/app/services/daily_sync.py`（**改**）：`sync_historical_for_pool` 在每 (code, date) 步后检查 `tracker.is_cancel_requested()`；cancel 时 break 双层循环；触发取消时不再 `tracker.clear()`（让前端通过 status 看到最后一次状态）
- `backend/app/api/sync.py`（**改**）：
  - `trigger_sync` 用 FastAPI `BackgroundTasks`；同步阻塞逻辑移除；返回 `is_running=true` 的 `SyncTriggerResult`
  - 新增 `POST /sync/historical/cancel` 端点
- `backend/app/schemas.py`（**可能改**）：`SyncTriggerResult` 保留；`SyncStatusResponse` 加 `is_cancelled: bool` 字段（Optional，向后兼容）

**Frontend**：
- `frontend/src/api/hooks.ts`（**改**）：
  - 新增 `useCancelSync()` mutation hook
  - `useSyncStatus` 返回类型扩展 `is_cancelled`
  - `useTriggerSync` 移除 `setQueryData` 副作用（避免与 cancel 状态竞速；status poll 已覆盖）
- `frontend/src/pages/DynamicPoolPage.tsx`（**改**）：新增「取消」按钮（header 中或 banner 内）；取消时调 `useCancelSync.mutate()`
- `frontend/src/components/SyncProgressBanner.tsx`（**改**）：接 `isCancelled` prop；true 时渲染红色「已取消」样式

### 不修改的文件

- `useDynamicPool`（已 M15 收敛）
- 其他 mutation hook 的 `onSuccess`（与 cancel 无关）
- 后端模型层（StaticPool / DynamicPoolEntry / MarketBarCache 表结构不变）
- 数据源实现（fixture / akshare 不动）

### 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| BackgroundTasks 跨重启丢失 | 中 | 进程重启后 tracker 为空，前端 status 看到 `is_running=false`；用户可重新触发。本期 mock 路径无影响 |
| 取消 race：cancel 在 trigger 返回前到达 | 低 | trigger 立即把 BackgroundTask 添加后才返回；cancel 端的 `tracker.is_active()` 检查看到的是 trigger 已设的状态。但 trigger 在添加 task 前会先 set in_progress（防御）；需要 implementer 决定 |
| 取消后落盘 summary 写入被 cancel flag 拦截 | 中 | 在 break 之后继续执行 summary 写入逻辑（不在 cancel check 范围内） |
| cancel flag 在多线程下的可见性 | 极低 | BackgroundTasks 跑在线程池；Python GIL 保证单布尔读写原子；无需加锁 |
| `useTriggerSync` 移除 setQueryData 后，前端看到「空状态」瞬间 | 中 | trigger 响应带 `is_running=true, in_progress=[]`；前端在 10s 内通过 status poll 拿到真实进度；UX 上不卡顿 |

---

**确认后进入 executing 阶段。**