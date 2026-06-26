# Spec: SQLite 数据模型

## ADDED Requirements

### Requirement: 四个核心实体建表
数据库必须包含 ETF、DailyPrice、BacktestRun、SignalSnapshot 四张表，结构遵循 `design.md`。

#### Scenario: 初始迁移后四表存在
- Given 已运行 `alembic upgrade head`
- When 检查 SQLite 数据库
- Then 存在 `etfs`、`daily_prices`、`backtest_runs`、`signal_snapshots` 四张表

### Requirement: ETF 实体结构
ETF 表存储 ETF 基础信息。

#### Scenario: 创建 ETF 记录
- Given 数据库连接可用
- When 插入 `{code: "510300", name: "沪深300ETF", market: "SH"}`
- Then 记录成功且自增 id 返回

#### Scenario: ETF.code 唯一
- Given 已存在 `code = "510300"` 的 ETF
- When 尝试插入另一条 `code = "510300"`
- Then 抛出 IntegrityError

### Requirement: DailyPrice 实体结构
DailyPrice 表存储日线行情。

#### Scenario: 写入单日行情
- Given 数据库连接可用
- When 插入 `{code: "510300", date: "2026-01-15", open: 4.123, high: 4.156, low: 4.100, close: 4.135, volume: 12345678}`
- Then 记录成功

#### Scenario: 同一 (code, date) 唯一
- Given 已存在 `{code: "510300", date: "2026-01-15"}` 行情
- When 再次插入相同 (code, date)
- Then 抛出 IntegrityError（防重复）

#### Scenario: 按 code 查询历史
- Given 存在多条 `code = "510300"` 的行情
- When 查询 `WHERE code = "510300" ORDER BY date`
- Then 按日期升序返回

### Requirement: BacktestRun 实体结构
BacktestRun 表存储回测参数与业绩指标。

#### Scenario: 存储完整回测记录
- Given 数据库连接可用
- When 插入包含 etf_pool、momentum_window、metrics JSON 的回测记录
- Then JSON 字段正确存储与读取

### Requirement: SignalSnapshot 实体结构
SignalSnapshot 表存储每日动量信号。

#### Scenario: 写入信号
- Given 数据库连接可用
- When 插入 `{date, etf_code, momentum_score, rank, action: "buy"}`
- Then 记录成功

#### Scenario: 按日期查询当日信号
- Given 存在多条 `date = "2026-01-15"` 的信号
- When 查询该日所有信号按 rank 排序
- Then 按 rank 升序返回

### Requirement: 数据库 Session 通过 FastAPI Depends 注入
后续 API 端点可通过 Depends 获取 Session，生命周期 per-request。

#### Scenario: get_db 返回 Session
- Given 已配置 engine 与 SessionLocal
- When FastAPI 端点声明 `db: Session = Depends(get_db)`
- Then 端点收到 Session 实例，函数返回后自动关闭

#### Scenario: 异常时回滚
- Given 端点内 Session 抛出异常
- When 请求结束时
- Then Session 自动 rollback，连接归还池

### Requirement: 配置支持 DATABASE_URL 环境变量
数据库 URL 通过环境变量 `DATABASE_URL` 配置，默认 `sqlite:///./etf_momentum.db`。

#### Scenario: 默认值生效
- Given 未设置 `DATABASE_URL`
- When 加载配置
- Then `DATABASE_URL = "sqlite:///./etf_momentum.db"`

#### Scenario: 环境变量覆盖
- Given `DATABASE_URL=postgresql://...`
- When 加载配置
- Then 使用 PostgreSQL URL

### Requirement: Alembic 迁移可应用
alembic 必须可生成迁移并升级数据库。

#### Scenario: alembic upgrade head 应用初始迁移
- Given 已运行 `alembic init` 并配置 env.py
- When 执行 `alembic upgrade head`
- Then 数据库包含四张表

#### Scenario: 迁移文件包含索引
- Given `alembic revision --autogenerate -m "initial"` 生成迁移
- When 检查迁移文件
- Then 包含 DailyPrice 与 SignalSnapshot 的复合唯一索引创建

### Requirement: 价格字段使用 Decimal 精度
所有价格字段使用 SQLAlchemy Numeric（映射 SQLite NUMERIC）存储，scale=4。

#### Scenario: 写入精确价格
- Given 字段定义为 `Numeric(10, 4)`
- When 插入 `Decimal("4.1234")`
- Then 数据库存储精确值，无浮点误差

### Requirement: 测试覆盖每个模型 CRUD
pytest 套件中每个模型至少有一个 CRUD 测试。

#### Scenario: 测试通过
- Given pytest 在 backend 目录运行
- When 收集所有 `tests/test_*.py`
- Then 全部通过；退出码 0
