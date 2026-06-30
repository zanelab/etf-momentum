# 开发日志

## 初始化

- 日期：2026-06-28 初始化 SpecCoding 结构
- OpenSpec CLI v1.3.1 已配置（spec-driven）
- 工作流骨架就位：spec/、openspec/、AGENTS.md、backend/、frontend/
- 架构选型确认：全栈 React 前端 + Python 后端
- Git 仓库初始化（main 分支，commit `7529e74`）
- 启动首个变更 `bootstrap-fullstack`（feature 分支，commit `8a5648d`）
- 状态：phase=init，可进入 proposal 阶段

## bootstrap-fullstack 变更归档

- 日期：2026-06-28（plan 72/72，10 个 commit）
- 分支：`feature/bootstrap-fullstack`
- 归档目录：`openspec/changes/archive/bootstrap-fullstack-20260628/`
- 范围：完整前后端骨架 + 全部 M0–M8 里程碑
- 关键产物：
  - **后端**：FastAPI + SQLModel + SQLite；11 个端点；74 个 pytest 用例
  - **前端**：React + Vite + TS + TanStack Query + recharts；8 个页面
  - **筛选核心**：`filter_etfs` 从 `main.py` 迁移至 `backend/app/services/screening.py`，移除 JoinQuant 全局依赖
  - **JoinQuant 兼容**：`_jq_shim.py` + `test_screening_parity.py` 三个对照测试（default / industry-diverse / ma-filter-off）确认迁移后行为与原版一致
  - **回测引擎**：日级重放 + equal-weight + 净值序列 + 5 项统计
  - **数据同步（mock）**：`daily_sync.sync_today()` 写 `data/daily_sync/YYYY-MM-DD.json`
  - **CI 验证**：`pytest` 74 passed / `ruff check` 通过 / `tsc --noEmit` 通过 / `npm run build` 通过
- 已知限制：
  - 行情数据为 GBM mock fixture（10 只 ETF × 500 天）
  - 持仓为 `portfolio_mock` 硬编码
  - 当日解析以 fixture 末日代替真实交易日历

## real-data-source 变更归档

- 日期：2026-06-29（plan 43/43，11 个 commit）
- 分支：`feature/real-data-source`
- 归档目录：`openspec/changes/archive/real-data-source-20260629/`
- 范围：真实数据源接入（akshare）+ 缓存装饰器 + 动态池管理 + 数据源观测面板
- 关键产物：
  - **`make_source(name)` 工厂**：根据 `ETF_DATA_SOURCE` 环境变量或 per-request 参数选择 `fixture` 或 `akshare`；akshare 路径自动包一层 `CachedSource`
  - **`AkShareSource`**：接入 akshare 的 `fund_etf_hist_em`（K 线）和 `fund_etf_spot_em`（全市场 ETF 列表，~1500 条）；含中文列名映射、指数退避重试、fixture 降级
  - **`CachedSource` 装饰器**：读穿透缓存到 SQLite `market_bar_cache` 表；暴露 `stats() / clear()`；命中/未命中计数器
  - **`retry_with_backoff` 工具**：指数退避，可配置重试次数与初始延迟
  - **动态池**：`DynamicPoolEntry` SQLModel 表 + 3 个端点（GET 列表 / POST sync / PATCH 切换启用）；sync 强制走 akshare（不受 `ETF_DATA_SOURCE` 影响），失败返回 503/502 明确错误
  - **观测**：`GET /api/health?stats=1` 在 CachedSource 时返回 `cache_hit` / `cache_miss` 计数
  - **前端**：`/datasource` 页面展示健康/缓存统计/动态池列表 + 同步按钮 + 行内启用开关
  - **CI 验证**：`pytest` 116 passed（新增 42 个用例）/ `ruff check` 通过（忽略 UP045 因为 venv 锁 py3.9）/ `tsc --noEmit` 通过 / `npm run build` 通过
- 已知限制：
  - 动态池同步仍需手动触发（`POST /sync` 或前端按钮），未做定时调度
  - akshare 返回 6 位裸码（如 `512650`），与静态池带后缀格式（如 `512650.XSHG`）未做归一化，`filter_etfs` 合并两池时需补一步
  - CachedSource 对 `history` 使用"日历超集"启发式，存在少量过度刷写缓存的情况
  - 同步任务尚未接入定时器（手动调用 `sync_today()`）
- 下一步：merge 阶段合入 main

## akshare-code-normalization 变更（执行中，2026-06-29）

- 日期：2026-06-29（real-data-source 归档后启动的新迭代）
- 范围：ETF 代码格式归一化（akshare 6 位裸码 ↔ 静态池带后缀格式）
- 关键产物：
  - **`app/data_sources/codes.py`**：新增 `normalize_etf_code(code) -> str` 与 `same_etf(a, b) -> bool`；规范格式 `XXXXXX.XSHG/XSHE`；交易所推断规则为首字符 5/6→SH、1/0/3→SZ
  - **`AkShareSource.all_etf_entries`**：返回前对每个 code 应用归一化（裸码 → canonical，非法 code 静默丢弃）
  - **`filter_etfs` 合并**：用 `{normalize_etf_code(c) for c in static + dynamic}` 去重；defensive 比对用 `normalize_etf_code(params.defensive_etf)`
  - **`load_display_names` 双查**：先按原 code 查 `static_pool`，未命中再按 canonical form 查；输出 key 保持输入形式
  - **动态池 sync upsert key**：sync 前先把存量裸码 row 迁移到 canonical form（同一标的不会出现两个 row）；PATCH 路径也对 code 参数做归一化
- CI 验证：`pytest` 159 passed（116 + 新增 43）/ `ruff check` 通过 / `tsc --noEmit` 通过 / `npm run build` 通过
- 设计依据：对照 `main.py:282` 显式融合逻辑（`list(set(STATIC_ETF_POOL + g_dynamic_pool))`）与 `main.py:131-133` 原版动态池拉取（JoinQuant `get_all_securities` 自带后缀），确认 akshare 与 JoinQuant 格式差异才是真正的语义不一致源
- 已知限制（仍是 M9 原始限制）：动态池手动同步、CachedSource 启发式过刷写

## user-journey-reorg 变更归档

- 日期：2026-06-29（spec + plan + 10 task 实施 + 1 fix wave，共 13 个 commit）
- 分支：`feature/user-journey-reorg`
- 设计/计划文档：
  - 设计 spec：`docs/superpowers/specs/2026-06-29-user-journey-design.md`
  - 实施 plan：`docs/superpowers/plans/2026-06-29-user-journey.md`
- 范围：用户旅程与导航重整——以"非投资者日常 P&L + 周度再平衡"为目标用户重塑 IA
- 关键产物：
  - **导航结构**：顶部 4 项（仪表盘/持仓/今日调仓/设置）+ 侧边栏 7+1（静态池/主题词典/策略参数/动态池 divider 回测/历史数据/数据源）；`AppShell.tsx` + `Sidebar.tsx`；通配 `*` → `/`；`/screening` → `/signals`
  - **首页 Dashboard**（`/`）：4 卡片——资产概览、今日需要做的、系统状态、当前持仓 Top 5；过期动态池 amber 横幅
  - **/signals 改版**：周度操作清单（要卖出的/要买入的表格 + 每行复制 + 全局复制完整清单 + 防御模式 banner + ▶ 进阶 per-ETF 表 + ▶ 原始输出 JSON）
  - **/dynamic-pool 独立页**：从原 `/datasource` 抽出
  - **打印**：`@media print` 隐藏 nav/aside/details，`/signals` 可单页打印
  - **后端扩展**：
    - `PortfolioResponse` 加 `available_cash` / `net_value`；`signals_today()` 移除 100k fallback
    - `ScreeningTodayResponse` 加 `details: list[ScreeningTargetDetail]`（momentum_score/annual_return/r2/volume_ratio?）；新增 `filter_etfs_detailed`，`filter_etfs` 保留为薄包装（`backtest.py` 不变）
  - **测试基础设施**：vitest + @testing-library/react + jsdom（devDeps）
- 实施过程：10 个 subagent-driven-development 任务 + 1 个 whole-branch review 后的 fix wave（实现 spec §5.3 进阶 + 3 个 one-liner 修复）
- CI 验证：
  - 前端：`npm test` 29 passed（vitest+RTL+jsdom）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest` 165 passed（159 + 6 新增）/ `uv run ruff check` 通过
  - 整合：manual smoke 待运行
- 已知限制（从 M9/M10 继承）：动态池手动同步、akshare 缓存过刷写
- 新增/已知 minor（已记录，留待后续 M11.1）：
  - `100_000.0` 资本硬编码在 `backend/app/api/screening.py` 三处
  - `setupFetchMock` 重复实现于 5 个测试文件（`/api/screening/today` mock 在 Dashboard/Signals 路径上是 dead）
  - 11 个文件缺尾部换行（含本次新增的多个）
  - `@vitest/ui` 已装但缺 `test:ui` script
  - 前端 `.toFixed()` 缺 `Number.isFinite` 防御（后端测试已覆盖）
- 下一步：merge 阶段合入 main

## dashboard-flatten 变更归档

- 日期：2026-06-29（4 个 commit — 3 feature + 1 chore followup）
- 分支：`feature/dashboard-flatten`（基于 user-journey-reorg HEAD `7549550` fast-forward 后的 main）
- 设计/计划文档：
  - 流程归属：**openspec**（非 docs/superpowers）——`openspec/changes/dashboard-flatten-20260629/{proposal.md, spec.md, plan.md}`
- 范围：Dashboard 化整为零——把周度操作清单与当前持仓从独立路由折叠进首页 Dashboard；顶层 IA 从 4-entry nav 收敛为 2-entry nav
- 关键产物（无后端改动）：
  - **路由清理**：`frontend/src/App.tsx` 移除 `<Route path="/portfolio">`、`<Route path="/signals">`、`<Route path="/screening">`（兼容重定向不再需要）；保留 `*` → `/` 通配
  - **顶部导航**：`AppShell.TOP_NAV` 由 4 项减为 2 项——`仪表盘` + `设置`（按钮唤起侧边栏）
  - **页面删除**：`frontend/src/pages/Portfolio.tsx`（85 行）与 `frontend/src/pages/Signals.tsx`（206 行）整文件删除
  - **Dashboard.tsx 内联**：新增完整 7 列持仓表卡片（代码/名称/数量/成本价/现价/市值/盈亏，不限 Top-5）；`今日需要做的` 卡片内联周度操作清单——SELL/BUY 表 + 每行 `📋 复制` + 全局复制按钮 + 防御模式 banner + `▶ 进阶` per-ETF 折叠（momentum_score/annual_return/r2/volume_ratio?）+ `▶ 原始输出` JSON 折叠
  - **测试迁移**：原 `Signals.test.tsx` 改名为 `Dashboard.signals.test.tsx`；新增 `Dashboard.holdings.test.tsx`（3 用例）；删除 `screening-redirect.test.tsx`；`app-shell-wiring.test.tsx` 断言更新为 2-entry nav
  - **chore followup**（commit `98dd65b`）：清理 Dashboard.tsx 内联段中残留的 stale `/signals` `/portfolio` 路径注释
- 实施过程：3 个 subagent-driven-development 任务（inline /signals / inline /portfolio / route+nav cleanup）+ 1 个 whole-branch review 触发的 chore followup
- CI 验证：
  - 前端：`npm test` **30 passed**（9 个 test files）/ `npm run lint`（tsc --noEmit）clean / `npm run build` 成功（dist 641.54 kB）
  - 后端：`uv run pytest -q` **165 passed**（沿用，无新增）/ `uv run ruff check` clean
  - 整合：manual smoke — `/` 渲染完整 Dashboard，无顶部链接指向 `/signals` 或 `/portfolio`；Settings 侧边栏照常
- 已知限制（从 user-journey-reorg 继承）：动态池手动同步、akshare 缓存过刷写
- 新增/已知 minor（留待后续 M12.1）：
  - `Dashboard.tsx` 中 `money` / `formatMoney` 辅助函数在资产概览卡与持仓表卡各重复实现一次（应抽出为共享 helper）
  - `Dashboard.test.tsx` 中测试名 `renders the four card headings` 现在略不准确——卡片总数仍为 4，但其中两张承载原独立页完整内容
  - 多处测试文件尾部换行不一致（沿用 M11.1 已知项）
- 下一步：merge 阶段合入 main

## etf-historical-sync 变更归档

- 日期：2026-06-29（6 个 commit — 1 backend refactor + 1 backend refactor fix + 1 backend api + 1 frontend hooks + 1 frontend page + 1 docs sync，共 6 个）
- 分支：`feature/etf-historical-sync`（基于 dashboard-flatten HEAD `d21e79d` fast-forward 后的 main）
- 流程归属：openspec（`openspec/changes/etf-historical-sync/{proposal.md, spec.md, plan.md}`）
- 范围：可观测性扩展——为 `static_pool ∪ dynamic_pool` 中每只 ETF 同步最新一根 bar 并暴露状态 API；新增 `/sync` 侧边栏页面
- 关键产物（无 frontend 路由变更 / 无 nav 顶导变更）：
  - **后端服务**：`sync_historical_for_pool(codes)` 替代原 `sync_today()`；后者保留为薄包装；每行新增 `status` / `error` 字段
  - **后端 API**：`GET/POST /api/sync/historical/{status,trigger}`（`backend/app/api/sync.py`）；`lifespan` 启动同步容错化
  - **前端 hooks**：`useSyncStatus()` / `useTriggerSync()`（`@/api/hooks.ts`）
  - **前端页面**：`/sync` 表格 4 列 + 立即同步按钮 + 空池子占位；`Sidebar` 的 `TOOL_ENTRIES` 增补"数据同步"项
- CI 验证：
  - 前端：`npm test` 33 passed（30 既有 + 3 新增）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest -q` 172 passed（165 既有 + 7 新增）/ `uv run ruff check` 通过
- 已知限制（继承 M11.1）：mock 路径仅同步 fixtures；akshare 真实数据源在 `_read_latest_bar` 抽象处替换时需要新增 akshare 调用 + 重试
- 新增/已知 minor（留待后续 M12.x）：
  - `useSyncStatus` refetchInterval=10s；同步刚完成后未立即刷新到 UI（mutation onSuccess 已 invalidate，可考虑更短 polling）
  - `_read_latest_bar` 接口预留 akshare 注入点；当前实现仅 fixtures
- 下一步：merge 阶段合入 main

## dynamic-pool-consolidate 变更归档

- 日期：2026-06-29（plan 6/6，6 个 commit — 1 refactor + 1 refactor fix + 1 page extension + 1 new page + 1 fix wave + 1 cleanup + 1 docs sync；外加 manual smoke）
- 分支：`feature/dynamic-pool-consolidate`（基于 etf-historical-sync HEAD `bb480ea` fast-forward 后的 main）
- 流程归属：openspec（`openspec/changes/dynamic-pool-consolidate/{proposal, design, spec, plan}.md`）
- 范围：纯前端 IA 重构——3 个并列工具页（`/dynamic-pool` `/history` `/sync`）合并为 1 个动态池中枢 + 1 个下钻子页
- 关键产物：
  - **`<SyncStatusBadge>` 抽取**：从 `SyncStatus.tsx` 内部实现提到 `frontend/src/components/`，主页表格与下钻子页共用（Task 1）
  - **主页 `/dynamic-pool` 扩展**（Task 2）：双同步按钮（互斥 disabled；空池仅「同步 ETF 历史数据」disabled）+ 表格新增「历史同步状态」列（4 徽章）+ 行点击下钻 + 行内 checkbox stopPropagation + tabIndex+Enter 键盘可达
  - **子页 `/dynamic-pool/:code`（新）**（Task 3）：标题 `<code> · <name>` + 顶部「← 返回动态池」+ 池外 ETF 软兜底（amber 警示 + K 线仍渲染）+ recharts K 线（ComposedChart close+volume，沿用 `useMarketHistory` 的 `rows` 字段）
  - **路由与侧边栏清理**（Task 4）：删除 `/history` 与 `/sync` 路由 + `History.tsx` + `SyncStatus.tsx` + `SyncStatus.test.tsx`（3 个旧测试随页面删除）；`TOOL_ENTRIES` 由 4 → 2
  - **测试基础设施**：`ResizeObserver` polyfill 加到 `frontend/src/test/setup.ts`（jsdom 缺失；recharts ResponsiveContainer 需要）
- 实施过程：4 个 subagent-driven-development 任务（Task 1–4）+ Task 5 全栈 CI 验证 + Task 6 项目级 spec 同步。Task 3 一轮 fix wave（commit 6419635）修复 review 发现的 2 Important + 1 Minor：`<button>` 还原为 `<Link>`（可访问性）、`<h3>` 前缀还原匹配 `History.tsx`、trailing newlines、测试断言收紧（`getByRole("heading", { level: 2 })` + `<a href>` 属性断言以绕开 `<Link>`→`useNavigate` ESM closure mock 限制）
- CI 验证：
  - 前端：`npm test` 38 passed（33 既有 + 4 DynamicPoolPage 新增 + 4 EtfDetailPage 新增 - 3 SyncStatus 旧用例删除 = 净增 5）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest -q` 172 passed（沿用，无新增）/ `uv run ruff check` 通过
  - 整合：manual smoke 待运行（Task 5 清单）
- 已知限制（继承 M12）：mock 路径仅同步 fixtures；akshare 真实数据源在 `_read_latest_bar` 抽象处替换时需要新增 akshare 调用 + 重试
- 新增/已知 minor（留待后续 M13.x）：
  - 子页 K 线的「字段选择」（open/high/low/volume）原 `History.tsx` 提供，本变更收敛为只显示 close + volume（简化版）
  - 下钻子页未复用 `useMarketList` 的下拉（沿用动态池的 code 上下文）
  - `useMarketList` 与 `useMarketHistory` 仍导出但前端无使用方（保留 hooks 不变，待后续清理）
- 下一步：merge 阶段合入 main

## add-sync-progress-ui 变更归档

- 日期：2026-06-29（plan 50/50，10 个 commit — 4 docs + 6 feature/fix）
- 分支：`feature/add-sync-progress-ui`（基于 dynamic-pool-consolidate HEAD `f902f39` fast-forward 后的 main）
- 流程归属：openspec（`openspec/changes/add-sync-progress-ui/{proposal.md, design.md, spec.md, plan.md}`）
- 范围：同步进度可视化 + 日期范围支持——把粗粒度「同步中…」按钮 disabled 升级为细粒度 (code, date) 进度展示，同时让「补同步一段历史」成为一等操作
- 关键产物：
  - **后端服务**：
    - `app/services/sync_progress.py`（**新**）：`SyncProgressTracker` 进程内单例（`dict[code, ProgressInfo]`）；`ProgressInfo` Pydantic 模型；模块级 `tracker = SyncProgressTracker()` 实例
    - `app/services/daily_sync.py`（**改**）：`sync_historical_for_pool(codes, from_date, to_date)` 双层循环重构（外 code、内 offset），每步更新 tracker；新增 `_read_bar_for_date(code, target_date)`；`sync_today(target_date)` 保留为薄包装
    - `app/main.py`（**改**）：startup hook 改用 30 天窗口（`from=today-30, to=today`）
    - `app/api/sync.py`（**改**）：`trigger_sync` 改 `Query` 参数（`from_date` / `to_date` 必填）；4 条 400 校验（from>to / from 在未来 / 跨度>730 / 并发防御）；`get_sync_status` 合并 `in_progress` + `is_running`；`MAX_RANGE_DAYS = 730`
    - `app/schemas.py`（**改**）：`SyncStatusResponse` 扩展 `in_progress` / `is_running`；`SyncTriggerResult` 扩展 `from_date` / `to_date` 回显
  - **前端组件**：
    - `<DateRangePicker>`（**新**）：Modal + 2 个 `<input type="date">` + 「开始同步」「取消」；客户端预校验（from<=to + 跨度<=730，对齐后端）；错误 `role="alert"` 内联
    - `<SyncProgressBanner>`（**新**）：表格顶部横幅；`done/max(overall_index)/overall_total` + 百分比进度条 + 当前 code / `current_date` / `total_days` 天
    - `<RowProgressBar>`（**新**）：表格行内进度条 + `aria-valuenow` + `current_date / total_days 天` 文本
    - `<SyncStatusBadge>`（**未改**：本期不需要，in-progress 行渲染 `<RowProgressBar>`，其余行照旧）
  - **前端 hooks/页面**：
    - `useTriggerSync`（**改**）：签名变 `mutate({ from_date, to_date })` 必填，URL 拼 query string
    - `useSyncStatus`（**未改**：保留 10s 轮询；现在终于有意义了）
    - `DynamicPoolPage`（**改**）：接入 `DateRangePicker`；新增 `pickerOpen` / `syncError` state；`anyPending` 增加 `isRunning` 维度（按钮在 sync 期间也 disabled）；in-progress 行渲染 `<RowProgressBar>`；`SyncProgressBanner` 条件渲染
  - **测试**：
    - 后端：5（tracker 单测） + 5（daily_sync 扩展：`_read_bar_for_date` 3 + `sync_historical_for_pool` 2） + 7（api 端点：422 / 400×4 / 200 / 并发 / inactive） + 1（fix 追加并发 trigger） = 19 新增，191 总量（172 → 191）
    - 前端：8（DateRangePicker 含 730-day） + 3（SyncProgressBanner） + 2（RowProgressBar） + 1（useTriggerSync mutation） + 4（DynamicPoolPage 集成） = 18 新增，56 总量（38 → 56）
- 实施过程：6 个 subagent-driven-development 任务（Task 1–6）+ Task 7 全栈 CI 验证 + final review 触发的 fix wave（commit 73cee3f：730-day 客户端校验 + 并发 trigger 测试）
- CI 验证：
  - 前端：`npm test` 56 passed（11 个 test files）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest -q` 191 passed / `uv run ruff check` clean
  - 整合：manual smoke 11/11 步骤通过 — Modal 弹出 / 默认值 / 校验 / 范围触发 / Network 观察 / 进度展示 / 行内 / 完成后清除 / 按钮 disabled / 后端 400 / 跨 tab refetch
- 已知限制（Minor，不阻塞）：
  - `_read_bar_for_date` 每次调用 `pd.read_csv` 全量读 fixture（47 codes × 200 days ≈ 9400 次读）；mock 路径无感，真实数据源接入后需替换实现或加缓存
  - `_read_latest_bar` 现为 dead code（被 `_read_bar_for_date` 替代），可后续清理
  - 进度展示依赖 10s 轮询；极短同步（< 10s）可能错过横幅展示（mock fixture 实测 < 1s），但 `refetchOnWindowFocus` 切回 tab 兜底
- 新增/已知 minor（留待后续 M14.x）：
  - `useDynamicPool` 5s 轮询仍在 `/dynamic-pool` 运行（独立 PR 处理）
  - 同步运行时如需「取消」按钮需新增 `POST /api/sync/historical/cancel` 端点（本期 out-of-scope）
- 下一步：merge 阶段合入 main

## drop-dynamic-pool-polling 变更归档

- 日期：2026-06-30（plan 12/12，1 个 commit — `132c834`）
- 分支：`feature/drop-dynamic-pool-polling`（基于 main `e56cd43` 启动）
- 流程归属：openspec（`openspec/changes/drop-dynamic-pool-polling/{proposal.md, spec.md, plan.md}`）
- 范围：动态池轮询收敛——删除 `useDynamicPool` 的 5s 轮询，依赖 mutation-driven refresh（已有）+ TanStack Query 默认 `refetchOnWindowFocus: true` 兜底跨 tab 同步
- 关键产物（极小变更，1 行代码 + 2 测试）：
  - **前端 hooks**：`useDynamicPool`（`frontend/src/api/hooks.ts:372-378`）删除 `refetchInterval: 5_000`；其他 5 个有 refetchInterval 的 hook 不动（`useScreeningToday` / `usePortfolio` / `useSignalsToday` / `useHealthStats` / `useSyncStatus` 各自有轮询依据）
  - **测试**：`DynamicPoolPage.test.tsx` 新增 2 个测试——「停留 30s 只 1 次请求」（fake timer 限定 `setInterval`/`clearInterval` 避免 `waitFor` 死锁）+ 「mutation 后 refetch 触发」
- 实施过程：1 个 subagent-driven-development 任务（Task 1）+ Task 2 用户决定 skip smoke + final review（trivial 1-line 变更，2 个单测覆盖核心行为）
- CI 验证：前端 `npm test` 58 passed（56 既有 + 2 新增）/ `tsc --noEmit` 通过 / `npm run build` 成功
- 已知限制：无
- 下一步：merge 阶段合入 main

## sync-cancel 变更归档

- 日期：2026-06-30（plan 30/30，7 个 commit — `1ab6198` / `4e3e244` / `350003b` / `a24d4c2` / `4ca15df` / `4f90656` / `066faa4`）
- 分支：`feature/sync-cancel`（基于 main `fe2fe60` 启动；post-M15 merge）
- 流程归属：openspec（`openspec/changes/sync-cancel/{proposal.md, spec.md, plan.md}` + design 写在 proposal 内）
- 范围：M14 的「同步 ETF 历史数据」目前是同步阻塞的（`trigger_sync` 调 `sync_historical_for_pool` 等完成才返回），HTTP 请求未释放导致用户根本无法取消。本变更让用户可以中途取消
- 核心约束：必须先把 sync 移到后台（FastAPI `BackgroundTasks`），trigger 立即返回，再单独 POST `/cancel`
- 设计决策：
  - 执行模型：FastAPI `BackgroundTasks`（trigger 立即返回 + 后台跑 + cancel 单独 POST）
  - 取消时机：下一 (code, date) 边界停止（不强中断正在执行的 `_read_bar_for_date`——I/O 中断语义复杂）
  - 取消后 UI：Banner 变红 + 部分进度；新增 `is_cancelled` 字段标识
- 关键产物：
  - **后端**：
    - `SyncProgressTracker`（`backend/app/services/sync_progress.py`）：新增 `_cancel_requested: bool` 字段 + `cancel()` / `is_cancel_requested()` / `reset_cancel()` 方法 + 新增 `clear_progress()` 方法（只清 `_by_code` 保留 cancel flag）。`clear()` 既有方法同步 reset cancel flag（保持向后兼容）
    - `sync_historical_for_pool`（`backend/app/services/daily_sync.py`）：循环开头 `tracker.reset_cancel()`（防 stale flag）；每步后 `tracker.set(...)` 之后检查 `tracker.is_cancel_requested()`，true 时 `break` 内层 + Python `for/else/break` 模式 break 外层；summary JSON 仍写（部分 rows）
    - `trigger_sync`（`backend/app/api/sync.py`）：改用 FastAPI `BackgroundTasks` + `_run_sync_and_clear` 包装 closure（finally 中调 `tracker.clear_progress()` 保证正常路径清进度；cancel 路径保留 flag 让前端看到）
    - `POST /api/sync/historical/cancel`（同文件）：`tracker.is_active()` 检查后调 `tracker.cancel()`，返回 `CancelResult(cancelled=True)`，无 sync 跑时 400
    - `SyncStatusResponse`（`backend/app/schemas.py`）：新增 `is_cancelled: bool = False` 字段（向后兼容）
    - `CancelResult`（同文件）：新 Pydantic schema `{cancelled: bool}`
  - **前端**：
    - `useCancelSync`（`frontend/src/api/hooks.ts`）：TanStack Query mutation，POST 到 `/api/sync/historical/cancel`，onSuccess invalidate `["sync-historical-status"]`
    - `SyncStatusResponse` TS 类型：新增 `is_cancelled: boolean`
    - `useTriggerSync.onSuccess`：移除 `setQueryData`（避免与 status poll 竞速；status poll 已覆盖）
    - `<SyncProgressBanner>`（`frontend/src/components/SyncProgressBanner.tsx`）：新增 `isCancelled?: boolean` prop，true 时切换 `bg-red-50`/`bg-red-500`/`bg-red-100` + 头部「已取消」+ 当前 label 改「已同步」
    - `<DynamicPoolPage>`（`frontend/src/pages/DynamicPoolPage.tsx`）：新增「取消」按钮（仅 `inProgress.length > 0 && !isCancelled` 时显示，pending 时 disabled）
- 实施过程：5 个 subagent-driven-development 任务（Tasks 1-5，全部 review clean）+ Task 6 CI 验证（用户决定 skip smoke + final review）
- Bug 修复（实施中发现）：
  - **fix1** `a24d4c2`：Task 3 把 `trigger_sync` 改为异步后丢了 `tracker.clear()` 调用（同步 → 异步，原 API 层 clear 没了）。通过 `_run_sync_and_clear` 包装 closure 恢复 cleanup；3 个既有 trigger 测试（断言旧同步语义）需更新匹配新异步行为
  - **fix2** `4ca15df`：cancel-path lifecycle — wrapper 原用 `if not is_cancel_requested: clear()`，结果 cancel 路径 `_by_code` 留着，`is_active()` 一直 True，`/status` 返回 `is_running=True` 不符合 spec "下次 status 轮询看到 is_running=false"。新增 `tracker.clear_progress()`（只清 `_by_code` 不动 cancel flag），wrapper 改为无条件 `clear_progress()`。Cancel 路径现在返回 `is_running=false, is_cancelled=true`
- CI 验证：
  - 前端：`npx vitest run` 64 passed（15 files，58 既有 + 1 useCancelSync + 2 banner + 3 page）/ `tsc --noEmit` 通过 / `npm run build` 通过
  - 后端：`uv run pytest -q` 202 passed（191 既有 + 4 tracker + 2 daily_sync + 5 sync_cancel api = +11 新增；3 既有测试更新）/ `uv run ruff check` clean
- 已知限制（Minor，不阻塞）：
  - BackgroundTasks 跨进程重启丢失（mock 路径无影响；前端 status poll 看到 `is_running=false` 后 UI 复位）
  - `useTriggerSync` 移除 setQueryData 导致「空状态」瞬间（trigger 响应带 `is_running=true, in_progress=[]`；前端 10s 内 status poll 拿到真实进度）
  - cancel race：cancel 到达时 sync 恰好完成（cancel 端检查 `tracker.is_active()`，如果 sync 已完成 tracker 已 clear，会返回 400——这是预期行为）
  - `_read_bar_for_date` 在 cancel flag 检查前阻塞 I/O（mock 路径 < 1ms/步；真实数据源可能 50-200ms 延迟，本期接受这个粒度）
- 下一步：merge 阶段合入 main
