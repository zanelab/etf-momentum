# 项目目录结构说明

## 架构选型

全栈架构：**React 前端 + Python 后端**（2026-06-28 决定）。

将原聚宽（JoinQuant）单文件策略 `main.py` 重构为前后端分离的应用。

### 职责划分

| 层 | 职责 | 技术 |
|---|------|------|
| **前端 (frontend/)** | 配置 UI：静态核心池、主题分类词典、策略参数；展示：回测结果、ETF 历史数据、当日买入/卖出信号、当前持仓、数据同步状态 | React |
| **后端 (backend/)** | 提供 REST API；执行 ETF 筛选逻辑；收盘数据同步；对接行情数据源 | Python |

### 后续重构范围

- 原 `main.py` 的筛选/回测核心逻辑 → 迁移至 `backend/`（去除 JoinQuant API 依赖，封装为可独立调用的服务）
- 新增前端配置面板，替代原 `STRATEGY_CONFIG` 硬编码字典
- 主题词典 `THEME_KEYWORDS`、静态池 `STATIC_ETF_POOL` 等配置项由前端管理并持久化

## 当前结构

```
etf-momentum/
├── main.py                 # 原聚宽策略脚本（保留为参考；filter_etfs 已迁移）
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # FastAPI app + 路由挂载（含 sync_router）
│   │   ├── api/            # 路由层
│   │   │   ├── configs.py      # 池子/词典/参数 CRUD + 动态池 list/sync/patch
│   │   │   ├── screening.py    # 当日筛选 / 持仓 / 信号（支持 ?source=）
│   │   │   ├── backtest.py     # 回测任务（支持 ?source=）
│   │   │   ├── market.py       # ETF 列表 + OHLCV 历史（支持 ?source=）
│   │   │   └── sync.py         # GET/POST /api/sync/historical/{status,trigger}
│   │   ├── services/       # 业务服务
│   │   │   ├── screening.py        # filter_etfs 核心
│   │   │   ├── signals.py           # 买卖信号生成
│   │   │   ├── backtest.py          # 日级回放引擎
│   │   │   ├── backtest_task.py     # JSON 文件任务生命周期
│   │   │   ├── portfolio_mock.py    # 模拟持仓
│   │   │   ├── daily_sync.py        # 收盘同步（_read_bar_for_date + sync_historical_for_pool[codes,from,to] + sync_today 薄包装）
│   │   │   ├── sync_progress.py     # SyncProgressTracker 进程内单例 + ProgressInfo 模型（M14 新增）
│   │   │   └── today.py             # 当日解析 + DB 装载
│   │   ├── data_sources/   # MarketDataSource 抽象 + FixtureCSVSource + AkShareSource + CachedSource
│   │   │   ├── __init__.py          # make_source(name) 工厂
│   │   │   ├── base.py              # 抽象接口
│   │   │   ├── codes.py             # ETF 代码归一化（normalize_etf_code / same_etf）
│   │   │   ├── fixture.py           # CSV mock
│   │   │   ├── akshare_source.py    # akshare 适配（K线 + 全市场列表）
│   │   │   ├── cache.py             # 读穿透缓存装饰器
│   │   │   └── retry.py             # retry_with_backoff 工具
│   │   ├── models/         # SQLModel 表（static_pool / theme_keyword / strategy_param / dynamic_pool_entry / market_bar_cache）
│   │   ├── schemas.py      # Pydantic 请求/响应模型（含 SyncETFStatus / SyncStatusResponse / SyncTriggerResult）
│   │   ├── db.py           # SQLite 初始化 + session_scope
│   │   └── seed.py         # 默认数据填充
│   ├── tests/              # pytest（172 用例）
│   │   │   ├── test_daily_sync.py        # 6 用例（含 sync_historical_for_pool 3 个）
│   │   │   ├── test_sync_api.py          # 4 用例（/api/sync/historical/{status,trigger}）
│   │   │   ├── test_make_source.py       # 4 用例
│   │   │   ├── test_market_bar_cache.py  # 3 用例
│   │   │   ├── test_dynamic_pool_model.py / test_dynamic_pool_api.py
│   │   │   ├── test_retry.py / test_akshare_source.py / test_cached_source.py
│   │   │   └── test_health_stats.py
│   ├── data/
│   │   ├── fixtures/       # 10 只 ETF × 500 天 GBM mock CSV
│   │   ├── backtest_tasks/ # 任务 JSON 文件
│   │   └── daily_sync/     # 收盘摘要 JSON（含 status / error 字段）
│   ├── scripts/generate_fixtures.py
│   └── pyproject.toml
├── frontend/               # React + Vite + TS 前端
│   ├── src/
│   │   ├── api/            # client.ts + hooks.ts（TanStack Query；含 useSyncStatus / useTriggerSync）
│   │   ├── pages/          # 8 个页面：Dashboard + 配置 3 + 数据 2 + 回测 + 动态池 + 下钻子页
│   │   │   ├── Dashboard.tsx               # 4 卡片：资产概览 / 今日需要做的（含周度操作清单）/ 系统状态 / 当前持仓
│   │   │   ├── PoolConfig.tsx / ThemeConfig.tsx / StrategyConfig.tsx
│   │   │   ├── Backtest.tsx
│   │   │   ├── DataSource.tsx              # 数据源 + 缓存统计
│   │   │   ├── DynamicPoolPage.tsx         # 动态池中枢（双同步按钮 + 状态列 + 行点击下钻）
│   │   │   └── EtfDetailPage.tsx           # /dynamic-pool/:code 下钻子页（K 线 + 软兜底）
│   │   ├── components/      # AppShell + Sidebar（顶部 2 项 + 侧边栏 4+2）+ SyncStatusBadge + 进度组件
│   │   │   ├── AppShell.tsx                # 顶部 2 项 + Outlet 容器
│   │   │   ├── Sidebar.tsx                 # 侧边栏 CONFIG_ENTRIES 4 + TOOL_ENTRIES 2（回测、数据源）
│   │   │   ├── SyncStatusBadge.tsx         # 4 状态徽章（ok/failed/missing/never）— 主页与子页共用
│   │   │   ├── DateRangePicker.tsx         # 同步日期范围选择 Modal（M14 新增）
│   │   │   ├── SyncProgressBanner.tsx      # 表格顶部进度横幅（M14 新增）
│   │   │   └── RowProgressBar.tsx          # 表格行内进度条（M14 新增）
│   │   ├── App.tsx         # 路由（/、/pool、/themes、/strategy、/backtest、/datasource、/dynamic-pool、/dynamic-pool/:code）
│   │   └── main.tsx        # 入口
│   └── package.json
├── spec/                   # 项目级 Spec（累积式维护）
│   ├── requirements.md
│   ├── design.md
│   ├── tasks.md            # M0–M15 全部 ✅
│   ├── devlog.md
│   └── structure.md        # 本文档
├── openspec/
│   ├── config.yaml
│   ├── specs/              # 长期规格
│   └── changes/
│       └── archive/
│           ├── bootstrap-fullstack-20260628/
│           ├── real-data-source-20260629/        # M9：真实数据源接入
│           ├── akshare-code-normalization-20260629 # M10：代码归一化
│           ├── dashboard-flatten-20260629         # M11.1：Dashboard 化整为零
│           ├── etf-historical-sync-20260629       # M12：历史同步可观测
│           ├── dynamic-pool-consolidate-20260629  # M13：动态池中枢化（合并 /history /sync + 下钻子页）
│           ├── add-sync-progress-ui-20260629      # M14：同步进度可视化 + 日期范围支持
│           └── drop-dynamic-pool-polling-20260630 # M15：删除 useDynamicPool 5s 轮询
├── scripts/                # speccoding 工具脚本
│   ├── speccoding-state.sh
│   ├── speccoding-gate.sh
│   ├── speccoding-checkpoint.sh
│   └── speccoding-tdd.sh
├── AGENTS.md               # 开发规则
├── README.md               # 启动步骤 + API + 已知限制
└── .speccoding-state.json
```
