# Dashboard 化整为零（删除 /signals 与 /portfolio 二级页面）

## 背景

刚合并的 `feature/user-journey-reorg`（M11）把 IA 重整为「顶部 4 项 + 侧边栏 7+1」结构，将今日调仓（`/signals`）和持仓（`/portfolio`）作为二级页面展示。

用户反馈这两个页面的内容**没必要单独成页**——理由是「非投资者日常用户」每周只来一两次，单页层级反而增加跳转成本。应当把这两个页面的内容**原封不动搬到仪表盘**中作为两个大卡片，让用户在首屏就能看到完整的卖出清单和持仓表格，**不需要点击进入二级页面**。

## 范围

仅调整前端 IA 与 Dashboard 组成。**后端不动**（`/api/signals/today`、`/api/portfolio` 已经存在并被新 Dashboard 直接调用）。

## 变更内容

### 删除

1. **路由 `/signals`** —— 完全删除（不再二级页面）
2. **路由 `/portfolio`** —— 完全删除
3. **路由 `/screening`** —— 删除（它原本 `<Navigate to="/signals" replace />`，`/signals` 没了就没意义）
4. **文件 `frontend/src/pages/Signals.tsx`** —— 删除
5. **文件 `frontend/src/pages/Portfolio.tsx`** —— 删除
6. **顶部导航条目 `持仓` 与 `今日调仓`** —— 删除（保留 `仪表盘` + `设置` 两个按钮）

### 合并到 Dashboard（`/`）

`Dashboard.tsx` 当前结构：
```
1. 资产概览
2. 今日需要做的（CTA → /signals）       ← 改为承载原 Signals 全部内容
3. 系统状态
4. 当前持仓（Top 5）（CTA → /portfolio）← 改为承载原 Portfolio 全部内容
```

**变更后**：
```
1. 资产概览
2. 今日调仓（原 /signals 全部内容：卖出表/买入表/复制按钮/防御 banner/进阶/原始输出）
3. 系统状态
4. 当前持仓（原 /portfolio 全部内容：完整持仓表格，不只是 Top 5）
```

合并方式：
- 把 `Signals.tsx` 中渲染卖出表 + 买入表 + 复制按钮 + 防御 banner + ▶ 进阶 + ▶ 原始输出的 JSX 直接 inline 进 Dashboard 的「今日调仓」卡片（保持原有的所有数据获取逻辑 `useSignalsToday`、`useScreeningToday`、`usePool`）
- 把 `Portfolio.tsx` 中渲染完整持仓表格的 JSX inline 进 Dashboard 的「当前持仓」卡片（用 `usePortfolio()` + `usePool()` 做名称查询）
- Dashboard 的 `useSignalsToday`、`useScreeningToday`、`usePool` hooks 已经在现有 Dashboard 中调用，无需重新接入

### 测试

| 测试文件 | 处理 |
|---------|------|
| `frontend/src/pages/__tests__/Signals.test.tsx`（4 用例） | 迁入 `frontend/src/pages/__tests__/Dashboard.flatten.test.tsx`，断言原 Signals 内容在 Dashboard 中可见 |
| `frontend/src/pages/__tests__/Portfolio.test.tsx`（如有） | 同上模式 |
| `frontend/src/pages/__tests__/Dashboard.test.tsx`（5 用例） | 保留 + 扩展：移除「CTA → /signals」「CTA → /portfolio」相关断言，改为断言完整内容已渲染 |
| `frontend/src/pages/__tests__/Dashboard.stale-sync.test.tsx`（2 用例） | 保留不变 |
| `frontend/src/__tests__/screening-redirect.test.tsx`（1 用例） | 删除（`/screening` 路由没了） |
| `frontend/src/__tests__/app-shell-wiring.test.tsx`（2 用例） | 调整：「renders 4-entry top nav」改为「renders 2-entry top nav」；移除对 `今日调仓` / `持仓` 的断言 |

### 不动

- AppShell.tsx 组件（只调整 nav 常量）
- Sidebar.tsx（侧边栏不受影响）
- DynamicPoolPage、DataSource、Backtest、History、PoolConfig、ThemeConfig、StrategyConfig 8 个配置/工具页
- 所有后端代码、API、模型、测试
- 通配路由 `<Route path="*">` 继续保留 → `/`

## 验收

- [ ] `npm test` 全绿
- [ ] `npm run lint` 与 `npm run build` 通过
- [ ] 后端 `uv run pytest -q` 仍 165 passed
- [ ] 用户访问 `/` 在首屏可见完整的卖出清单与持仓表格，无需点击任何链接
- [ ] 顶部导航只有 `仪表盘` 与 `设置` 两项
- [ ] `git grep "/signals\|/portfolio\|/screening"`（排除 source-map / spec 文档）在 `frontend/src/` 下零命中
- [ ] Dashboard 仍通过原有全部 7 个用例（5 + 2 stale-sync）+ 新增 flatten 用例

## 不在范围

- 不调整 Dashboard 上「资产概览」与「系统状态」的内容
- 不调整后端
- 不调整侧边栏内容
- 不调整打印样式（`@media print` 块仍适用——Dashboard 现在有「今日调仓」表格可打印）
- 不调整 `/dynamic-pool` 独立页面（用户没要求合并它）

## 风险

1. **Dashboard 首屏很长** —— 「今日调仓」+「当前持仓」完整表格堆到首屏会显著增加滚动。这是用户接受的取舍（已经明确"原封不动搬到仪表盘"）。
2. **重复 fetch** —— `useSignalsToday`、`useScreeningToday`、`usePool`、`usePortfolio` 在 Dashboard 与原页面中的 query key 一致，TanStack Query 会自动去重，没有额外的网络请求。
3. **测试迁移** —— Signals 4 个测试 + Portfolio 0 个测试的迁移是新工作，不是单纯删除；但都是机械的断言重定位。

---

**Status**: - [x] 提案已确认（2026-06-29）— 进入 spec 阶段