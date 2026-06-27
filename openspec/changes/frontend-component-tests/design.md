# Design — Frontend Component Tests

## Context

`frontend/src/` 下 23 个测试文件覆盖 165 测试；但 `components/ui/button.tsx`、`pages/HealthPage.tsx`、`layouts/Layout.tsx` 这三个文件完全没有测试。`Layout` 是路由入口，`HealthPage` 涉及 4 个状态分支 + 重试按钮，`Button` 是其他页面复用的 UI primitive。

| 模块 | 现状 | 现有测试 | 缺口 |
|------|------|---------|------|
| `components/ui/button.tsx` | cva 驱动的 Button primitive（6 variant × 4 size） | 0 | variant/size 矩阵 + ref + className 合并 |
| `pages/HealthPage.tsx` | 4 状态 + JSON 数据展示 + 手动重试 | 0 | 状态分支 + 重试 + 错误展示 |
| `layouts/Layout.tsx` | 4 NavLink + Outlet + 标题 | 0 | active 高亮 + Outlet |

本次变更只补测试。`vitest.config.ts` 和现有 `@testing-library/react` 配置已经够用，`MemoryRouter` 也已通过 `react-router-dom` 在 devDependencies 提供。

## Goals / Non-Goals

**Goals:**
- 为 `Button` 提供 variant × size 矩阵 + ref/disabled/onClick/className passthrough 的契约测试。
- 为 `HealthPage` 锁定 4 状态机（idle / loading / ok / error）+ 重试按钮 + JSON 展示的契约。
- 为 `Layout` 验证 4 个 NavLink 渲染 + active 高亮 + Outlet 渲染。
- 不引入新的依赖。

**Non-Goals:**
- 不改任何 `.tsx` 组件 / `Layout.tsx` / store。
- 不引入 `msw`、`user-event` 等新工具——继续用 `@testing-library/react` + `fireEvent`。
- 不写 e2e / Playwright。
- 不补 layout 中 icon import 的单元测试（图标是 lucide-react 第三方组件，测试意义不大）。

## Decisions

### 1. 每个组件单独一个 `.test.tsx` 文件，跟现有约定一致

**理由**：现有所有组件测试都是 `Foo.tsx` + `Foo.test.tsx` 同目录。HealthPage / Layout 也按这个布局写。

**替代方案**：用 `describe()` 把 3 个组件塞进 `components.test.tsx`。否决：约定混乱，定位测试不方便。

### 2. HealthPage 用 vi.spyOn mock apiGet，而不是 mock fetch

**理由**：`@/api/client` 是项目内部抽象，spyOn 它比 mock fetch 更精确（只影响 HealthPage 的 GET /health，不影响其他 fetch）。

**替代方案**：mock global fetch。否决：粒度太粗，会污染后续如果引入 fetch 的其他测试。

### 3. Layout 测试用 MemoryRouter + initialEntries 控制 active link

**理由**：NavLink 的 active 状态依赖 location.pathname。MemoryRouter + initialEntries 是 react-router-dom 官方推荐的测试方式。

**替代方案**：直接渲染 Layout 不包 Router。否决：会触发 react-router warning，无法测 active。

### 4. Button 测试不通过 snapshot

**理由**：cva 生成的 className 很长且依赖 Tailwind 配置，snapshot 测试脆弱。改为断言关键 className token（如 `bg-primary`、`h-10`）即可。

**替代方案**：snapshot。否决：cva className 一旦 Tailwind 升级会变，snapshot 经常误报。

## Risks / Trade-offs

- **[Risk] HealthPage 内部直接调 `apiGet`，spyOn 时需要 reset** → **Mitigation**：在 `beforeEach` 里 `vi.restoreAllMocks()`，跟 BacktestPage 测试一致。
- **[Risk] Button 的 6 variant × 4 size = 24 组合** → **Mitigation**：不全覆盖；只测 1-2 个最具代表性的 variant（default / destructive / outline）+ 关键 size（default / icon），以及 ref 转发。其余变体通过 `buttonVariants({...})` 工厂函数自身的 cva 类型保证。
- **[Risk] Layout 的 active 高亮是 CSS class，断言会绑死 Tailwind 名字** → **Mitigation**：断言 NavLink 的 `aria-current="page"` 属性（react-router-dom 默认 active NavLink 会加这个属性），不绑死 className。

## Migration Plan

无。本变更只动测试文件。

## Open Questions

- 是否要把"v1.0 阶段 4 的前端 README 文档" 拆成另一个 change？当前 spec/tasks.md 还有一个 "[ ] README + 启动文档" 待办，留到下一轮。