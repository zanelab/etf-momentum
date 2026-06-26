# Implementation Plan: SQLite 数据模型

## Prerequisites
- [x] 切换到 feature/sqlite-data-model 分支
- [x] 确认 backend 目录存在，FastAPI 脚手架已就位
- [x] 确认 Python 3.11+ 与 uv 可用

## Dependencies
- [x] `uv add sqlalchemy alembic greenlet`（同步模式需要 greenlet）
- [x] 确认 `backend/pyproject.toml` 已记录新依赖

## Config
- [x] `app/core/config.py` 定义 `DATABASE_URL`（默认 `sqlite:///./etf_momentum.db`），通过 `os.getenv` 读取

## Database Foundation
- [x] `app/db/__init__.py` 空包文件
- [x] `app/db/base.py` 定义 SQLAlchemy 2.0 `DeclarativeBase`，所有 model 继承自此
- [x] `app/db/session.py` 创建 `engine`、`SessionLocal`、`get_db`（FastAPI Depends，yield + rollback + close）
- [x] `backend/.env.example` 增补 `DATABASE_URL=sqlite:///./etf_momentum.db`

## Models
- [x] `app/models/__init__.py` 导出全部 4 个 model 类
- [x] `app/models/etf.py` 定义 `ETF`（id, code UNIQUE, name, market, category, created_at）
- [x] `app/models/daily_price.py` 定义 `DailyPrice`（id, code, date, open/high/low/close Numeric(10,4), volume BigInteger, UNIQUE(code,date) 索引）
- [x] `app/models/backtest_run.py` 定义 `BacktestRun`（id, name, etf_pool JSON, momentum_window, rebalance_freq, start_date, end_date, metrics JSON, created_at）
- [x] `app/models/signal_snapshot.py` 定义 `SignalSnapshot`（id, date, etf_code, momentum_score Numeric(10,6), rank, action, created_at, UNIQUE(date,etf_code) 索引）

## Repositories
- [x] `app/repositories/__init__.py` 空包文件
- [x] `app/repositories/etf_repository.py` 提供 `EtfRepository`（`get_by_code`, `list_all`, `create`）

## Alembic
- [x] `cd backend && alembic init alembic`（生成目录结构与 `alembic.ini`）
- [x] 修改 `alembic.ini`：将 `sqlalchemy.url` 留空，由 env.py 注入
- [x] 修改 `alembic/env.py`：
  - 导入 `app.core.config.DATABASE_URL`
  - 导入 `Base` 与全部 model（确保 metadata 完整）
  - 设置 `target_metadata = Base.metadata`
- [x] 生成首次迁移：`alembic revision --autogenerate -m "initial schema"`
- [x] 检查迁移文件包含：4 张 `op.create_table`、DailyPrice 与 SignalSnapshot 的 UNIQUE 复合约束
- [x] 应用迁移：`alembic upgrade head`，验证 4 张表与索引存在

## FastAPI Integration
- [x] `app/main.py` 在启动日志打印 `DATABASE_URL`（便于排错）
- [x] 添加临时端点 `GET /api/v1/etfs/count`（仅用于冒烟测试，依赖 `Depends(get_db)`）— 后续 change 会替换
- [x] 端点内 `db: Session = Depends(get_db)`，使用 `select(func.count())` 返回整数

## Testing
- [x] `tests/conftest.py` 创建 `engine` + `db_session` fixture（`sqlite://:` + StaticPool）
- [x] `tests/test_etf.py`：插入/查询/唯一约束 + EtfRepository
- [x] `tests/test_daily_price.py`：插入/按 code 查询历史/(code,date) 唯一约束
- [x] `tests/test_backtest_run.py`：插入 + 读取 JSON metrics 字段
- [x] `tests/test_signal_snapshot.py`：插入/按 date 查询按 rank 排序/(date,etf_code) 唯一约束
- [x] `tests/test_session.py`：验证 `get_db` yield session，异常时 rollback
- [x] `tests/test_config.py`：默认值与 env 覆盖
- [x] `tests/test_etfs_api.py`：端到端 /api/v1/etfs/count 验证 Depends 注入

## TDD Verification
- [x] 写完 21 个测试后运行 pytest 全部通过（GREEN）

## Build & Runtime Verification
- [x] `cd backend && pytest` → 21/21 通过，退出码 0
- [x] `cd backend && alembic upgrade head` → 成功，生成 `etf_momentum.db`
- [x] 启动 uvicorn，访问 `GET /api/v1/etfs/count` → 返回 `{"count":0}`
- [x] `cd backend && pytest` → 21/21 通过

## Documentation
- [x] `backend/README.md` 增补「数据库迁移」章节与数据模型表

## Acceptance Check
- [x] 逐条对照 `proposal.md` 的 9 项 Acceptance Criteria，全部满足
- [x] 逐条对照 `spec.md` 的 9 个 Requirement 至少一个 Scenario 通过
