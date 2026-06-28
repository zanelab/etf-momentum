# 架构设计

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│  React 前端 (frontend/)                              │
│  - 配置面板（池子/词典/参数）                          │
│  - 回测可视化                                       │
│  - 当日信号 & 持仓展示                                │
└────────────────────┬────────────────────────────────┘
                     │ HTTP/JSON
┌────────────────────▼────────────────────────────────┐
│  Python 后端 (backend/)                              │
│  - FastAPI 路由层                                    │
│  - Service 层（筛选/回测/信号）                       │
│  - Data Source 抽象层（行情、配置持久化）               │
│  - 收盘同步定时任务                                   │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    SQLite DB    行情数据源    文件/对象存储
    (配置/历史)
```

## 技术选型

| 层 | 技术 | 理由 |
|---|------|------|
| 前端框架 | React + Vite | 用户指定 |
| 前端 UI | Ant Design 或 shadcn/ui | 适合配置型后台 |
| 前端状态 | TanStack Query + Zustand | Query 管远程，Zustand 管本地 UI 状态 |
| 后端框架 | FastAPI | 异步友好、Pydantic 校验、自动 OpenAPI |
| 后端 ORM | SQLModel（基于 SQLAlchemy + Pydantic） | 与 FastAPI 风格一致 |
| 数据库 | SQLite（dev）→ Postgres（prod） | 起步轻量、迁移成本低 |
| 数值计算 | pandas + numpy | 与原策略代码一致 |
| 测试 | pytest + httpx（异步测试） | TDD 强制 |

## 模块划分（backend）

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── api/               # 路由层
│   │   ├── configs.py     # 池子/词典/参数 CRUD
│   │   ├── screening.py   # ETF 筛选 / 当日信号
│   │   ├── backtest.py    # 回测
│   │   ├── market.py      # 历史数据
│   │   └── portfolio.py   # 持仓
│   ├── services/          # 业务逻辑
│   │   ├── screening.py   # filter_etfs() 核心（从 main.py 迁移）
│   │   ├── backtest.py    # 回测引擎
│   │   └── signals.py     # 调仓建议生成
│   ├── data_sources/      # 数据源抽象
│   │   ├── base.py        # MarketDataSource 接口
│   │   └── mock.py        # mock 实现
│   ├── models/            # SQLModel ORM
│   ├── schemas/           # Pydantic 请求/响应模型
│   └── sync/              # 收盘同步任务
└── tests/
```

## 模块划分（frontend）

```
frontend/
├── src/
│   ├── pages/
│   │   ├── PoolConfig.tsx       # 静态池配置
│   │   ├── ThemeConfig.tsx      # 主题词典配置
│   │   ├── StrategyConfig.tsx   # 策略参数配置
│   │   ├── Backtest.tsx         # 回测页
│   │   ├── Signals.tsx          # 当日买卖信号
│   │   └── Portfolio.tsx        # 持仓展示
│   ├── api/                     # 后端 API 客户端
│   ├── components/              # 复用组件
│   └── store/                   # Zustand stores
└── ...
```

## 数据流

### 当日信号流

1. 前端调用 `GET /api/signals/today`
2. 后端从 DB 读取池子/词典/参数配置
3. 后端调用 `screening.filter_etfs()` → 返回目标列表
4. 后端结合当前持仓生成调仓建议（卖出列表、买入列表、数量）
5. 返回 JSON 给前端展示

### 回测流

1. 前端调用 `POST /api/backtest`（区间、初始资金、配置快照）
2. 后端在区间内按日重放筛选 + 调仓逻辑
3. 返回净值序列、交易明细、统计指标

## 关键设计决策

- **配置存储**：前端写入的池子/词典/参数持久化到 DB，回测时可指定配置快照（避免回测结果随当前配置漂移）
- **数据源抽象**：所有行情访问通过 `MarketDataSource` 接口，便于从 mock 切换到 akshare/tushare/聚宽
- **筛选逻辑纯净化**：迁移 `main.py` 的 `filter_etfs()` 时去除对 JoinQuant 全局函数（`history`、`get_current_data` 等）的依赖，改为显式参数注入，便于单测

## 实施调整（M0–M8 bootstrap-fullstack，2026-06-28）

- **持仓聚合**：原设计 `portfolio.py` 路由改为在 `screening.py` 路由内一并暴露 `GET /api/portfolio` 与 `GET /api/signals/today`（聚合 `portfolio_mock` + `signals.generate_signals`，简化模块边界）
- **同步落盘而非入库**：原设计同步写 DB，改为写 `data/daily_sync/YYYY-MM-DD.json`（轻量；生产可平迁到 DB）
- **回测任务异步化**：通过 FastAPI `BackgroundTasks` + JSON 文件持久化（`data/backtest_tasks/{task_id}.json`），前端按 2s 轮询 `/api/backtest/{task_id}` 获取状态
- **JoinQuant 兼容验证**：保留 `main.py` 不动，新增 `tests/_jq_shim.py` 装载原文件并 stub 所有 JQ API，用 3 个对照测试（default / industry-diverse / ma-filter-off）验证迁移后 `filter_etfs` 与原行为一致
- **前端 UI**：实际采用 Tailwind + 自写小组件替代 shadcn（避免额外工具链），仍满足配置型后台形态