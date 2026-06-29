# Design: dynamic-pool-consolidate

## 概述

将 3 个侧边栏工具页（`/dynamic-pool`、`/history`、`/sync`）合并为以 `动态池` 为中枢的统一页面，提供「池内 ETF 写侧（两个同步）+ 读侧（行级下钻到该 ETF 的历史）」的完整生命周期。后端 API 全部沿用，**纯前端 IA 重构**。

来源：见 `proposal.md`（What / Why / Scope / Acceptance Criteria）。

## 技术方案

### 方案 A（推荐）— 合并到动态池 + 子路由下钻

- 主页 `/dynamic-pool`：表格 + 顶部 2 个同步按钮 + 行级下钻
- 子页 `/dynamic-pool/:code`：单只 ETF 的 K 线 + 区间 + 字段 + 返回
- 删除 `/history` 与 `/sync`；侧边栏 4 → 2
- **优点**：IA 最简（一站式）；写侧与读侧在同一上下文；下钻模型符合「池 → 个体」的自然认知；侧边栏负担降到 M11 之前
- **缺点**：下钻子页需要单独测试；旧 `/history`、`/sync` 的链接失效（需 301 等价处理或通配兜底）

### 方案 B — 3 页保留 + 跨页导航链接（否决）

- 三个页面原样保留；仅在 `/dynamic-pool` 表格中加 `查看历史` / `查看同步状态` 列链接到另两页
- **优点**：零页面改动，仅增列；旧链接不破坏
- **缺点**：仍是 3 个并列页面，没解决 IA 重复的根本问题；用户依旧要在 3 个页面间跳转；侧边栏 4 项不变

### 方案 C — 合并为「数据管理」+ Tab 切换（否决）

- 单一页面 `/data`，内含 3 个 Tab（动态池 / 同步状态 / 历史查询）
- **优点**：单页聚合，Tab 切换无跨页加载
- **缺点**：Tab 之间状态不持久（切换丢表单）；仍是 3 个并列概念，只是被 Tab 包裹；「历史查询」Tab 单独存在意味着「池外查询」语义被保留，与本提案「仅池内 ETF」冲突

## 最终决策

选择**方案 A**。原因：

1. 用户已明确「池内 ETF + 下钻」的认知模型
2. 行为细节（空池、按钮互斥、404 软兜底）都已在 brainstorming 阶段对齐
3. 方案 A 实施范围明确（3 个页面删除/合并、1 个新页面、1 个新子路由、1 列表扩展、1 个侧边栏收编），无模糊点
4. 后端零改动降低风险

## 详细设计

### 路由结构

```
/                          Dashboard
/pool                      PoolConfig
/themes                    ThemeConfig
/strategy                  StrategyConfig
/dynamic-pool              DynamicPoolPage (main, 含表格 + 2 同步按钮)
/dynamic-pool/:code        EtfDetailPage (新，K 线 + 区间 + 字段 + 返回)
/backtest                  Backtest
/datasource                DataSource
*                          Navigate to /
```

被删：`/history`、`/sync`（路由表移除 + 侧边栏移除）。未对 `/history` 与 `/sync` 设 301 重定向——侧边栏不再出现，外部链接极少，按通配 `*` → `/` 兜底即可。

### 页面布局

#### `/dynamic-pool`（主页面）

```
┌─ 动态池 ──────────────────────────── [同步 ETF]  [同步历史数据] ┐
│                                                            │
│  表格：                                                    │
│  ┌─────────┬──────┬──────┬──────────┬──────────────────┐   │
│  │ 代码     │ 名称  │ 启用 │ 上次同步 │ 历史同步状态      │   │
│  ├─────────┼──────┼──────┼──────────┼──────────────────┤   │
│  │ 510300… │ 华泰… │ ☑   │ 06-29 … │ ✓ 已同步 06-29  │ ↗ │  ← 行可点击
│  │ 510500… │ 南方… │ ☑   │ 06-29 … │ ⚠ 失败 akshare… │ ↗ │
│  │ 159915… │ 易方达 │ ☐   │ 06-28 … │ — 缺失          │ ↗ │
│  └─────────┴──────┴──────┴──────────┴──────────────────┘   │
│  （行 hover 高亮 + cursor-pointer + 右侧 ↗ 标识）            │
└────────────────────────────────────────────────────────────────┘
```

- 行点击（`onClick` on `<tr>`）→ `navigate('/dynamic-pool/' + encodeURIComponent(code))`
- 行级键盘可达：`<tr tabIndex={0} onKeyDown>` 处理 `Enter`
- 右侧 ↗ 是纯视觉 affordance，`<a>` 仍包裹整行以保证点击区
- 整行包 `<Link>` 比 `useNavigate + onClick` 更 SEO/语义友好，但需要防止内嵌 checkbox 触发外层导航。决策：行级用 `useNavigate + onClick`，checkbox 区域 `e.stopPropagation()` 阻止冒泡

#### `/dynamic-pool/:code`（子页面）

```
┌─ ← 返回动态池  ·  510300.XSHG · 华泰柏瑞沪深300ETF ┐
│                                                  │
│  K 线 + 成交量（recharts ComposedChart）           │
│                                                  │
│  [开始: 2026-01-01] [结束: 2026-03-19]            │
│  字段：[☑ open] [☑ high] [☑ low] [☑ close] [☑ vol]│
│                                                  │
│  （继承原 History 页的所有交互）                    │
└──────────────────────────────────────────────────┘
```

- 标题：`<code> · <name>`（从 `useDynamicPool` 数据中查 name；不在池时显示 `<code>` + 琥珀色提示「该 ETF 已被移出动态池」）
- 404 软兜底：子页用 `useDynamicPool()` 查 code；不在 → 顶部 amber 警示条 + 「← 返回动态池」链接；K 线区**仍渲染**（`useMarketHistory` 仍可查 `static_pool`/`akshare`）
- 「← 返回动态池」用 `useNavigate(-1)` 不靠谱（首次进入无历史），改为 `navigate('/dynamic-pool')`

### 状态管理

#### Hook 复用

| Hook | 来源 | 新页面用途 |
|------|------|------|
| `useDynamicPool()` | 既有 | 主页表格 + 子页 name 解析 |
| `useSyncDynamicPool()` | 既有 | 「同步 ETF」按钮 |
| `useToggleDynamicEntry()` | 既有 | 表格启用切换 |
| `useSyncStatus()` | 既有（M12） | 「历史同步状态」列 |
| `useTriggerSync()` | 既有（M12） | 「同步 ETF 历史数据」按钮 |
| `useMarketList()` | 既有 | 子页字段选择的下拉（如有） |
| `useMarketHistory(code, start, end, fields)` | 既有 | 子页 K 线 |

无需新增 hook；纯组合。

#### 互斥（Mutex）模式

主页两按钮的 disabled 由任一 mutation 的 `isPending` 决定：

```tsx
const syncPool = useSyncDynamicPool();
const syncHistory = useTriggerSync();
const anyPending = syncPool.isPending || syncHistory.isPending;

<button disabled={anyPending || isPoolEmpty}>同步 ETF</button>
<button disabled={anyPending || isPoolEmpty}>同步历史数据</button>
```

`isPoolEmpty = (useDynamicPool.data?.length ?? 0) === 0` 时两个按钮都 disabled（与「空池时主推同步 ETF」对齐——但这里两个都灰，因为没池子啥都干不了；改成 primary 灰是 UX 细节，由按钮 style 区分 primary/secondary，不影响 enabled 状态）。

实际上：空池时「同步 ETF」**不禁用**——它是主 CTA；「同步历史数据」才禁用（无意义）。修正：

```tsx
const isPoolEmpty = (useDynamicPool.data?.length ?? 0) === 0;

<button disabled={anyPending}>同步 ETF</button>  // 主推
<button disabled={anyPending || isPoolEmpty}>同步 ETF 历史数据</button>  // 空池灰
```

### 空态文案

- 表格空 + 未在同步中：`暂无动态池条目，请点击「同步 ETF」拉取全市场 ETF 列表`
- 表格空 + 任一同步 in-flight：表格上方显示 `正在同步…` 占位

### 表格列定义

| 列 | 数据源 | 渲染 |
|----|--------|------|
| 代码 | `e.code` | `<code>` 标签 + 字体 mono |
| 名称 | `e.name` | 普通文本；null 时显示 `—` |
| 启用 | `e.is_enabled` | checkbox（stopPropagation） |
| 上次同步 | `e.last_synced_at` | `new Date(...).toLocaleString('zh-CN')` |
| 历史同步状态 | `useSyncStatus().etfs[code].status` | 复用 `<SyncStatusBadge>`（从 M12 抽出）；4 个徽章 |
| 操作 | — | 不显示新列；行整体可点击 → ↗ chevron 视觉提示 |

`<SyncStatusBadge>` 抽取：M12 的 `SyncStatus.tsx` 中的徽章逻辑提到 `frontend/src/components/SyncStatusBadge.tsx`，主页与下钻子页都用。

### 测试策略

| 范围 | 测试文件 | 新增用例数 |
|------|---------|------|
| `DynamicPoolPage` 重组（按钮 + 互斥 + 空态 + 行点击） | `frontend/src/pages/__tests__/DynamicPoolPage.test.tsx`（既有 2 个 → 扩到 ~6 个） | +4 |
| `EtfDetailPage`（新页面，K 线 + 404 软兜底 + 返回） | 新增 `frontend/src/pages/__tests__/EtfDetailPage.test.tsx` | +4 |
| `SyncStatusBadge` 抽取（从 SyncStatus 抽出） | 抽出后由 SyncStatus 与 DynamicPoolPage 间接覆盖 | 0 |
| 路由清理（无 `/history` `/sync`） | `frontend/src/pages/__tests__/AppShell.test.tsx` | +1 |
| 后端 | 不变 | 0 |

合计前端测试 33 → ~42。后端 172 保持。

### 实施任务分解（preview，落到 `plan.md` 时确定细节）

1. **抽出 `<SyncStatusBadge>`**：从 `SyncStatus.tsx` 提到 `components/`，保留 `SyncStatus` 页面的现有测试
2. **扩展 `DynamicPoolPage`**：新增 2 同步按钮 + 「历史同步状态」列 + 行点击 + 空态文案 + 互斥逻辑
3. **新增 `EtfDetailPage`**：`/dynamic-pool/:code` 路由 + K 线 + name 解析 + 404 软兜底 + 返回链接
4. **路由与侧边栏清理**：删除 `History` / `SyncStatus` 路由注册与导入；侧边栏 `TOOL_ENTRIES` 收编为 2 项；删除 `pages/History.tsx` 与 `pages/__tests__/History.test.tsx`（如果存在）；`SyncStatus.tsx` 保留文件以复用 `SyncStatusBadge` 但不再有路由
5. **测试更新 + 验证**：上述测试矩阵 + `npm test` / `tsc` / `npm run build` / 后端 `pytest` 全绿
6. **项目级 spec 同步**：`spec/requirements.md` M13 / `spec/tasks.md` M13 / `spec/structure.md`

## 风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| 行点击与 checkbox 切换冲突 | 中 | `e.stopPropagation()` + 视觉上 checkbox 在独立列 |
| 旧 `/history` `/sync` 链接失效 | 低 | 通配 `*` → `/` 兜底；侧边栏已移除，外部来源极少 |
| 抽出 `<SyncStatusBadge>` 漏改 `SyncStatus.tsx` 内部引用 | 低 | 抽出后立刻跑 `SyncStatus.test.tsx` 验证 3 个旧用例 |
| 「历史同步状态」列与 `useSyncStatus` 10s polling 叠加导致表格抖动 | 低 | 10s 间隔已较慢，UI 闪烁可接受；如有抖动可加 CSS `transition-colors` |
| 下钻子页 ETF 不在池时 `useMarketHistory` 仍命中 fixture（akshare 缺失时）→ 显示「假数据」误导 | 中 | 子页顶部 amber 提示必须显眼（不只是小字）；明确写「该 ETF 已被移出动态池，以下数据仅供参考」 |
| 抽 `<SyncStatusBadge>` 后 `SyncStatus` 页面变成空壳 | 中 | 任务 4 删除 `SyncStatus.tsx` 的页面逻辑，保留 `SyncStatusBadge` 即可 |

## 不在范围

- 后端任何改动
- akshare 真实数据源接入
- 移动端响应式重新设计
- 任何新增依赖

## 状态

- [x] 设计已确认
