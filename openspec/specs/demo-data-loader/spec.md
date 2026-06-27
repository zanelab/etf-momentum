## ADDED Requirements

### Requirement: 用户可在 ≤ 10 秒内灌入完整演示数据

`make seed-demo` 命令 MUST 把 `backend/app/data/fixtures/demo_data.json` 中的演示数据写入当前 SQLite，并在完成后打印摘要。

#### Scenario: 首次灌入成功
- **WHEN** 用户在全新 DB 上执行 `make seed-demo`
- **THEN** 顺序完成：(1) 读取 fixture JSON (2) upsert 15 只 ETF 主数据 (3) upsert 约 750 天 × 15 只 ≈ 11250 行日线 (4) 写入 1 个 signal snapshot (5) 创建 1 个示例 pool；全过程 ≤ 10 秒；完成后打印 `etfs=15 daily_prices=~11250 signals=15 pool="宽基三杰"`

#### Scenario: 二次执行幂等
- **WHEN** 用户在已有数据的 DB 上再次执行 `make seed-demo`
- **THEN** 命令 exit 0；etf 数不变（15）；日线行数不变；signal snapshot 行数不变；pool 数不变；不报 duplicate key 错

#### Scenario: Make target 等价于 CLI
- **WHEN** 用户执行 `make seed-demo`
- **THEN** 实际执行 `docker compose exec backend uv run python -m app.data.seed_demo`（Docker 环境）或 `cd backend && uv run python -m app.data.seed_demo`（本地开发环境）；两者效果一致

### Requirement: Loader 不依赖运行时网络

`backend/app/data/seed_demo.py` MUST 在完全离线环境下也能完成灌入。

#### Scenario: 离线环境正常执行
- **WHEN** 用户在断网环境执行 `python -m app.data.seed_demo`
- **THEN** 命令不发起任何 HTTP 请求；只读取本地 fixture JSON；upsert 到本地 SQLite；exit 0

#### Scenario: fixture 文件缺失时报错清晰
- **WHEN** 用户执行 loader 但 `demo_data.json` 不存在
- **THEN** 退出码非 0 + 错误信息明确指向缺失文件路径（如 `[Errno 2] No such file or directory: 'demo_data.json'`）

### Requirement: Loader 失败时整批回滚

`seed_demo.py` MUST 在任意阶段失败时回滚已写入的变更，保证 DB 处于干净状态。

#### Scenario: 单只 ETF 日线写入失败
- **WHEN** loader 写到第 8 只 ETF 时抛出异常（如 DB 写入错误）
- **THEN** 整个 session.rollback()；DB 中 etf_pools / signal_snapshots / etfs / daily_prices 表行数与执行前一致；exit code ≠ 0

### Requirement: Generator 脚本不入 CI 流水线

`backend/scripts/seed_demo/generate.py` MUST 仅作为开发者手动工具，不出现在 `pyproject.toml` 的 `scripts` 段、CI workflow、或测试 setup 中。

#### Scenario: Generator 仅手动调用
- **WHEN** 用户 grep `pyproject.toml` 和 `.github/workflows/`
- **THEN** `generate.py` 不被引用；CI 跑 `pytest` 时不会调用 generator

## ADDED Requirements

### Requirement: Fixture 数据契约稳定

`backend/app/data/fixtures/demo_data.json` MUST 遵循明确的 schema 约定，让 loader 与未来潜在的工具（编辑器、检查器）能可靠解析。

#### Scenario: Schema 顶层结构
- **WHEN** 读取 fixture JSON
- **THEN** 顶层 MUST 包含以下 key：`version` (int) / `generated_at` (ISO 8601 字符串) / `source_note` (字符串) / `etfs` (list) / `daily_prices` (dict[str, list]) / `signal_snapshot` (dict) / `pool` (dict)

#### Scenario: version 字段向前兼容
- **WHEN** loader 读取 fixture 但 `version` 字段值不识别
- **THEN** loader 抛出明确错误（如 `Unsupported demo data version: X`）而非静默忽略

#### Scenario: ETF 主数据字段
- **WHEN** 解析 `etfs[i]`
- **THEN** MUST 包含 `code` / `name` / `market` / `category` 4 个字段；与 `app.models.etf.ETF` ORM schema 一致

#### Scenario: 日线数据字段
- **WHEN** 解析 `daily_prices[code][j]`
- **THEN** MUST 包含 `date` (YYYY-MM-DD) / `open` / `high` / `low` / `close` (字符串形式的 Decimal) / `volume` (int) 6 个字段；与 `app.models.daily_price.DailyPrice` ORM schema 一致

#### Scenario: Signal snapshot 字段
- **WHEN** 解析 `signal_snapshot`
- **THEN** MUST 包含 `date` (YYYY-MM-DD) / `rows` (list)；`rows[i]` MUST 包含 `etf_code` / `momentum_score` / `rank` / `action` 4 个字段

#### Scenario: Pool 字段
- **WHEN** 解析 `pool`
- **THEN** MUST 包含 `name` (string) / `description` (string | null) / `etf_codes` (list[str]) 3 个字段

### Requirement: Fixture 数据范围满足 v1.0 演示需求

Fixture MUST 包含足以让 Dashboard / Backtest / Pools 三个页面立即呈现有意义的展示数据的最小集。

#### Scenario: 覆盖 v1.0 演示场景
- **WHEN** 灌入 fixture 后访问以下端点：
  - `GET /api/v1/etfs` → MUST 返回 15 条
  - `GET /api/v1/signals/latest` → MUST 返回 15 行（覆盖 BUY / HOLD 两态至少各 1 个）
  - `GET /api/v1/pools` → MUST 返回 1 个 pool（"宽基三杰"，含 3 个成员）
  - `POST /api/v1/backtest`（body 用 pool id=1，window=60，skip=5，start/end 落在 fixture 时间区间内）→ MUST 返回 200 且 metrics 含 6 个指标

#### Scenario: 时间窗口足够支撑回测
- **WHEN** fixture 中最早日期与最晚日期
- **THEN** 差值 ≥ 250 个交易日（够 60 天 lookback + 5 天 skip + 至少 1 次调仓）

### Requirement: 文档必须明确两条路径的关系

README 的快速开始章节 MUST 同时呈现「真实数据路径」与「演示数据路径」两条互斥但等价的入口。

#### Scenario: 两条路径并列展示
- **WHEN** 用户阅读 `README.md` 快速开始章节
- **THEN** MUST 同时给出：(a) 「快速展示」路径（`make seed-demo`，5-10 秒，仅依赖内置 fixture） (b) 「真实数据」路径（`sync etfs` + `sync prices` + `signal run`，约 2-3 分钟，依赖 akshare）

#### Scenario: 标注非投资建议
- **WHEN** 用户阅读演示数据相关章节
- **THEN** MUST 显著位置标注「⚠️ 演示数据仅用于系统功能演示，不构成投资建议」

## REMOVED Requirements

无（仅新增 fixture + loader + 文档，无规格变更）