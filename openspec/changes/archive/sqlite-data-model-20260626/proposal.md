# Proposal: SQLite 数据模型

## What
为 etf-momentum 系统建立 SQLite 数据访问层，包含 `spec/design.md` 中定义的 4 个核心实体：

- **ETF**：ETF 池主数据（id, code, name, market, category）
- **DailyPrice**：日线行情（code, date, OHLCV）
- **BacktestRun**：回测运行记录（id, 参数 + 业绩指标 JSON, created_at）
- **SignalSnapshot**：实时信号快照（date, etf_code, momentum_score, rank, action）

具体交付：
- SQLAlchemy 2.0 ORM 模型定义
- Alembic 迁移初始化与首次迁移文件
- 数据库 Session 工厂（FastAPI Depends 集成）
- 基础 Repository / 查询工具函数（增删改查 + 常用查询）
- 自动化测试：内存 SQLite 测试数据库 + 至少一个端到端 CRUD 测试
- `README.md` 增补：迁移命令（alembic upgrade head）

## Why
当前业务模块（数据同步、回测、信号计算）都依赖持久化存储。提前建立稳固的数据层可以让：
- 后续 akshare 数据同步 change 直接写入数据库
- 回测引擎可以读取历史价格
- 信号计算可以持久化结果供前端查询

数据模型是后端基础设施的关键一环，影响后续所有业务 change。

## Scope
- [x] backend
- [ ] frontend

## Acceptance Criteria
- [ ] `backend/app/models/` 目录下 4 个 SQLAlchemy 模型（ETF、DailyPrice、BacktestRun、SignalSnapshot）
- [ ] `backend/app/db/` 目录下 Base、Session、engine 配置
- [ ] `alembic` 初始化在 `backend/alembic/`，首次迁移可 `alembic upgrade head` 应用
- [ ] 应用启动时自动创建表（开发环境 fallback）或要求运行迁移
- [ ] Session 通过 FastAPI Depends 注入，便于后续 API 使用
- [ ] 至少一个 Repository（如 `EtfRepository`）提供基础 CRUD + 常用查询（如按 code 查询）
- [ ] 测试：内存 SQLite + pytest，每个模型至少 1 个 CRUD 测试
- [ ] `backend/pyproject.toml` 添加依赖：SQLAlchemy 2.0、alembic、greenlet（同步模式）
- [ ] `backend/README.md` 增补迁移命令说明
- [ ] `backend/.env.example` 或 `app/core/config.py` 提供 `DATABASE_URL` 配置（默认 `sqlite:///./etf_momentum.db`）

## Status
- [x] 提案已确认
