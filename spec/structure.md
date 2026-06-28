# 项目目录结构说明

## 架构选型

全栈架构：**React 前端 + Python 后端**（2026-06-28 决定）。

将原聚宽（JoinQuant）单文件策略 `main.py` 重构为前后端分离的应用。

### 职责划分

| 层 | 职责 | 技术 |
|---|------|------|
| **前端 (frontend/)** | 配置 UI：静态核心池、主题分类词典、策略参数；展示：回测结果、ETF 历史数据、当日买入/卖出信号、当前持仓 | React |
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
│   │   ├── main.py         # FastAPI app + 路由挂载
│   │   ├── api/            # 路由层
│   │   │   ├── configs.py      # 池子/词典/参数 CRUD
│   │   │   ├── screening.py    # 当日筛选 / 持仓 / 信号
│   │   │   ├── backtest.py     # 回测任务
│   │   │   └── market.py       # ETF 列表 + OHLCV 历史
│   │   ├── services/       # 业务服务
│   │   │   ├── screening.py        # filter_etfs 核心
│   │   │   ├── signals.py           # 买卖信号生成
│   │   │   ├── backtest.py          # 日级回放引擎
│   │   │   ├── backtest_task.py     # JSON 文件任务生命周期
│   │   │   ├── portfolio_mock.py    # 模拟持仓
│   │   │   ├── daily_sync.py        # 收盘同步
│   │   │   └── today.py             # 当日解析 + DB 装载
│   │   ├── data_sources/   # MarketDataSource 抽象 + FixtureCSVSource
│   │   ├── models/         # SQLModel 表（static_pool / theme_keyword / strategy_param）
│   │   ├── schemas.py      # Pydantic 请求/响应模型
│   │   ├── db.py           # SQLite 初始化 + session_scope
│   │   └── seed.py         # 默认数据填充
│   ├── tests/              # pytest（74 用例）
│   ├── data/
│   │   ├── fixtures/       # 10 只 ETF × 500 天 GBM mock CSV
│   │   ├── backtest_tasks/ # 任务 JSON 文件
│   │   └── daily_sync/     # 收盘摘要 JSON
│   ├── scripts/generate_fixtures.py
│   └── pyproject.toml
├── frontend/               # React + Vite + TS 前端
│   ├── src/
│   │   ├── api/            # client.ts + hooks.ts（TanStack Query）
│   │   ├── pages/          # 7 个页面 + Landing
│   │   │   ├── PoolConfig.tsx / ThemeConfig.tsx / StrategyConfig.tsx
│   │   │   ├── Signals.tsx / Portfolio.tsx / Screening.tsx
│   │   │   ├── Backtest.tsx / History.tsx
│   │   ├── App.tsx         # 路由
│   │   └── main.tsx        # 入口
│   └── package.json
├── spec/                   # 项目级 Spec（累积式维护）
│   ├── requirements.md
│   ├── design.md
│   ├── tasks.md            # M0–M8 全部 ✅
│   ├── devlog.md
│   └── structure.md        # 本文档
├── openspec/
│   ├── config.yaml
│   ├── specs/              # 长期规格
│   └── changes/
│       └── archive/
│           └── bootstrap-fullstack-20260628/  # 本次变更归档
├── scripts/                # speccoding 工具脚本
│   ├── speccoding-state.sh
│   ├── speccoding-gate.sh
│   ├── speccoding-checkpoint.sh
│   └── speccoding-tdd.sh
├── AGENTS.md               # 开发规则
├── README.md               # 启动步骤 + API + 已知限制
└── .speccoding-state.json
```