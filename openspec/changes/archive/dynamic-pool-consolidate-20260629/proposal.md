# Proposal: dynamic-pool-consolidate

## What

将当前的 3 个侧边栏工具页——`动态池 (/dynamic-pool)`、`历史数据 (/history)`、`数据同步 (/sync)`——合并成**单个 `动态池` 页面**，作为「池内 ETF 的全生命周期管理中枢」：

- **写侧（顶部按钮区）**：
  - `同步 ETF`：保留现有 `POST /api/configs/pool/dynamic/sync` 行为，从 akshare 拉全市场 ETF 列表入本地动态池
  - `同步 ETF 历史数据`：保留现有 `POST /api/sync/historical/trigger` 行为，为 `static_pool ∪ dynamic_pool` 每只 ETF 拉最新一根 bar
- **读侧（行级下钻）**：动态池表格行点击 → 跳转到新子路由 `/dynamic-pool/{code}`，该子页直接渲染该 ETF 的历史 K 线（沿用 `useMarketHistory`）+ 时间区间 + 字段选择
- **同步状态可观测**：动态池表格新增 `历史同步状态` 列，复用现有 4 个状态徽章（`✓ 已同步` / `⚠ 失败` / `— 缺失` / `— 未同步`），数据源为 `GET /api/sync/historical/status`

**路由收编**：
- 保留：`/dynamic-pool`（主页面）、新增 `/dynamic-pool/:code`（下钻子页）
- 删除：`/history`、`/sync`
- 侧边栏移除 `历史数据` 与 `数据同步` 两项

## Why

- **IA 重复**：动态池表格的「上次同步」列、`SyncStatus` 表格、`History` 表格三者在「池内 ETF」这一维度上语义重叠，用户从「动态池」到「它的同步状态」到「它的历史」要跨 3 个页面
- **写侧从未被单独需要**：两个同步操作（同步 ETF / 同步历史）的触发时机和受众高度重合（都是「刚改完池子想看效果」），分散在 3 个页面只会增加点击成本
- **下钻模型是更自然的认知流**：从「池子是什么」到「某只具体 ETF 怎么样」是层层聚焦，而不是平铺的 3 个并列页面

## Scope

- [ ] backend（无后端改动；复用现有 `/api/configs/pool/dynamic/*`、`/api/sync/historical/*`、`/api/market/history`）
- [ ] frontend（页面合并 + 路由清理 + 子路由 + 表格列扩展 + sidebar 收编）

## Acceptance Criteria

- [ ] `/dynamic-pool` 单页面同时承载「同步 ETF」与「同步 ETF 历史数据」两个操作按钮（带 loading 态、错误态）
- [ ] `/dynamic-pool` 表格新增 `历史同步状态` 列，使用与原 `SyncStatus` 一致的 4 个徽章
- [ ] 点击 `/dynamic-pool` 表格行 → 导航到 `/dynamic-pool/{code}` 子路由，渲染该 ETF 的 K 线 + 成交量 + 字段选择
- [ ] `/dynamic-pool/{code}` 页面有 `← 返回动态池` 入口（链接回 `/dynamic-pool`）
- [ ] 路由 `/history` 与 `/sync` 被删除（侧边栏不再出现这两项；浏览器访问这两个 URL 落到通配 `*` → `/`）
- [ ] 侧边栏 `TOOL_ENTRIES` 由 4 项减为 2 项（仅剩 `回测` + `数据源`）
- [ ] 现有后端测试（172 用例）全部保留通过；前端 vitest ≥ 33 用例全绿；新增/迁移测试覆盖新行为（行点击下钻、状态列渲染、404 兜底）
- [ ] `tsc --noEmit` / `ruff check` / `npm run build` 全绿
- [ ] 项目级 `spec/requirements.md` 增加 M13 章节，`spec/tasks.md` 增加 M13 详细条目，`spec/structure.md` 反映新页面布局与路由

## Out of Scope

- 后端 API 改造（不动 `daily_sync` / `sync_api` / `market` 任一端点）
- 池子筛选/启用/删除/排序逻辑调整（沿用 `useDynamicPool` / `useToggleDynamicEntry`）
- akshare 真实数据源接入（仍走 fixture mock，遵循 M12 已知限制）
- `useSyncStatus` 的 polling 间隔调整（10s 沿用）
- 移动端响应式重新设计

## Status

- [x] 提案已确认
