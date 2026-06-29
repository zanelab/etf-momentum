# 里程碑任务

## 总览

| 版本 | 主题 | 状态 |
|------|------|------|
| M0 | 项目初始化 | ✅ 完成 |
| M1 | 后端骨架与配置 CRUD | ✅ 完成 |
| M2 | 筛选核心迁移与单测 | ✅ 完成 |
| M3 | 当日信号与持仓 API | ✅ 完成 |
| M4 | 回测引擎 | ✅ 完成 |
| M5 | 前端配置面板（池子/词典/参数） | ✅ 完成 |
| M6 | 前端信号与持仓页 | ✅ 完成 |
| M7 | 前端回测页 | ✅ 完成 |
| M8 | 收盘数据同步（mock） | ✅ 完成 |
| M9 | 真实数据源接入（akshare + 缓存 + 动态池） | ✅ 完成 |
| M10 | ETF 代码归一化（akshare 6 位裸码 ↔ `XXXXXX.XSHG/XSHE`） | ✅ 完成 |
| M11 | 用户旅程与导航重整（顶部 4 + 侧边栏 7+1） | ✅ 完成 |
| M11.1 | Dashboard 化整为零（折叠 `/signals` `/portfolio`） | ✅ 完成 |
| M12 | ETF 历史数据同步可观测（per-ETF 状态 + /sync 页面） | ✅ 完成 |

## 详细任务

### M0 项目初始化

- [x] 创建 `openspec/`、`spec/`、`backend/`、`frontend/`
- [x] 安装 `AGENTS.md`
- [x] 起草 `spec/requirements.md`、`design.md`、`tasks.md`、`structure.md`
- [x] 初始化 Git 仓库
- [x] 创建首个 `openspec/changes/` 变更（`bootstrap-fullstack`，已归档）

### M1 后端骨架与配置 CRUD

- [x] FastAPI 项目结构
- [x] SQLite + SQLModel
- [x] `POST/GET/PUT/DELETE /api/configs/{pool|themes|strategy}`
- [x] 单测：配置 CRUD（`tests/test_configs.py`）

### M2 筛选核心迁移与单测（TDD 强制）

- [x] 将 `main.py` 的 `filter_etfs()` 迁移到 `backend/app/services/screening.py`
- [x] 去除 JoinQuant 全局函数依赖，改为显式参数
- [x] 用 mock 数据源 + 真实 `numpy/pandas` 逻辑写单测
- [x] JoinQuant shim 对照测试（`tests/test_screening_parity.py`，3 个用例）

### M3 当日信号与持仓 API

- [x] `GET /api/signals/today`（返回买卖建议）
- [x] `GET /api/portfolio`（当前持仓 + 市值 + 盈亏）
- [x] `GET /api/screening/today`（当日筛选目标）
- [x] 单测覆盖（`tests/test_signals.py` + `test_screening_api.py`）

### M4 回测引擎

- [x] `POST /api/backtest`（含 366 天窗口校验）
- [x] `GET /api/backtest/{task_id}`（BackgroundTask + JSON 文件持久化）
- [x] 日级重放 + 净值序列 + 统计（total_return / annualized_return / sharpe / max_drawdown / n_rebalances）
- [x] 单测覆盖（`tests/test_backtest.py`）

### M5 前端配置面板

- [x] React + Vite + TypeScript + Tailwind
- [x] 池子页（启用切换 / 删除 / 筛选）
- [x] 词典页（主题关键词分组编辑 + dirty/save）
- [x] 参数页（带类型校验的表单）
- [x] 调 M1 API

### M6 前端信号与持仓页

- [x] 信号页（卖出/买入卡片 + 原因/股数/盈亏）— 5s 轮询
- [x] 持仓页（市值/盈亏/总额）— 5s 轮询
- [x] 当日筛选目标页（chips）

### M7 前端回测页

- [x] 时间区间选择 + 回测触发（≤ 366 天）
- [x] recharts NAV 折线 + 4 项统计卡片
- [x] 任务状态轮询（2s，conditional）
- [x] 调 M4 API

### M8 收盘数据同步（mock）

- [x] `daily_sync.sync_today(target_date)` 读 fixture 末条写入 `backend/data/daily_sync/YYYY-MM-DD.json`
- [x] 当前以 fixture 末日作为 "today"（生产应替换为真实交易日历）

### M9 真实数据源接入（real-data-source 2026-06-29）

- [x] `make_source(name)` 工厂 + `ETF_DATA_SOURCE` 环境变量 + per-request `?source=` 参数
- [x] `AkShareSource` 适配（`fund_etf_hist_em` + `fund_etf_spot_em`，中文列名映射，指数退避重试，fixture 降级）
- [x] `CachedSource` 读穿透缓存 + SQLite `market_bar_cache` 表 + `stats()` / `clear()`
- [x] `retry_with_backoff` 工具
- [x] `DynamicPoolEntry` 模型 + 3 个动态池端点（list / sync / patch）
- [x] sync 强制走 akshare，失败返回 503/502 明确错误
- [x] `/api/health?stats=1` 暴露缓存命中统计
- [x] 前端 `/datasource` 页面（健康 + 缓存统计 + 动态池列表 + 同步按钮 + 行内启用）
- [x] 单测：新增 8 个测试文件 / 42 个用例（116 总数）
- [x] ruff / tsc / vite build 全绿

### M10 ETF 代码归一化（akshare-code-normalization 2026-06-29）

- [x] `app/data_sources/codes.py` 新增 `normalize_etf_code` / `same_etf`
- [x] `AkShareSource.all_etf_entries` 归一 + 非法 code 静默丢弃
- [x] `filter_etfs` 合并两池时按 canonical form 去重
- [x] `load_display_names` 双查（原 code + canonical form）
- [x] 动态池 sync upsert key 迁移到 canonical form
- [x] pytest 159 passed（116 + 43 新增）

### M11 用户旅程与导航重整（user-journey-reorg 2026-06-29）

- [x] 顶部 4 项 + 侧边栏 7+1（`AppShell` + `Sidebar`）
- [x] 首页 Dashboard 4 卡片（资产概览 / 今日需要做的 / 系统状态 / 当前持仓 Top 5）
- [x] `/signals` 改版（周度操作清单 + 复制 + 进阶表 + 原始输出折叠）
- [x] `/dynamic-pool` 独立成页（从原 `/datasource` 抽出）
- [x] 过期动态池 amber 横幅 + 立即同步
- [x] `@media print` 友好
- [x] 后端 `PortfolioResponse` 新增 `available_cash` / `net_value`；`ScreeningTodayResponse.details`
- [x] vitest + RTL + jsdom 测试基础设施
- [x] 165 backend / 29 frontend passed

### M11.1 Dashboard 化整为零（dashboard-flatten 2026-06-29）

- [x] 移除 `/signals` `/portfolio` `/screening` 路由
- [x] 顶部 nav 从 4 项减为 2 项（仪表盘 + 设置）
- [x] 删除 `pages/Portfolio.tsx` 与 `pages/Signals.tsx`
- [x] `Dashboard.tsx` 内联 7 列持仓表 + 完整周度操作清单
- [x] 测试迁移（`Dashboard.holdings.test.tsx` / `Dashboard.signals.test.tsx` / 删除 `screening-redirect.test.tsx`）
- [x] frontend 30 passed / backend 165 passed（沿用）

### M12 ETF 历史数据同步可观测（etf-historical-sync 2026-06-29）

- [x] `sync_historical_for_pool(codes)` 替代 `sync_today()`；每行新增 `status` / `error`
- [x] `_read_latest_bar(code)` 抽象层（fixture 走文件，akshare 注入点预留）
- [x] `GET/POST /api/sync/historical/{status,trigger}`（pool union 去重 + name 解析）
- [x] `lifespan` 启动同步容错化（try/except + `if codes:` 守卫）
- [x] 前端 `useSyncStatus` / `useTriggerSync` hooks
- [x] `/sync` 页面（4 列表格 + 立即同步按钮 + 4 状态徽章 + 空池子占位）
- [x] `Sidebar` TOOL_ENTRIES 增补"数据同步"项
- [x] 172 backend / 33 frontend passed

## 当前迭代

所有 M0–M12 里程碑已完成并归档（`bootstrap-fullstack-20260628/` + `real-data-source-20260629/` + `akshare-code-normalization-20260629/` + `dashboard-flatten-20260629/` + `etf-historical-sync-20260629/`）。M11 走的是 docs/superpowers 流程而非 openspec（无归档目录，仅在 `spec/devlog.md` 有记录）。下一迭代可在新变更中启动，例如：

- 动态池定时同步（cron 或 APScheduler）
- akshare 代码归一化（6 位裸码 ↔ `XXXXXX.XSHG/XSHE`）以合并 static/dynamic pool
- akshare `fund_etf_spot_em` 真实调用集成测试（mock 当前绕过网络）