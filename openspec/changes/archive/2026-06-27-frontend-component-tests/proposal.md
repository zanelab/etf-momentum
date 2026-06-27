# 前端组件测试

## Why

`spec/tasks.md` 阶段 4「质量与交付」要求补全前端组件测试。当前 165 个前端测试覆盖了大部分组件（`components/{backtest,dashboard,pools}/*` 和 `pages/{BacktestPage,DashboardPage,PoolsPage}.tsx`），但仍有 3 个文件完全没测试：

| 文件 | 路径 | 当前状态 |
|------|------|---------|
| `Button` UI primitive | `frontend/src/components/ui/button.tsx` | 0 测试 |
| `HealthPage` 健康检查页 | `frontend/src/pages/HealthPage.tsx` | 0 测试 |
| `Layout` 导航布局 | `frontend/src/layouts/Layout.tsx` | 0 测试 |

风险：
- `Button` 是 UI primitive，被 `HealthPage` 等页面直接使用；它的 variant/size/disabled 行为没有任何测试守住，未来调整 `buttonVariants` (cva) 配置时容易回归。
- `HealthPage` 有 4 个状态（idle / loading / ok / error）+ 手动重试按钮 + JSON 数据展示，逻辑分支多但完全没有测试。
- `Layout` 是路由框架（NavLink active 高亮）入口，所有页面都嵌在它里面；active 高亮的逻辑直接决定导航条上"当前在哪一项"的可读性。

这三个文件加起来约 150 行代码、6 个有意义的逻辑分支；按 v1.0 质量门控，应该有显式测试守护。

## What Changes

仅新增 3 个测试文件，不修改任何 React 组件：

| 新增文件 | 测试数 | 重点 |
|---------|-------|------|
| `frontend/src/components/ui/button.test.tsx` | ~8 | 6 个 variant × 默认行为、4 个 size、ref 转发、disabled、className 合并、onClick |
| `frontend/src/pages/HealthPage.test.tsx` | ~10 | 4 状态分支（idle/loading/ok/error）、重试按钮、JSON 数据展示、错误信息展示、HealthStore 联动 |
| `frontend/src/layouts/Layout.test.tsx` | ~5 | 4 个 NavLink 渲染、active 高亮（用 MemoryRouter 包裹）、Outlet 渲染、标题显示 |

预期：前端测试从 165 → ~188（+23）。`vitest` 跑完全部 ~50s（当前 ~10s）。

不引入：
- 不改任何 `.tsx` 组件文件
- 不改 store
- 不引入新的测试工具（继续用 `@testing-library/react` + `vitest` + `MemoryRouter` from `react-router-dom`）
- 不改 vitest 配置

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- (none)

> 本次变更只补测试、不改产品行为，因此不引入新 capability，也不对现有 capability 写 delta spec。

## Impact

- **代码**：仅 3 个新测试文件 + 必要的 `MemoryRouter` wrapper 引入。
- **API / DB / CLI**：无。
- **依赖**：沿用 `vitest` + `@testing-library/react` + `react-router-dom`（已在 devDependencies 中）。
- **CI**：当前仓库无 `.github/workflows/`，新增测试通过 `npx vitest run` 跑即可。
- **风险**：所有新断言都是「已有行为 → 显式锁定」，不涉及规范变更。