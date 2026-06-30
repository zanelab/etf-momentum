# Proposal: 去掉 useDynamicPool 的 5s 轮询

**变更名**: `drop-dynamic-pool-polling`
**日期**: 2026-06-30
**状态**: - [x] 提案已确认（用户 2026-06-30 在 brainstorming 阶段确认）

## 背景（What）

`/dynamic-pool` 页面进入后，每 5 秒请求一次 `GET /api/configs/pool/dynamic`。该端点对应的数据只通过用户点击「同步 ETF」或行内启用切换才会变化，没有任何后台进程写它——轮询是浪费的。

M14（add-sync-progress-ui）刚把"为什么需要轮询"补到了 `useSyncStatus` 上（同步进行时才有意义），但 `useDynamicPool` 的轮询仍是无理由开销。

## 当前代码

`frontend/src/api/hooks.ts:372-378`：

```ts
export function useDynamicPool() {
  return useQuery({
    queryKey: ["dynamic-pool"],
    queryFn: () => api<DynamicPoolEntry[]>("/api/configs/pool/dynamic"),
    refetchInterval: 5_000,   // ← 删除
  });
}
```

**3 个 caller**：
- `frontend/src/pages/EtfDetailPage.tsx:20` — 读 `pool` 判断当前 ETF 是否在池中
- `frontend/src/pages/DynamicPoolPage.tsx:12` — 主页表格渲染
- `frontend/src/pages/Dashboard.tsx:24` — 系统状态卡 + 过期动态池 amber 横幅

## 为什么是问题（Why）

- **网络浪费**：用户每次进 `/dynamic-pool` 立即触发首请求，之后每 5s 一次，停留 1 分钟 = 13 次 GET，绝大多数是「无变化的轮询」
- **后端无意义**：除了 `useSyncDynamicPool` / `useToggleDynamicEntry` mutation 写该数据，无其他写源
- **mutation 已正确 invalidate**：`useSyncDynamicPool` / `useToggleDynamicEntry` 都已 `qc.invalidateQueries({ queryKey: ["dynamic-pool"] })`（hooks.ts:387、403），mutation 完成后自动刷新，**不需要轮询兜底**

## 范围（Scope）

**改动面**：纯前端 1 行

涉及：
- `frontend/src/api/hooks.ts`（**改 1 行**）：删除 `refetchInterval: 5_000`
- `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（**可能改**：测试用例若断言「5s 后再次请求」需更新为依赖 mutation 触发）

## 验收标准（Acceptance Criteria）

1. 进入 `/dynamic-pool` 页面后，DevTools Network 只看到一次 `GET /api/configs/pool/dynamic`，停留 30s 内不再触发
2. 行内启用切换 → 表格立即刷新（mutation 已 invalidate）
3. 点击「同步 ETF」→ 表格刷新（mutation 已 invalidate）
4. Dashboard 系统状态卡 + 过期动态池 banner 仍正常工作（依赖同一 queryKey）
5. EtfDetailPage「池外 ETF」amber 警示逻辑仍正确
6. 现有 56 个 vitest 用例全部继续通过；新增 / 修改的测试断言也通过
7. tsc / build / ruff 全绿

## 非范围（Out of Scope）

- 其他 query 的轮询调整（`useScreeningToday` / `usePortfolio` / `useSignalsToday` / `useHealthStats` / `useSyncStatus`）—— 这些有各自的轮询依据
- 跨 tab 实时同步（如果用户切到别的 tab 修改数据，切回时是否需要 refetch 由 TanStack Query 默认 `refetchOnWindowFocus: true` 兜底，不在本变更范围）
- 后端任何改动

## 替代方案（仅记录，最终走 A）

- **A（推荐）**：直接删除 `refetchInterval`，依赖 mutation-driven invalidate。最小改动，行为正确。
- **B**：保留 `refetchInterval` 但延长到 60s。妥协方案，仍有浪费。
- **C**：改用 `EventSource` 推送。后端需新增 SSE 端点，overkill。

→ **A**

---

**下一步**：用户确认后进入 brainstorming（仅问 1 题：跨 tab 刷新行为），再写 spec + plan。