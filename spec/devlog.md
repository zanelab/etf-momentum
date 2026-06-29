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
