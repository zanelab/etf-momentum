# 项目需求

## 项目概述

将原聚宽（JoinQuant）ETF 动量轮动策略重构为前后端分离的全栈应用。

策略核心保持不变（静态+动态池融合、双均线过滤、动量评分、行业分散、止损、防御 ETF），但参数和池子从硬编码改为前端可配置；筛选/回测逻辑从单文件脚本迁移到后端服务；前端提供可视化与交互入口。

## 核心功能

### 前端（React）

| 功能 | 说明 |
|------|------|
| 静态核心池配置 | 增删改查核心 ETF 列表（替代原 `STATIC_ETF_POOL`） |
| 主题分类词典配置 | 增删改查主题关键词映射（替代原 `THEME_KEYWORDS`） |
| 策略参数配置 | 可视化编辑动量周期、均线周期、止损比例、防御 ETF 等（替代原 `STRATEGY_CONFIG`） |
| 回测执行与展示 | 选择时间区间、执行回测、展示净值曲线与统计指标 |
| ETF 历史数据查询 | 单只 ETF 的历史 K 线、成交额、动量评分查询 |
| 当日买入/卖出信号 | 展示当日 `filter_etfs()` 选中的标的与调仓建议 |
| 当前持仓展示 | 持仓清单、成本价、浮动盈亏、止损线 |

### 后端（Python）

| 功能 | 说明 |
|------|------|
| 配置持久化 API | 静态池、主题词典、策略参数的 CRUD |
| ETF 筛选 API | 接收前端配置，调用核心 `filter_etfs()` 逻辑，返回当日目标列表 |
| 历史数据 API | 行情数据查询（K 线、成交额等） |
| 回测 API | 在选定时间区间上重放筛选逻辑，计算净值与统计 |
| 当日买入/卖出信号 API | 与筛选 API 类似，但额外返回调仓建议（卖出列表 + 买入列表 + 数量） |
| 持仓 API | 当前持仓、成本价、市值、盈亏 |
| 收盘数据同步 | 每日收盘后拉取真实/模拟行情，写入数据库 |

## 非功能需求

- **API 风格**：RESTful，JSON over HTTP
- **数据存储**：配置数据可用关系型 DB（SQLite 起步，便于后续迁移 Postgres）；行情/回测结果历史可入库
- **数据源**：抽象数据源接口（`MarketDataSource`），至少实现一个 mock/本地数据源 + 一个真实源（akshare）；通过 `make_source(name)` 工厂按 `ETF_DATA_SOURCE` 环境变量或 per-request 参数切换；akshare 路径自动缓存
- **回测**：后端串行执行，避免阻塞 API（可用异步任务或同步短任务）
- **测试**：核心筛选逻辑必须有单测覆盖（TDD 强制，参见 AGENTS.md）
- **动态池管理**：用户可拉取 akshare 全市场 ETF 列表入本地表，勾选启用哪些进入筛选；同步失败必须返回明确错误（不可静默回退）

## 数据源切换与缓存（real-data-source 2026-06-29）

- **数据源**：`ETF_DATA_SOURCE` 环境变量决定默认源（`fixture` / `akshare`）；也支持 `?source=akshare` per-request 覆盖（行情、筛选、信号、回测接口均接受）
- **akshare 缓存**：`CachedSource(AkShareSource)` 自动写入 SQLite `market_bar_cache` 表；hits / misses 由 `/api/health?stats=1` 暴露
- **动态池同步**：`POST /api/configs/pool/dynamic/sync` 必须走 akshare（不受 `ETF_DATA_SOURCE` 影响）；返回 200 `{synced, total, enabled}` / 503 akshare 缺失 / 502 akshare 拉取失败
- **前端面板**：`/datasource` 页面展示健康状态、缓存命中统计、动态池列表与同步按钮

## ETF 代码归一化（akshare-code-normalization 2026-06-29）

- **规范格式**：系统内 ETF 代码统一使用 `XXXXXX.XSHG`（上海）或 `XXXXXX.XSHE`（深圳）带后缀形式；akshare 返回的 6 位裸码由 `app/data_sources/codes.normalize_etf_code` 在 4 个接入点统一归一（akshare 返回、动态池 upsert key、`filter_etfs` 池合并、`load_display_names` 查表）
- **交易所推断**：6 位裸码首字符规则 — 5/6 → XSHG、1/0/3 → XSHE
- **向后兼容**：所有归一化点同时接受裸码与带后缀输入；存量裸码 row 在下次 `POST /api/configs/pool/dynamic/sync` 时自动迁移到 canonical form

## 用户旅程重整（user-journey-reorg 2026-06-29）

- **目标用户重定位**：非投资者日常用户——每日上来查看盈亏，每周依据调仓信号做一次再平衡。整套 IA 与文案围绕此重组
- **导航结构**：
  - **顶部 4 项**：`仪表盘` (/)、`持仓` (/portfolio)、`今日调仓` (/signals)、`设置`（按钮 → 唤起侧边栏）
  - **侧边栏 7+1**（divider 分隔）：`静态池` (/pool)、`主题词典` (/themes)、`策略参数` (/strategy)、`动态池` (/dynamic-pool)、divider、`回测` (/backtest)、`历史数据` (/history)、`数据源` (/datasource)
  - **通配路由**：未知 URL 跳转 `/`（避免空白页）
  - **兼容路由**：`/screening` 301-equivalent 重定向到 `/signals`
- **首页 Dashboard（4 卡片）**：资产概览（净值/市值/成本/盈亏/可用）、今日需要做的（动作数 + CTA）、系统状态（健康/缓存/动态池/最后同步）、当前持仓 Top 5
- **/signals 改版**：周度操作清单——`要卖出的` / `要买入的` 表格（代码/名称/数量/金额 + 每行 `📋 复制`）+ 全局 `📋 复制完整调仓清单` + `▶ 进阶：为什么这样选`（per-ETF 动量分/年化/R²/量比）+ `▶ 原始筛选输出` JSON 折叠 + 防御模式 banner
- **/dynamic-pool 独立成页**：从原 `/datasource` 抽出；侧边栏独立入口
- **过期感知**：动态池 `last_synced_at` > 24h → Dashboard 顶部黄色 `⚠ 动态池已过期` 横幅 + 立即同步链接
- **打印友好**：`@media print` 隐藏 `header nav` / `aside` / `details`，将 `/signals` 渲染为单页操作清单
- **后端扩展**：
  - `PortfolioResponse` 新增 `available_cash`（`100_000 − total_cost`）与 `net_value`（`market_value + available_cash`）；`signals_today()` 不再硬编码 100k fallback，`total_value` 改由 `available_cash + total_market_value` 推导
  - `ScreeningTodayResponse` 新增 `details: list[ScreeningTargetDetail]` 字段（每标的：momentum_score / annual_return / r2 / volume_ratio?），前端 `▶ 进阶` 折叠表使用；`targets: list[str]` 保留做向后兼容
  - 新增 `filter_etfs_detailed(...)` 服务函数，保留 `filter_etfs` 旧签名（`backtest.py` 不变）
- **测试覆盖**：前端 vitest + RTL + jsdom（29 用例覆盖 AppShell/Sidebar/Dashboard/Signals/DynamicPoolPage/screening-redirect/app-shell-wiring/stale-sync）；后端 pytest 165 用例（含 M11 新增 2）

## Dashboard 化整为零（dashboard-flatten 2026-06-29）

- **目标**：进一步简化 IA——把"周度再平衡"用户最常用的两类信息（调仓清单 + 当前持仓）从独立路由折叠进首页 Dashboard；让"一次访问 = 一次决策完成"
- **导航结构**：
  - **顶部 2 项**：`仪表盘` (/) + `设置`（按钮 → 唤起侧边栏）
  - **侧边栏 7+1 不变**（divider 分隔）：`静态池` (/pool)、`主题词典` (/themes)、`策略参数` (/strategy)、`动态池` (/dynamic-pool)、divider、`回测` (/backtest)、`历史数据` (/history)、`数据源` (/datasource)
  - **路由清理**：移除 `/signals` 与 `/portfolio` 路由；移除 `/screening` → `/signals` 兼容重定向（不再需要）
  - **通配路由**：未知 URL 跳转 `/`（保留）
- **首页 Dashboard 卡片重排**（cards 仍是 4 张，但其中两张承载原独立页内容）：
  - **资产概览**（净值/市值/成本/盈亏/可用）
  - **今日需要做的**（动作数 + CTA；内联完整周度操作清单——`要卖出的` / `要买入的` 表格含代码/名称/数量/金额 + 每行 `📋 复制` + 全局 `📋 复制完整调仓清单` + 防御模式 banner + `▶ 进阶：为什么这样选` per-ETF 折叠表 + `▶ 原始筛选输出` JSON 折叠）
  - **系统状态**（健康/缓存/动态池/最后同步；过期动态池 amber 横幅 + 立即同步链接）
  - **当前持仓**（完整 7 列持仓表：代码/名称/数量/成本价/现价/市值/盈亏——不再是 Top-5）
- **文件层面**：删除 `frontend/src/pages/Portfolio.tsx` 与 `frontend/src/pages/Signals.tsx`；`Dashboard.tsx` 整合两个卡片，新增 `Dashboard.holdings.test.tsx` + `Dashboard.signals.test.tsx`；移除 `screening-redirect.test.tsx`
- **后端**：无改动（沿用 user-journey-reorg 产出的 `PortfolioResponse` 与 `ScreeningTodayResponse` / `details` 字段）
- **设计依据**：openspec 流程而非 docs/superpowers 流程——`openspec/changes/dashboard-flatten-20260629/{spec,plan,proposal}.md`
- **测试覆盖**：前端 vitest 30 passed（9 个测试文件：AppShell/Sidebar/Dashboard/Dashboard.holdings/Dashboard.signals/Dashboard.stale-sync/DynamicPoolPage/app-shell-wiring/setup）；后端 pytest 165 passed（沿用，无新增）

## ETF 历史数据同步可观测（etf-historical-sync 2026-06-29）

- **目标**：解决"某只 ETF 是不是真的同步上了最新一天的数据？"的可观测性盲区
- **数据范围**：`static_pool ∪ dynamic_pool`（去重）；每只 ETF 仅同步最新一根 bar（mock 走 fixtures；akshare 走真实源；接口已抽象为 `_read_latest_bar(code)`，生产实现待后续替换）
- **同步触发**：
  - 启动期（FastAPI `lifespan`）：失败容错，记录日志，**不**阻塞应用
  - 手动：`POST /api/sync/historical/trigger`
- **同步状态**：`ok` / `failed`（含 `error`）/ `missing`（数据源无该 ETF）；失败隔离——单只失败不阻塞其他
- **API**：
  - `GET /api/sync/historical/status` → `{as_of, etfs: [{code, name, last_synced_date, status, error?}]}`；池子未同步过的 ETF 标记 `status: "never"`
  - `POST /api/sync/historical/trigger` → 同 schema + `synced_count` + `run_at`
- **前端**：侧边栏"数据同步"入口 → `/sync`；表格 4 列（代码 | 名称 | 同步日期 | 状态）；状态徽章 `✓ 已同步` / `⚠ 失败` / `— 缺失` / `— 未同步`；立即同步按钮（loading 期间禁用）；空池子显示 `暂无 ETF`
- **持久化**：摘要 JSON 写入 `backend/data/daily_sync/{YYYY-MM-DD}.json`（与原 mock 路径一致，row 扩展 `status` / `error` 字段）
- **测试覆盖**：后端 pytest 172 用例（含本变更新增 7 个：sync_for_pool 3 个 + sync_api 4 个）；前端 vitest 33 用例（含本变更新增 3 个）

## 待用户确认

- 数据源：是否已有可用数据源（如 akshare、tushare、聚宽自带）？还是先 mock？
- 回测粒度：分钟级 / 日级？
- 部署形态：本地启动 / Docker / 远端？

## 已确认（M0 决议 2026-06-28）

- **数据源**：起步使用 mock（`backend/app/data_sources/fixture.py` 提供 GBM 生成的 10 只代表性 ETF × 500 个交易日的 OHLCV），生产接入通过替换 `MarketDataSource` 实现完成
- **回测粒度**：日级（API 强约束：单次回测 ≤ 366 天）
- **部署形态**：本地启动 — 后端 `uvicorn app.main:app --port 8000`，前端 `npm run dev`（Vite 代理 `/api` → `localhost:8000`）