# Proposal: 历史同步进度 UI

**变更名**: `add-sync-progress-ui`
**日期**: 2026-06-29
**状态**: - [x] 提案已确认（用户 2026-06-29 在 brainstorming 阶段确认）

## 背景（What）

`/dynamic-pool` 页面点击「同步 ETF 历史数据」后，用户只能看到禁用按钮 + 「同步中…」文本，看不到：
- 正在处理哪个 ETF 代码
- 该代码的日期范围
- 整体进度（X / Y 个 (code, date) 已完成）

后端 `sync_historical_for_pool` 当前只对每个 code 读「最新一根 K 线」就落盘汇总，没有任何 in-progress 状态可供 UI 暴露。

## 当前代码

`backend/app/services/daily_sync.py:43` `sync_historical_for_pool(codes, target_date=None)`：
- 循环 codes
- 每个 code 调一次 `_read_latest_bar` → 拿 CSV 最后一行
- 写汇总 JSON

`backend/app/api/sync.py:102` `trigger_sync()`：
- 同步阻塞调用 `sync_historical_for_pool`
- 返回 `SyncTriggerResult { as_of, etfs, synced_count, run_at }`

`backend/app/api/sync.py:93` `get_sync_status()`：
- 读汇总 JSON，没有 in-progress 概念

`frontend/src/pages/DynamicPoolPage.tsx`：
- 按钮 `disabled={anyPending}`（基于 `useTriggerSync().isPending`）
- 没有进度展示

## 为什么是问题（Why）

- **黑盒同步**：用户点了按钮后不知道系统在工作还是卡死
- **没有范围控制**：当前实现就是「拉最新一天 K 线」，不能补历史
- **没有取消机制**：跑错了也无法中断（本期不做取消，但至少要有可见进度）

## 范围（Scope）

**改动面**：后端 + 前端

涉及：
- `backend/app/services/sync_progress.py`（**新**）— 进程内进度跟踪器
- `backend/app/services/daily_sync.py`（**改**）— `sync_historical_for_pool` 接受 `from_date`/`to_date`，每 (code, date) 更新 tracker
- `backend/app/api/sync.py`（**改**）— `trigger_sync` 接受 query 参数，`get_sync_status` 合并 in-progress
- `backend/app/schemas.py`（**改**）— `SyncStatusResponse` 加 `in_progress` 字段
- `backend/app/main.py:49`（**改**）— startup hook 传入默认 30 天窗口
- `frontend/src/components/DateRangePicker.tsx`（**新**）— 日期范围 Modal
- `frontend/src/components/SyncProgressBanner.tsx`（**新**）— 顶部进度横幅
- `frontend/src/components/RowProgressBar.tsx`（**新**）— 行内进度条
- `frontend/src/pages/DynamicPoolPage.tsx`（**改**）— 接入 picker + 进度条
- `frontend/src/api/hooks.ts`（**改**）— `useTriggerSync` mutation 接受 `{from_date, to_date}`

## 验收标准（Acceptance Criteria）

1. 点击「同步 ETF 历史数据」按钮 → 弹出 DateRangePicker Modal，含 from/to 两个 date input
2. Modal 默认 from = today-30，to = today
3. 校验失败时 Modal 内显示错误，「开始」按钮禁用
4. 确认后 POST 请求 URL 含 `?from_date=...&to_date=...`
5. 后端返回 400 时 Modal 内显示错误详情
6. 同步运行时，表格顶部显示「同步进行中 X/Y — 当前 code 在 day M/N」
7. 当前正在处理的 code 行内显示行内进度条 + 日期范围
8. 同步完成 → invalidate `["sync-historical-status"]` → 表格更新，进度条消失
9. 同步期间两个按钮均 disabled
10. 既有 172 后端测试 + 38 前端测试**继续通过**（不修改既有断言）
11. 新增 ~6 后端测试 + ~6 前端测试**全部通过**
12. tsc --noEmit 干净 / npm run build 成功 / ruff check 干净

## 非范围（Out of Scope）

- 取消同步功能（`POST /api/sync/historical/cancel` + UI 按钮）
- `useDynamicPool` 的 5s 轮询删除（独立的极小变更，下个 PR 单独做）
- 真实数据源接入（akshare / tushare）
- WebSocket / SSE 实时推送（本期用 10s 轮询）
- Dashboard 上的"上次同步"卡片扩展

## 替代方案（仅记录，最终走 A）

- **A（推荐）**：内存进度状态 + 10s 轮询。最小改动，复用现有架构。
- **B**：BackgroundTasks + 进度文件，POST 立即返回，状态 reload 不丢。实现复杂度更高。
- **C**：SSE 实时推送。引入新传输层，overkill for mock。

→ **A**

## 设计文档

详见 `openspec/changes/add-sync-progress-ui/design.md`（已通过 brainstorming 4 节确认）

---

**下一步**：用户确认 design.md 后，写 spec.md + plan.md 进入 executing 阶段。
