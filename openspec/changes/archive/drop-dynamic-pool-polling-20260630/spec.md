# Spec: drop-dynamic-pool-polling

## Context

`/dynamic-pool` 页面进入后，前端每 5 秒请求一次 `GET /api/configs/pool/dynamic`。该端点对应的数据只通过用户点击「同步 ETF」或行内启用切换才会变化——无后台写源，轮询是纯浪费。

M14（add-sync-progress-ui）已把"为什么需要轮询"补到 `useSyncStatus`（同步进行时才有意义）。`useSyncDynamicPool` / `useToggleDynamicEntry` mutation 已正确 `qc.invalidateQueries({ queryKey: ["dynamic-pool"] })`，mutation 完成后自动刷新。

本变更：删除 `useDynamicPool` 的 `refetchInterval: 5_000`，依赖 mutation-driven refresh + TanStack Query 默认 `refetchOnWindowFocus: true` 兜底跨 tab 同步。

## ADDED Requirements

### Requirement: `useDynamicPool` 不再轮询

`useDynamicPool` 必须不在 query 配置中设置 `refetchInterval`。

#### Scenario: 进入页面后无重复请求
- Given 用户在 `/dynamic-pool` 页面
- When 用户停留 30 秒不做任何操作
- Then DevTools Network 中 `GET /api/configs/pool/dynamic` 只出现 1 次（首请求）

#### Scenario: 行内启用切换后即时刷新
- Given 用户在 `/dynamic-pool` 页面
- When 用户点击某行的启用 checkbox
- Then `useToggleDynamicEntry` mutation 成功
- And `["dynamic-pool"]` 被 invalidate
- And 表格立即反映新状态（无需轮询）

#### Scenario: 同步动态池后即时刷新
- Given 用户在 `/dynamic-pool` 页面
- When 用户点击「同步 ETF」按钮
- Then `useSyncDynamicPool` mutation 成功
- And `["dynamic-pool"]` 被 invalidate
- And 表格立即反映新同步的 ETF 列表

#### Scenario: 跨 tab 切换刷新
- Given 用户打开了 `/dynamic-pool` tab A
- And 同一应用在另一 tab B 触发了 dynamic pool 修改（mutation）
- When 用户切回 tab A
- Then TanStack Query `refetchOnWindowFocus: true` 触发 refetch
- And tab A 显示最新数据

### Requirement: 修改不应破坏现有测试覆盖

#### Scenario: 前端 vitest 继续全绿
- Given 修改前 `npx vitest run` 56 个测试全部通过
- When 实施本变更后跑 `npx vitest run`
- Then 既有 56 个测试继续全部通过
- And 新增 / 调整的测试也通过

#### Scenario: tsc / build 干净
- Given 修改前 `npx tsc --noEmit && npm run build` 干净
- When 实施本变更后跑同样命令
- Then 全部仍然干净

## MODIFIED Requirements

无。

## REMOVED Requirements

无。

## Cross-cutting

### 修改的文件清单

- `frontend/src/api/hooks.ts`（**改 1 行**）：删除 `useDynamicPool` 的 `refetchInterval: 5_000`
- `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（**可能改**：检查并更新任何依赖「5s 后再次请求」或 fake timer 推进的断言）

### 不修改的文件

- `useSyncStatus` 10s 轮询（同步运行时才有意义，M14 已确认保留）
- 其他 5 个 mutation hook 的 `onSuccess`（已正确 invalidate `["dynamic-pool"]`）
- 其他合法轮询 hook（useScreeningToday / usePortfolio / useSignalsToday / useHealthStats）
- 后端任何文件

### 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 测试用 fake timer 推进 5s 断言「再次请求」 | 低 | 实现时跑测试定位，按需调整断言 |
| 真实场景下另一客户端修改数据后本 tab 看不到 | 低 | `refetchOnWindowFocus: true` 默认开启，tab 切回触发 refetch |
| Dashboard / EtfDetailPage 渲染时机因 query 行为变化异常 | 极低 | 3 个 caller 行为都是「读 query.data」，去掉轮询不改变读路径，只改变 refetch 频率 |

---

**确认后进入 executing 阶段。**