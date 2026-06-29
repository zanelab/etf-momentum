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
