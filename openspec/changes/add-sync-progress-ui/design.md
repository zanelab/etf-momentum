# Design: add-sync-progress-ui

**状态**: - [x] 设计已确认（用户 2026-06-29 在 brainstorming 阶段确认）
**变更名**: `add-sync-progress-ui`
**日期**: 2026-06-29

## 概述

`/dynamic-pool` 页面触发「同步 ETF 历史数据」时，用户只能看到禁用按钮 + 「同步中…」文本，看不到：
1. 正在处理哪个 ETF 代码
2. 该代码的日期范围
3. 整体进度（X / Y 个 (code, date) 已完成）

当前后端 `sync_historical_for_pool` 只读每 code 的「最新一根 K 线」就落盘汇总，没有任何 in-progress 状态可供 UI 暴露。本变更：

- **后端**：把同步重构成「按 (code, date) 细粒度循环」，期间维护进程内 `SyncProgressTracker` 单例；`trigger_sync` 接受 from/to 日期范围；`status` 端点合并 in-progress 数据。
- **前端**：新增 `DateRangePicker` 弹窗组件；`DynamicPoolPage` 接入日期范围 + 顶部进度横幅 + 行内进度条；`useTriggerSync` mutation 改为接受 `{from_date, to_date}`。
- **复用**：保留 `useSyncStatus` 10s 轮询（现在终于有意义了 — 每次轮询能拿到最新进度）。

## 用户确认的范围选择

| 问题 | 决定 |
|------|------|
| 进度语义 | 给同步加日期范围功能（不是只显示 code 计数） |
| 日期范围来源 | 用户手动选（UI 日期选择器） |
| 同步粒度 | 细粒度：逐 (code, date) |
| 架构 | 内存状态 + 10s 轮询（方案 A） |
| 取消同步 | 不做（本变更） |

## 技术方案

### 后端

**1. 新增 `backend/app/services/sync_progress.py`**

```python
"""Process-singleton in-memory tracker for in-progress historical sync."""
from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel


class ProgressInfo(BaseModel):
    code: str
    from_date: date
    to_date: date
    current_date: date
    total_days: int
    completed_days: int
    overall_index: int
    overall_total: int
    started_at: datetime


class SyncProgressTracker:
    """dict[code, ProgressInfo] backed by a module-level singleton."""

    def __init__(self) -> None:
        self._by_code: dict[str, ProgressInfo] = {}

    def set(self, code: str, info: ProgressInfo) -> None:
        self._by_code[code] = info

    def get_all(self) -> list[ProgressInfo]:
        return list(self._by_code.values())

    def clear(self) -> None:
        self._by_code.clear()

    def is_active(self) -> bool:
        return bool(self._by_code)


# module-level singleton
tracker = SyncProgressTracker()
```

**2. 修改 `backend/app/services/daily_sync.py`**

```python
def sync_historical_for_pool(
    codes: list[str],
    from_date: date,
    to_date: date,
) -> Path:
    """For each code, iterate [from_date, to_date], update progress tracker.

    Writes the same per-day CSV-backed summary (mock) but records progress
    for every (code, date) step so the UI can render live status.
    """
    from app.services.sync_progress import ProgressInfo, tracker

    total_days = (to_date - from_date).days + 1
    overall_total = total_days * len(codes)
    overall_index = 0
    started_at = datetime.now(timezone.utc)
    rows: list[dict] = []

    for code in codes:
        for offset in range(total_days):
            current_date = from_date + timedelta(days=offset)
            try:
                bar = _read_bar_for_date(code, current_date)  # new helper
            except Exception as e:
                rows.append({
                    "code": code, "date": current_date.isoformat(),
                    "status": "failed", "error": str(e),
                    "close": None, "volume": None, "money": None,
                })
            else:
                if bar is None:
                    rows.append({
                        "code": code, "date": current_date.isoformat(),
                        "status": "missing", "error": None,
                        "close": None, "volume": None, "money": None,
                    })
                else:
                    rows.append({"code": code, "date": current_date.isoformat(),
                                 **bar, "status": "ok", "error": None})

            overall_index += 1
            tracker.set(code, ProgressInfo(
                code=code,
                from_date=from_date, to_date=to_date,
                current_date=current_date,
                total_days=total_days, completed_days=offset + 1,
                overall_index=overall_index, overall_total=overall_total,
                started_at=started_at,
            ))

    # write summary
    payload = {"date": to_date.isoformat(), "n_etfs": len(codes), "rows": rows}
    out_path = SYNC_DIR / f"{to_date.isoformat()}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False))
    return out_path
```

新增辅助函数 `_read_bar_for_date(code, target_date)`：
- 复用现有 `_read_latest_bar` 的 CSV 读取逻辑
- 增加按 `target_date` 过滤行（`df[df["date"] == target_date]`）
- 找不到返回 `None`（状态变成 `missing` 而非 `failed`）

**3. 修改 `backend/app/schemas.py`**

```python
class ProgressInfo(BaseModel):
    code: str
    from_date: date
    to_date: date
    current_date: date
    total_days: int
    completed_days: int
    overall_index: int
    overall_total: int
    started_at: datetime


class SyncStatusResponse(BaseModel):
    as_of: str | None
    etfs: list[SyncETFStatus]
    in_progress: list[ProgressInfo] | None = None  # 新
    is_running: bool = False                         # 新


class SyncTriggerResult(SyncStatusResponse):
    synced_count: int
    run_at: datetime
    from_date: date                                  # 新
    to_date: date                                    # 新
```

**4. 修改 `backend/app/api/sync.py`**

```python
from datetime import date as date_type
from fastapi import Query

from app.services.sync_progress import ProgressInfo, tracker

MAX_RANGE_DAYS = 730


@router.post("/sync/historical/trigger", response_model=SyncTriggerResult)
def trigger_sync(
    from_date: date_type = Query(...),
    to_date: date_type = Query(...),
) -> SyncTriggerResult:
    """Run a fresh historical sync for the given date range."""
    if from_date > to_date:
        raise HTTPException(400, "from_date must be ≤ to_date")
    if from_date > date_type.today():
        raise HTTPException(400, "from_date cannot be in the future")
    if (to_date - from_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(400, f"date range too large (max {MAX_RANGE_DAYS} days)")
    if tracker.is_active():
        raise HTTPException(400, "sync already running")

    codes = _pool_union_codes()
    if not codes:
        raise HTTPException(400, "pool is empty; nothing to sync")

    try:
        sync_historical_for_pool(codes=codes, from_date=from_date, to_date=to_date)
    except Exception as e:
        tracker.clear()
        raise HTTPException(500, f"sync failed: {e}") from e
    finally:
        # leave the final state visible for one poll cycle, then clear
        # (status endpoint will see the last progress snapshot)

    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(codes, names, by_code)
    synced_count = sum(1 for e in etfs if e.status == "ok")
    final_in_progress = tracker.get_all()  # snapshot before clear
    tracker.clear()

    return SyncTriggerResult(
        as_of=as_of, etfs=etfs,
        in_progress=final_in_progress, is_running=False,
        synced_count=synced_count, run_at=datetime.now(timezone.utc),
        from_date=from_date, to_date=to_date,
    )


@router.get("/sync/historical/status", response_model=SyncStatusResponse)
def get_sync_status() -> SyncStatusResponse:
    names = _name_lookup()
    as_of, by_code = _latest_summary()
    etfs = _build_etfs(_pool_union_codes(), names, by_code)
    in_progress = tracker.get_all() if tracker.is_active() else None
    return SyncStatusResponse(
        as_of=as_of, etfs=etfs,
        in_progress=in_progress,
        is_running=tracker.is_active(),
    )
```

### 前端

**1. 新增 `frontend/src/components/DateRangePicker.tsx`**

- Modal 弹窗（dialog 元素，原生 HTML）
- 两个 `<input type="date">` + 取消/开始按钮
- 默认 `to_date=today`、`from_date=today-30 天`
- 校验：`from ≤ to`、都不晚于 today
- Props: `open: boolean`, `onClose: () => void`, `onConfirm: (range: {from_date: string, to_date: string}) => void`, `isSubmitting: boolean`
- 错误条：父组件传 `errorMessage?: string`

**2. 修改 `frontend/src/api/hooks.ts`**

```ts
export interface SyncTriggerVariables {
  from_date: string;  // YYYY-MM-DD
  to_date: string;
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation<SyncTriggerResult, Error, SyncTriggerVariables>({
    mutationFn: ({ from_date, to_date }) =>
      api<SyncTriggerResult>(
        `/api/sync/historical/trigger?from_date=${from_date}&to_date=${to_date}`,
        { method: "POST" }
      ),
    onSuccess: (data) => {
      qc.setQueryData(["sync-historical-status"], data);
      qc.invalidateQueries({ queryKey: ["sync-historical-status"] });
    },
  });
}
```

`useSyncStatus` 不动（仍 10s 轮询）。

**3. 修改 `frontend/src/pages/DynamicPoolPage.tsx`**

新增状态：
```tsx
const [pickerOpen, setPickerOpen] = useState(false);
const [syncError, setSyncError] = useState<string | null>(null);

const isRunning = syncStatus.data?.is_running ?? false;
const inProgress = syncStatus.data?.in_progress ?? [];
const progressByCode = new Map(inProgress.map(p => [p.code, p]));
const anyInProgress = inProgress.length > 0;
const anyPending = syncPool.isPending || syncHistory.isPending;
const disabled = anyPending || isRunning;
```

按钮：
```tsx
<button
  onClick={() => { setSyncError(null); setPickerOpen(true); }}
  disabled={disabled}
>
  {syncHistory.isPending ? "同步中…" : "同步 ETF 历史数据"}
</button>
```

顶部进度横幅（仅 `anyInProgress` 时显示）：
```tsx
{anyInProgress && (
  <SyncProgressBanner progress={inProgress} />
)}
```

新增 `SyncProgressBanner` 组件（也放 `frontend/src/components/`，简单展示总体进度 + 当前 code/date）。

表格行内：
- `progressByCode.get(e.code)` 存在 → 渲染 `<RowProgressBar info={...} />`
- 否则 → 既有 `<SyncStatusBadge status={statusByCode.get(e.code) ?? "never"} />`

DateRangePicker 接入：
```tsx
<DateRangePicker
  open={pickerOpen}
  onClose={() => setPickerOpen(false)}
  isSubmitting={syncHistory.isPending}
  errorMessage={syncError}
  onConfirm={(range) => {
    syncHistory.mutate(range, {
      onError: (e) => setSyncError(e.message),
      onSuccess: () => setPickerOpen(false),
    });
  }}
/>
```

### 不修改的（已正确）

- `useSyncStatus` 的 10s 轮询（保留 — 现在终于有意义）
- `useSyncDynamicPool` / `useToggleDynamicEntry` 的 `onSuccess` invalidate 逻辑
- `useScreeningToday` / `usePortfolio` / `useSignalsToday` / `useBacktestTask` / `useHealthStats` 等其他合法轮询

### 配套修改（startup 启动同步 + sync_today 包装函数）

`sync_historical_for_pool` 签名从 `(codes, target_date=None)` 变为 `(codes, from_date, to_date)` —— 必填。需要同步更新 2 个调用方：

**1. `backend/app/main.py:49` startup hook**

```python
# before
sync_historical_for_pool(codes=codes)

# after（默认值 30 天窗口，足够覆盖日常增量）
sync_historical_for_pool(
    codes=codes,
    from_date=date.today() - timedelta(days=30),
    to_date=date.today(),
)
```

**2. `backend/app/services/daily_sync.py:74` `sync_today` 包装函数**

```python
def sync_today(target_date: date | None = None) -> Path:
    """Backwards-compatible wrapper. If `target_date` is given, sync just that
    day; otherwise sync [today-30, today]."""
    codes = sorted(p.stem for p in FIXTURES_DIR.glob("*.csv"))
    if target_date is None:
        # preserve old behaviour: use latest bar date as the summary filename
        latest = _find_latest_bar_date(codes)
        to_date = latest.date() if latest else date.today()
        from_date = to_date  # single day
    else:
        from_date = to_date = target_date
    return sync_historical_for_pool(codes=codes, from_date=from_date, to_date=to_date)
```

新增辅助 `_find_latest_bar_date(codes)`：跨所有 fixture 找最大 date。

**3. `backend/tests/test_daily_sync.py` 现有 3 个 `test_sync_today_*` 用例**

- `test_sync_today_writes_summary_file` / `test_sync_today_summary_includes_all_fixtures`：`sync_today()` 仍返回 Path，断言不变
- `test_sync_today_honors_explicit_target_date`：调用 `sync_today(target_date=date(2026,3,1))`，新签名下 to_date=2026-03-01，断言「summary filename 含 2026-03-01」仍成立

→ **既有 3 个 test_sync_today_* 用例应不需修改**（signature 是 `sync_today(target_date=...)`，外层不变；只是内部改用 from_date/to_date）。

### 不修改的其他合法轮询

| Hook | 端点 | 间隔 | 合法原因 |
|------|------|------|----------|
| `useScreeningToday()` | `/api/screening/today` | 5s | 当日筛选目标随市场数据 / akshare 缓存更新而变 |
| `usePortfolio()` | `/api/portfolio` | 5s | 持仓随调仓执行而变 |
| `useSignalsToday()` | `/api/signals/today` | 5s | 信号在调仓周期内可能变化 |
| `useBacktestTask()` | `/api/backtest/{id}` | 2s（conditional） | 任务状态变化是后台驱动的，必须轮询 |
| `useHealthStats()` | `/api/health?stats=1` | 5s | akshare 缓存命中统计每次请求都在变 |

注：本变更**保留** `useDynamicPool` 5s 轮询不变（虽然它也只通过 mutation 变化，但用户未在本变更要求修改它）。下个变更可单独处理。

## 下游影响分析

### `useTriggerSync` 调用方变化

| 调用方 | 当前调用 | 修改后 |
|--------|---------|--------|
| `DynamicPoolPage.tsx` | `syncHistory.mutate()` | `syncHistory.mutate({ from_date, to_date })` |

### `SyncStatusResponse` 消费者变化

| 消费者 | 行为 |
|--------|------|
| `DynamicPoolPage.tsx` | 新增 `is_running` 检查用于按钮 disabled；新增 `in_progress` 用于进度条渲染 |
| `Dashboard.tsx`（如有引用）| 既有 etfs 不变；新字段 Optional，向后兼容 |

### `_read_latest_bar` → `_read_bar_for_date`

原 `_read_latest_bar` 仅取 `df.iloc[-1]`。新增 `_read_bar_for_date(code, target_date)` 按日期过滤行，返回该日期的 bar 或 `None`。保留 `_read_latest_bar` 给其他调用方（如 `sync_today`）。

### `sync_historical_for_pool` 调用方变化

| 调用方 | 当前调用 | 修改后 |
|--------|---------|--------|
| `backend/app/main.py:49` (startup) | `sync_historical_for_pool(codes=codes)` | `sync_historical_for_pool(codes=codes, from_date=today-30, to_date=today)` |
| `backend/app/services/daily_sync.py:94` (`sync_today`) | `sync_historical_for_pool(codes=codes, target_date=target_date)` | `sync_historical_for_pool(codes=codes, from_date=from_date, to_date=to_date)` |
| `backend/app/api/sync.py:110` (`trigger_sync`) | `sync_historical_for_pool(codes=codes)` | `sync_historical_for_pool(codes=codes, from_date=from_date, to_date=to_date)` |

### `sync_today` 既有 3 个 test

`test_sync_today_writes_summary_file` / `test_sync_today_summary_includes_all_fixtures` / `test_sync_today_honors_explicit_target_date`：

- 都通过 `sync_today(...)` 入口调用，**外层 API 不变**
- 内部从 `target_date` 拆出 `from_date=to_date=target_date`，summary 文件名仍含 target_date
- 既有断言（filename 包含日期、n_etfs 等）应全部继续通过

## 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 同步期间另一请求 trigger 同步 | 低 | 中 | 后端 `tracker.is_active()` 守门；前端按钮已 disabled；双重保险 |
| 同步跑太久，浏览器 timeout | 中 | 中 | mock fixture 读取快（每 (code, date) < 1ms），47 codes × 200 days ≈ 9400 ops，预计 < 10s；远低于浏览器 timeout |
| 大范围（730 天 × 47 codes = 34310 ops）慢 | 中 | 低 | MAX_RANGE_DAYS=730 限制；用户拆分多次；进度可见，不会「假死」 |
| uvicorn --reload 丢状态 | 低 | 中 | 文档说明；reload 后状态清空但前端会看到 `is_running=false` 后重置；下次 trigger 重新建 tracker |
| 已有测试因为 `SyncStatusResponse` 字段变化而失败 | 低 | 低 | 新字段 Optional（`in_progress: list[ProgressInfo] \| None = None`）；既有测试如果 mock 旧 schema 仍然合法 |
| 已有测试因为 `useTriggerSync` 入参变化而失败 | 中 | 中 | 必须更新 `DynamicPoolPage.test.tsx` 中调用 mutate 的方式（无参 → 带参）；spec.md 阶段会列举所有受影响的测试 |

## 边界条件

- **空池**：`trigger_sync` 返回 400（既有行为）
- **from = to**：单日同步合法，total_days = 1
- **from = today**：合法（同步「今天」这 1 天）
- **date range 跨周末/节假日**：mock 不区分，全 7 天都同步；真实 akshare 会跳过无数据日（status=missing）
- **code 没有任何 bar 数据**：所有 date 状态 `missing`；进度仍正常推进
- **首次访问（无任何 summary JSON）**：`_latest_summary` 返回 `(None, {})`；`in_progress` 仍按 trigger 进度返回

## 测试策略

**TDD 路径**：

1. 写 `tests/services/test_sync_progress.py`（RED）→ 实现 `SyncProgressTracker`（GREEN）
2. 写 `tests/services/test_daily_sync.py` 日期范围用例（RED）→ 实现 `sync_historical_for_pool` 改造 + `_read_bar_for_date`（GREEN）
3. 写 `tests/api/test_sync.py` 新端点行为（RED）→ 改造 `trigger_sync` + `get_sync_status` + schemas（GREEN）
4. 写 `src/components/__tests__/DateRangePicker.test.tsx`（RED）→ 实现 `DateRangePicker` 组件（GREEN）
5. 改 `src/pages/__tests__/DynamicPoolPage.test.tsx`（适配 mutate 新签名 + 进度渲染）（RED）→ 改造 `DynamicPoolPage`（GREEN）
6. 跑全量：`uv run pytest -q` + `npx vitest run` + `tsc --noEmit` + `npm run build` + `ruff check`
7. manual smoke：真实启动 dev server，浏览器触发同步看进度

**测试总数**：172 → ~178 后端 / 38 → ~44 前端

## 不在本变更范围

- 取消同步功能（`POST /api/sync/historical/cancel` + UI 按钮）
- `useDynamicPool` 的 5s 轮询删除
- 真实数据源接入（akshare / tushare）
- WebSocket / SSE 实时推送
- Dashboard 上的"上次同步"卡片扩展为显示同步历史
- 同步历史的持久化（运行日志 / 历次 sync 记录）

## 验收标准

1. 点击「同步 ETF 历史数据」按钮 → 弹出 DateRangePicker Modal，含 from/to 两个 date input
2. Modal 默认 from = today-30，to = today
3. 校验失败（from > to / from > today / 跨度 > 730）时 Modal 内显示错误，「开始」按钮禁用
4. 确认后 POST 请求 URL 含 `?from_date=...&to_date=...`
5. 后端返回 400 时 Modal 内显示错误详情，按钮恢复可点
6. 后端返回 200 时 Modal 关闭
7. 同步运行时，表格顶部显示「同步进行中 X/Y — 当前 code 在 day M/N」
8. 当前正在处理的 code 行内显示行内进度条 + 日期范围
9. 同步完成 → invalidate `["sync-historical-status"]` → 表格更新，进度条消失
10. 同步期间两个按钮均 disabled
11. 同步期间从其他 tab 切回（`refetchOnWindowFocus`）能看到最新进度
12. 既有 172 后端测试 + 38 前端测试**继续通过**（不修改既有断言）
13. 新增 ~6 后端测试 + ~6 前端测试**全部通过**
14. tsc --noEmit 干净 / npm run build 成功 / ruff check 干净

---

**下一步**：用户确认 design.md 后，写 `spec.md` + `plan.md` 进入 executing 阶段。
