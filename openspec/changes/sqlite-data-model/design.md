# Design: SQLite 数据模型

> 2026-06-26 brainstorming 阶段产出。基于用户确认的关键决策与默认推断。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| ORM 框架 | SQLAlchemy 2.0（同步） | 与 FastAPI sync 端点天然搭配；代码简单、调试方便 |
| 数据库 | SQLite（文件 + 内存测试） | 单用户场景、零运维成本，足够 MVP；后续可平滑迁移至 PostgreSQL |
| 迁移工具 | Alembic | SQLAlchemy 生态标准，支持自动生成迁移 |
| 价格字段 | `Numeric(precision=10, scale=4)` | 金融数据，避免浮点累积误差 |
| 整数字段（成交量） | `BigInteger` | 防止 A 股高成交量 ETF 溢出 |
| 字符串 code | `String(10)` | A 股 ETF 代码如 `510300`、`159915` 不超过 6 位 |
| 时间字段 | `Date` / `DateTime(timezone=True)` | 日线数据用 Date；运行记录用带时区的 DateTime |
| 索引策略 | 在常见查询路径上显式建索引 | 避免后期回填索引 |
| Session 生命周期 | FastAPI Depends per-request | 自动 commit/rollback，避免泄漏 |
| JSON 字段 | SQLAlchemy `JSON` | BacktestRun.metrics 等结构化字段直接存 JSON |

## Schema 设计

### ETF
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| code | String(10) UNIQUE NOT NULL | ETF 代码（`510300`） |
| name | String(64) NOT NULL | ETF 名称（`沪深300ETF`） |
| market | String(2) NOT NULL | 交易所（`SH`/`SZ`） |
| category | String(32) | 分类（`指数`/`行业`/`主题`，可选） |
| created_at | DateTime(timezone=True) | 录入时间 |

**索引**：`code` UNIQUE 隐式索引；`category` 普通索引（按分类筛选）。

### DailyPrice
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| code | String(10) NOT NULL | ETF code（无 FK，留作数据同步灵活性） |
| date | Date NOT NULL | 交易日期 |
| open | Numeric(10,4) NOT NULL | 开盘价 |
| high | Numeric(10,4) NOT NULL | 最高价 |
| low | Numeric(10,4) NOT NULL | 最低价 |
| close | Numeric(10,4) NOT NULL | 收盘价 |
| volume | BigInteger NOT NULL | 成交量（股） |

**索引**：`UNIQUE(code, date)` 复合唯一索引（防重复写入）；`code` 普通索引（按 ETF 查询历史）。

> 决策：不设 FK，因为 akshare 数据同步是「upsert」语义，独立运行；后续如需外键可在迁移中追加。

### BacktestRun
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| name | String(128) | 用户命名（可选） |
| etf_pool | JSON NOT NULL | ETF code 列表（`["510300","510500"]`） |
| momentum_window | Integer NOT NULL | 动量窗口（月） |
| rebalance_freq | String(16) NOT NULL | 调仓频率（`monthly`/`quarterly`） |
| start_date | Date NOT NULL | 回测开始 |
| end_date | Date NOT NULL | 回测结束 |
| metrics | JSON | 业绩指标（年化收益、夏普、最大回撤等） |
| created_at | DateTime(timezone=True) | 创建时间 |

**索引**：`created_at` 普通索引（按时间倒序查询运行历史）。

### SignalSnapshot
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| date | Date NOT NULL | 信号日期 |
| etf_code | String(10) NOT NULL | ETF code |
| momentum_score | Numeric(10,6) NOT NULL | 动量得分 |
| rank | Integer NOT NULL | 当日排名 |
| action | String(8) NOT NULL | `buy`/`sell`/`hold` |
| created_at | DateTime(timezone=True) | 写入时间 |

**索引**：`UNIQUE(date, etf_code)` 复合唯一；`date` 普通索引（按日期查询当日所有信号）。

## 应用架构

```
backend/app/
├── core/
│   └── config.py           # DATABASE_URL 配置（默认 sqlite:///./etf_momentum.db）
├── db/
│   ├── __init__.py
│   ├── base.py             # SQLAlchemy DeclarativeBase
│   ├── session.py          # engine + SessionLocal + get_db Depends
│   └── init_db.py          # create_all（开发 fallback，可选）
├── models/
│   ├── __init__.py
│   ├── etf.py
│   ├── daily_price.py
│   ├── backtest_run.py
│   └── signal_snapshot.py
└── repositories/
    ├── __init__.py
    └── etf_repository.py   # 至少一个 Repository，演示查询模式

backend/
├── alembic.ini
└── alembic/
    ├── env.py              # 读取 metadata + DATABASE_URL
    ├── script.py.mako
    └── versions/
        └── 0001_initial.py # 初始迁移（4 表 + 索引）
```

## 测试策略

- **测试数据库**：每个测试 session 使用 `sqlite:///:memory:`，通过 fixture 提供 Session
- **覆盖范围**：每个模型至少 1 个 CRUD 测试 + 1 个索引 / 约束验证
- **框架**：pytest（已配置）

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| Numeric 精度不够 | 预留 scale=4 满足当前 ETF 价格范围；后续如需要可迁移到 scale=6 |
| SQLite 并发写锁 | 单用户 MVP 不影响；未来切 PostgreSQL 时调整 |
| Decimal 与 JSON 序列化 | 业务层显式 `str(decimal)` 或 `float()`；Repository 返回 dict 时处理 |
| 测试间数据库污染 | 每个测试用独立 engine + StaticPool，session-scoped fixture |

## 不在本 change 范围
- 任何 API endpoint（`/api/v1/etfs` 等）属于后续 change
- akshare 数据同步脚本
- 回测引擎
- 用户认证
