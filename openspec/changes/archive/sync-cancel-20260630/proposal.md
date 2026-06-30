# Proposal: 同步取消功能

**变更名**: `sync-cancel`
**日期**: 2026-06-30
**状态**: - [x] 提案已确认（用户 2026-06-30 在 brainstorming 阶段确认）

## 已确认决策（brainstorming 2026-06-30）

| 问题 | 决策 |
|------|------|
| 同步执行模型 | **A. FastAPI `BackgroundTasks`**：trigger 立即返回，sync 以后台任务运行，cancel 单独 POST |
| 取消时机 | **下一 (code, date) 边界停止**：每完成一步后检查 flag，不强中断正在执行的 `_read_bar_for_date` |
| 取消后 UI | **Banner 变红 + 部分进度**：清除 in_progress 前保留最后一次 partial 状态；新增 `is_cancelled` 字段标识 |

## 背景（What）

M14 加的「同步 ETF 历史数据」按钮点了之后会触发一次 (code × date) 的循环同步。**目前没有取消机制**——一旦点了「开始同步」，前端只能看到顶部横幅的进度数字在涨，等它跑完才能做别的事。

问题：
- 误操作：选错日期范围（如不小心把 from 调到 2020-01-01），要等几秒甚至几十秒
- 调试：发现某只 code 数据有问题想中止看效果，目前只能等
- 长任务：真实数据源接入后单次同步可能跑几分钟，必须能中止

后端当前实现：`trigger_sync` 是**同步阻塞**的（`backend/app/api/sync.py:135`），HTTP 请求要等 `sync_historical_for_pool` 返回才释放。客户端在这段时间内**无法发送第二个 HTTP 请求**——这是取消功能的核心约束。

## 当前代码

`backend/app/api/sync.py:115-158` `trigger_sync`：

```python
@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(from_date, to_date):
    ...
    try:
        sync_historical_for_pool(codes=codes, from_date=from_date, to_date=to_date)
    except Exception as e:
        tracker.clear()
        raise HTTPException(500, detail=f"sync failed: {e}") from e
    ...
    return SyncTriggerResult(...)  # 阻塞到 sync 完才返回
```

`backend/app/services/sync_progress.py:SyncProgressTracker`：
- `_by_code: dict[str, ProgressInfo]`
- `set / get_all / clear / is_active`

`frontend/src/pages/DynamicPoolPage.tsx`：
- 按钮 `disabled={anyPending || isRunning}`
- 同步时显示 `<SyncProgressBanner>` + 行内 `<RowProgressBar>`

## 为什么是问题（Why）

- **同步阻塞模型限制取消**：当前 `sync_historical_for_pool` 是同步函数，client 必须等响应才能发 `cancel` 请求
- **真数据源后时间更长**：mock fixture 47×200 ≈ 10s；akshare 真实拉取可能跑几分钟
- **用户体验差**：点了错的范围只能后悔

## 范围（Scope）

**改动面**：后端（执行模型重构 + cancel endpoint）+ 前端（取消按钮 + mutation hook + 状态展示）

涉及：
- `backend/app/services/sync_progress.py`（**改**）：`tracker` 加 cancel flag + `cancel()` 方法
- `backend/app/services/daily_sync.py`（**改**）：`sync_historical_for_pool` 在每个 (code, date) 步前检查 cancel flag
- `backend/app/api/sync.py`（**改**）：trigger 改为后台执行 + 新增 `POST /cancel` 端点
- `frontend/src/api/hooks.ts`（**改**）：新增 `useCancelSync()` mutation
- `frontend/src/pages/DynamicPoolPage.tsx`（**改**）：新增取消按钮 + 取消后状态展示
- `frontend/src/components/SyncProgressBanner.tsx`（**可能改**）：取消后展示「已取消」提示

## 验收标准（Acceptance Criteria）

1. 同步进行中，前端能看到「取消」按钮
2. 点击「取消」后，下次 status 轮询（10s 内）看到 `is_running=false`，`in_progress=null`
3. 后端 sync 循环在取消后**下一个 (code, date) 边界**停止（不强制立即中断正在执行的 bar 读取——`_read_bar_for_date` 是 I/O 同步操作，中断语义复杂）
4. 取消后写入的部分 summary JSON 仍可读（标记部分完成）
5. 并发 cancel 防御：sync 未运行时调 cancel 返回 400
6. 取消后用户可以立即发起新 sync
7. 既有 191 后端测试 + 58 前端测试继续通过（不修改既有断言）
8. 新增 ~6 后端测试 + ~3 前端测试
9. tsc / build / ruff 干净

## 非范围（Out of Scope）

- 取消后回滚已写入的 (code, date) 状态（summary 写盘设计为可幂等覆盖，保持简单）
- 取消后清理已落盘的 fixture 数据（mock 路径无意义；真实数据源是另一回事）
- 同步进度细分到「正在读取 fixture 510300.XSHE 的 2024-04-19」（已是当前实现，cancel 只在 iteration 边界检查）
- 取消后给用户展示「已同步 X / Y 个 code」等富摘要（summary JSON 仍可读，前端读它就行）
- 真数据源接入（akshare 接入是独立变更）

## 替代方案（仅记录，最终走 A）

- **A（推荐）**：FastAPI `BackgroundTasks` + tracker cancel flag。后台执行 sync，trigger 立即返回，cancel 单独 POST。
- **B**：用 `threading.Thread` 启后台线程。比 BackgroundTasks 灵活但要自己管生命周期，复杂。
- **C**：维持同步执行，cancel 端点返回错误「sync in progress, please wait」。不是真正的 cancel，等于不做。

→ **A**

## 设计文档

详见 `openspec/changes/sync-cancel/design.md`（brainstorming 阶段填充）。

---

**下一步**：用户确认后进入 brainstorming 阶段（关键问题：执行模型、取消时机、状态展示）。