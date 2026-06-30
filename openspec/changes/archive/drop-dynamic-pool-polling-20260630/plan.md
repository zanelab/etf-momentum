# Implementation Plan: drop-dynamic-pool-polling

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 `useDynamicPool` 的 `refetchInterval: 5_000`，让动态池数据走 mutation-driven refresh（已有）+ `refetchOnWindowFocus`（TanStack Query 默认）兜底。

**Architecture:** 纯前端 1 行配置修改 + 测试断言校验。3 个 caller（DynamicPoolPage / Dashboard / EtfDetailPage）都是只读 query.data，去掉轮询不改变读路径。

**Tech Stack:** React + TanStack Query + TypeScript + vitest.

## Global Constraints

- 单 commit per task
- 所有既有 56 个 vitest 用例继续通过（**不修改既有断言**；只调整 fake timer 推进的测试）
- 新增 ≤ 2 个测试（验证「停留 30s 只 1 次请求」+ 「mutation 后立即刷新」）
- tsc --noEmit / npm run build 干净
- 不引入新依赖
- 后端 0 改动

---

## Task 1: 前端 — 删除 `useDynamicPool` 的 `refetchInterval` + 调整/新增测试

**Files:**
- Modify: `frontend/src/api/hooks.ts:372-378`（删除 `refetchInterval: 5_000`）
- Modify: `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（如有用 fake timer 断言「5s 后再次请求」则更新；否则不动）

**Interfaces:**

```ts
// 旧
export function useDynamicPool() {
  return useQuery({
    queryKey: ["dynamic-pool"],
    queryFn: () => api<DynamicPoolEntry[]>("/api/configs/pool/dynamic"),
    refetchInterval: 5_000,   // ← 删除
  });
}

// 新
export function useDynamicPool() {
  return useQuery({
    queryKey: ["dynamic-pool"],
    queryFn: () => api<DynamicPoolEntry[]>("/api/configs/pool/dynamic"),
  });
}
```

- [x] **Step 1: 写新测试（RED）**

在 `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx` 新增（如果还没有的话）：

```tsx
import { render, screen, waitFor } from "@testing-library/react";
// ... 既有 imports

it("does not refetch /api/configs/pool/dynamic after 5s", async () => {
  let callCount = 0;
  server.use(
    http.get("*/api/configs/pool/dynamic", () => {
      callCount += 1;
      return HttpResponse.json([]);
    })
  );

  render(<DynamicPoolPage />);
  await waitFor(() => expect(callCount).toBe(1));

  // advance 30 seconds in fake time
  act(() => {
    vi.advanceTimersByTime(30_000);
  });

  // still only the initial request
  expect(callCount).toBe(1);
});

it("refetches after useToggleDynamicEntry mutation succeeds", async () => {
  let callCount = 0;
  server.use(
    http.get("*/api/configs/pool/dynamic", () => {
      callCount += 1;
      return HttpResponse.json([/* ... */]);
    }),
    http.patch("*/api/configs/pool/dynamic/*", () => {
      return HttpResponse.json({ /* updated entry */ });
    })
  );

  render(<DynamicPoolPage />);
  await waitFor(() => expect(callCount).toBe(1));

  // user toggles a row
  const toggle = screen.getByRole("switch", { name: /enable/i });
  await user.click(toggle);

  // invalidate triggers another fetch
  await waitFor(() => expect(callCount).toBeGreaterThan(1));
});
```

（具体 mock 形态需 implementer 按文件实际结构适配；关键是断言：① 5s/30s 后 callCount 仍为 1；② mutation 后 callCount > 1）

- [x] **Step 2: 跑新测试验证 RED**

```bash
cd frontend && npx vitest run src/pages/__tests__/DynamicPoolPage.test.tsx
```

Expected: 至少 1 个新测试 FAIL（refetchInterval 还在，所以 fake timer 推进后 callCount == 2）

- [x] **Step 3: 删除 `useDynamicPool` 的 `refetchInterval`**

`frontend/src/api/hooks.ts:372-378`：
```ts
export function useDynamicPool() {
  return useQuery({
    queryKey: ["dynamic-pool"],
    queryFn: () => api<DynamicPoolEntry[]>("/api/configs/pool/dynamic"),
  });
}
```

- [x] **Step 4: 跑新测试验证 GREEN**

```bash
npx vitest run src/pages/__tests__/DynamicPoolPage.test.tsx
```

Expected: 新增 2 个测试通过；既有测试也通过

- [x] **Step 5: 跑前端全量确认无回归**

```bash
npx vitest run
```

Expected: 56/56 + 2 新增 = 58/58 passed

- [x] **Step 6: tsc + build 验证**

```bash
npx tsc --noEmit && npm run build
```

Expected: tsc clean / build 成功

- [x] **Step 7: 提交**

```bash
git add frontend/src/api/hooks.ts frontend/src/pages/__tests__/DynamicPoolPage.test.tsx
git commit -m "feat(dynamic-pool): drop 5s polling from useDynamicPool"
```

---

## Task 2: 全量验证 + 手动 smoke + 收尾

**Files:** 无新文件

- [x] **Step 1: 跑前端全量 + tsc + build**

```bash
cd frontend && npx vitest run && npx tsc --noEmit && npm run build
```

Expected: 58/58 passed / tsc / build 全绿

- [x] **Step 2: 手动浏览器 smoke（人工，必做）**

启动 dev server：
```bash
# 终端 A
cd backend && uv run uvicorn app.main:app --reload --port 8000
# 终端 B
cd frontend && npm run dev
```

打开 http://localhost:5173/dynamic-pool：

1. **Network 验证**：DevTools Network 看到 `GET /api/configs/pool/dynamic` 1 次
2. **停留 30s**：不再触发任何 `pool/dynamic` 请求
3. **行内 toggle**：点击某行启用 checkbox → 表格立即更新（mutation invalidate）
4. **同步 ETF**：点击「同步 ETF」→ 表格刷新（mutation invalidate）
5. **跨 tab**：复制 tab，修改其中一份；切回原 tab → 看到最新数据（refetchOnWindowFocus）

如果失败，回到 Task 1 排查。

- [x] **Step 3: 跑 final review（subagent-driven-development）**

按 superpowers:subagent-driven-development 流程，dispatch final code reviewer subagent，传 `git merge-base main HEAD` 作为 base + HEAD 作为 head 生成的 review package。

- [x] **Step 4: 修复 review 发现的 Critical / Important 问题（如有）**

- [x] **Step 5: 准备合并**

```bash
cd /Users/zane/Workspace/etf-momentum
git log --oneline main..HEAD   # 应该有 1-2 个 commit
git status                     # 干净
```

---

## 风险与缓解

- **Task 1 测试调整范围不可控**（低）：跑测试时定位，预期 < 3 处 fake timer 断言
- **真实场景跨客户端 race**（极低）：refetchOnWindowFocus 已默认开启

---

**Report 文件**: `/Users/zane/Workspace/etf-momentum/.superpowers/sdd/ddpp-task-N-report.md`（N = 1..2）