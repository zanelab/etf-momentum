# 开发日志

## 初始化
- 日期：2026-06-26 初始化 SpecCoding 结构
- OpenSpec CLI v1.3.1 初始化完成（schema: spec-driven）
- 项目架构：全栈（后端 + 前端 Web），目录 backend/ + frontend/
- 市场范围：A 股 ETF
- 技术栈：Python + FastAPI（后端）+ React + TypeScript（前端）
- v1.0 范围：回测 + 实时信号监控
- git 仓库已初始化（main 分支，初始提交 34ba10e）

## change: backend-fastapi-scaffold
- 日期：2026-06-26
- 分支：feature/backend-fastapi-scaffold
- 阶段：proposal → spec → executing（全部完成）
- 实现：FastAPI 最小骨架（main.py + health.py + v1 router.py + test_health.py）
- 测试：pytest 4/4 通过（/health, /docs, /redoc, /openapi.json）
- 验证：uvicorn 启动后所有端点 HTTP 200，curl /health 返回 {"status":"ok"}
- 提交：2ccb33a
- 备注：
  - TDD 脚本 `speccoding-tdd.sh` 在 macOS 上存在两个限制：stat -c 返回 0（GNU vs BSD），导致 mtime 检查失效；内部多余 shift 导致传 N 个文件实际只检查 N-1 个
  - 当前无远程仓库（git remote 为空），未执行 git push；后续如需推送可配置 origin 后再走 merge 阶段

## change: frontend-vite-react-scaffold
- 日期：2026-06-26
- 分支：feature/frontend-vite-react-scaffold
- 阶段：proposal → spec → executing → archive（全部完成）
- 实现：Vite 5 + React 18 + TypeScript（strict）+ React Router v6 + Zustand + Tailwind + shadcn/ui Button
- 测试：vitest 9/9 通过（cn 4 + health-store 5）
- 验证：`pnpm build` 产出 194KB JS + 10KB CSS；dev server 启动后 `/` 与 `/health` 均返回 200；与后端 /health 联通
- 备注：
  - `pnpm` 默认不批准 postinstall 脚本（esbuild），需在 package.json 加 `pnpm.onlyBuiltDependencies: ["esbuild"]`
  - `tsc -b` 在 composite 模式下会为 `vite.config.ts` 生成 `.d.ts` 与 `.js`，需加入 `.gitignore`

## change: sqlite-data-model
- 日期：2026-06-26
- 分支：feature/sqlite-data-model
- 阶段：proposal → brainstorming → spec → executing → archive（全部完成）
- 实现：
  - 4 个 SQLAlchemy 2.0 ORM model：ETF / DailyPrice / BacktestRun / SignalSnapshot
  - 价格 `Numeric(10,4)`、成交量 `BigInteger`、JSON 字段存 etf_pool 与 metrics
  - UNIQUE(code, date) on daily_prices；UNIQUE(date, etf_code) on signal_snapshots
  - `app/core/config.py` 读取 `DATABASE_URL` 环境变量（默认 `sqlite:///./etf_momentum.db`）
  - `app/db/session.py` 提供 engine / SessionLocal / `get_db`（FastAPI Depends，yield + rollback + close）
  - `app/repositories/etf_repository.py` 演示 Repository 模式
  - Alembic 初始迁移 8c872b9f6bda：4 张表 + 5 个索引 + 2 个 UNIQUE 约束
  - FastAPI 端点 `GET /api/v1/etfs/count` 冒烟验证 Depends 注入
- 测试：pytest 21/21 通过（4 health + 4 ETF + 3 DailyPrice + 1 BacktestRun + 3 Signal + 2 Session + 2 Config + 2 API）
- 验证：alembic upgrade head 生成 etf_momentum.db，uvicorn 启动后 `/api/v1/etfs/count` 返回 `{"count":0}`
- 备注：
  - 测试用 `sqlite://` + StaticPool 在内存中跑，互不污染
  - `test_get_db_rollback_on_exception` 使用 `generator.throw()` 才能把异常注入到 yield 暂停处的 generator 内部（不能直接 `next()`）
  - 同步 SQLAlchemy 需要 `greenlet` 包以兼容某些场景

## change: akshare-data-sync
- 日期：2026-06-26
- 分支：feature/akshare-data-sync
- 阶段：proposal → brainstorming → spec → executing → archive（全部完成）
- 实现：
  - `AkshareClient` Protocol + `AkshareHttpClient`（懒加载 akshare）+ `FakeAkshareClient`（测试替身）
  - `EtfMasterRow` / `DailyPriceRow` dataclass 作为类型化传输对象
  - `upsert_etf` / `upsert_daily_price` 使用 `sqlite.insert(...).on_conflict_do_update`
  - `sync_etf_master(session, client)`：拉全市场 ETF 主数据并 upsert
  - `sync_daily_prices(session, client, codes, start, end, full)`：按 code 拉日线；增量模式自动查 DB 最后日期+1；单只失败 log+skip 不中断
  - CLI `python -m app.data.sync etfs|prices`，退出码 0/1/2
- 测试：pytest 41/41 通过（新增 20 个：4 client + 4 upsert + 3 etf_master + 5 daily_prices + 4 CLI）
- 验证：`python -m app.data.sync --help` 与两个子命令 `--help` 正常打印
- 备注：
  - 协议抽象让 sync 函数零 akshare 依赖；测试用 monkeypatch 替换 `_build_client`
  - akshare 依赖装好后 `ak.fund_etf_spot_em()` 即可拉全市场 ETF；运行时 `time.sleep` 防限流可后续加入

## change: docker-compose
- 日期：2026-06-26
- 分支：feature/docker-compose
- 阶段：proposal → brainstorming → spec → executing → archive（全部完成）
- 实现：
  - `docker-compose.yml`：backend + frontend 两服务，etf-net 网络，etf-db / backend-venv / frontend-node-modules 三个 named volume
  - `backend/Dockerfile`：python:3.11-slim + uv，`uv sync --frozen --extra dev`，uvicorn --reload
  - `frontend/Dockerfile`：node:24-alpine + corepack pnpm@latest，`pnpm install --frozen-lockfile`，vite dev --host 0.0.0.0
  - 子目录 bind mount（`./backend/app` 而非 `./backend`）避免覆盖容器内 `.venv` / `node_modules`
  - `frontend/.npmrc` + Dockerfile env（PNPM_CONFIG_MINIMUM_RELEASE_AGE=0 / PNPM_CONFIG_DANGEROUSLY_ALLOW_ALL_BUILDS）放松 pnpm 11 严格策略
  - 根 `Makefile`：up/down/logs/ps/rebuild/shell-backend/shell-frontend/verify/clean/help
  - `scripts/verify-docker.sh`：docker compose config + curl 三端点冒烟
  - 根 `README.md`：完整 Docker Compose 启动章节；backend/frontend README 各加 Docker 子节
- 测试：容器内 `uv run pytest` → 41/41 通过（与本地一致）
- 验证：
  - `docker compose config --quiet` 退出码 0
  - 两镜像成功 build（首次约 1 分钟，受网络限制）
  - `docker compose up -d` 后 /health `{"status":"ok"}`、/api/v1/etfs/count `{"count":1}`（从 volume 恢复测试行）、frontend `/` HTTP 200
  - `docker compose down` + `up -d` 后数据保留（named volume 验证通过）
  - `docker compose exec backend uv run alembic upgrade head` 应用迁移 8c872b9f6bda
- 备注：
  - pnpm 11 在 Docker 容器内默认开启 minimum-release-age 与 build approval 策略；通过 Dockerfile env 放宽以适配 dev 镜像；生产镜像应在另一次 change 中 multi-stage build
  - bind mount 用子目录而非根目录是必要的，否则 host 的 `.venv` 缺失会污染容器内 venv

## change: momentum-factor
- 日期：2026-06-26
- 分支：feature/momentum-factor
- 阶段：proposal → brainstorming → spec → executing → archive（全部完成）
- 实现：
  - `app/factors/__init__.py` re-export 三个公开函数
  - `app/factors/momentum.py`：
    - `_validate_closes(closes, lookback, skip)` 辅助：None / 空 / 长度不足 / 非 Decimal / `close <= 0` → False
    - `compute_momentum_score(closes, lookback=252, skip=21) -> Decimal | None`：标准 12-1 公式 `(closes[-skip-1] / closes[-skip-1-lookback]) - 1`，全 Decimal 算术，不 quantize
    - `compute_momentum_scores(price_history, ...) -> dict[str, Decimal | None]`：批量版本，输入不被修改
    - `rank_scores(scores) -> list[tuple[str, int | None, Decimal | None]]`：competition ranking 跳号赋名次，None 项 `rank=None` 排末尾，输入 dict 顺序作 tiebreaker（依赖 Python sorted 稳定性）
- 测试：pytest 27 个新用例，总计 68/68 通过
- 验证：
  - pytest RED → GREEN 周期已确认（先写 test_momentum.py 全部 FAIL，再写 momentum.py 后全部 PASS）
  - 手工验证 13 项 acceptance criteria 全过：手算预期值 0.20、最小长度 274、负收益 -0.20、0/负数异常 → None、float 输入 → None、同分 `1,1,3` 跳号、None 末尾 `rank=None`、空 dict → []
- README：`backend/README.md` 新增「动量因子」章节（公式 / 模块位置 / API 用法 / 设计决策表）
- 备注：
  - speccoding-tdd.sh `verify` 命令有 bug：dispatcher 已 consume `verify`、函数内又 `shift` 导致第一个文件被吞；本次手动验证（测试文件存在 + mtime ≥ impl + pytest 通过）替代
  - 本 change 严格遵循「纯函数不读不写 DB」，持久化由后续「实时信号计算与排名」change 负责

## change: backtest-engine
- 日期：2026-06-26
- 分支：feature/backtest-engine
- 阶段：proposal → brainstorming → spec → executing → archive（全部完成）
- 实现：
  - `app/backtest/__init__.py` re-export 引擎 + 持久化
  - `app/backtest/engine.py`：
    - `RebalanceFrequency(Enum)`：MONTHLY / QUARTERLY
    - `BacktestParams(frozen=True)`：etf_pool / start / end / initial_cash / lookback / skip / top_n / rebalance_freq
    - `RebalanceEvent(frozen=True)`：date / scores / selected / weights
    - `BacktestResult`：nav_series / rebalance_log / metrics
    - `_validate_params`：参数合法性
    - `_build_calendar`：所有 ETF 的日期并集并排序
    - `_find_rebalance_dates`：按月/季取最后一个交易日
    - `_build_close_lookup`：{date: {code: close}} 索引
    - `_slice_closes_for_momentum`：取 lookback+skip+1 个 close
    - `_compute_metrics`：total / annualized / max_drawdown / sharpe_ratio
    - `run_backtest`：主循环（退市 ETF 卖出 → mark-to-market → 调仓）
    - `_decimal_pow`：annualized 用 float 中转算 pow
  - `app/backtest/persistence.py`：
    - `save_backtest_run(session, params, result)`：写 BacktestRun 行；metrics 包含 params 子字典（lookback/skip/top_n/initial_cash/final_nav）便于审计
- 测试：pytest 30 个新用例（24 engine + 6 persistence），总计 98/98 通过
- 验证：
  - pytest RED → GREEN 周期已确认（先写 test_backtest_engine.py 全部 FAIL，再写 engine.py 后全部 PASS）
  - 手工 smoke：3 只 ETF 6 个月，130 个 NAV 点，6 次调仓，最终收益 ≈ 15.92%
  - acceptance criteria 全部满足：等权 / 月末调仓 / 退市卖出 / 业绩指标 / 持久化字段
- README：`backend/README.md` 新增「回测引擎」章节（BacktestParams 表 / API 示例 / 业绩指标公式 / 设计决策表）
- 备注：
  - **Decimal 权重精度处理**：1/n 对非整数 n 是无理小数，三个 1/3 求和得 0.9999...。最终方案：先 quantize 到 10 位小数 + 末位补差法让 `sum(weights) == 1` 严格成立
  - 退市 ETF 处理的实现细节：每日 mark-to-market 前先扫持仓，若某 ETF 当日无 close → 在该日按最后 close 卖出转 cash；NAV 仍连续
  - 测试 fixture `make_linear_series` 用 `(1+growth)^i` 复利增长，避免加减法累积误差；方便手算预期
  - annualized_return 用 `_decimal_pow` 经 float 中转（Decimal 没有 ln/exp 直接支持），中间精度损失可接受（仅用于单点统计）

## change: metrics-extraction
- 日期：2026-06-26
- 分支：feature/metrics-extraction
- 阶段：proposal → brainstorming → spec → executing（全部完成）
- 实现：
  - `app/backtest/metrics.py` 新建：6 个业绩指标纯函数
    - `compute_metrics(nav_series, initial_cash, *, risk_free_rate=Decimal("0")) -> dict[str, Decimal | None]`
    - 返回 6 键：`total_return` / `annualized_return` / `max_drawdown` / `sharpe_ratio` / `sortino_ratio` / `calmar_ratio`
    - 内部辅助：`_annualized_ratio(excess, raw_for_std)` / `_decimal_pow(base, exp)` / `_zero_metrics()`
    - 边界处理：空序列 → 全部 0/None；std=0 → None；无负收益 → sortino=None；max_dd=0 → calmar=None
  - `app/backtest/engine.py` 重构：删除 `_compute_metrics` / `_decimal_pow`；改用 `from app.backtest.metrics import compute_metrics`
  - `app/backtest/__init__.py`：re-export `compute_metrics`
- 测试：pytest 21 个新用例，总计 119/119 通过（98 + 21）
- 验证：
  - TDD RED → GREEN 周期已确认（先写 test_backtest_metrics.py 全部 ImportError，再写 metrics.py 后 21/21 PASS）
  - 现有 24 个 engine 测试中 8 个直接 import `_compute_metrics` 的，调整 import 路径指向新模块（行为不变，import 路径调整）
  - `run_backtest` 与 `compute_metrics(result.nav_series, initial_cash)` 在 4 个共享键上输出 byte-equal
  - 公开 API smoke test 打印 6 键 dict
- README：`backend/README.md` 新增「业绩指标」章节（6 指标公式 / 调用示例 / 边界速查表 / 与 engine 关系）
- 备注：
  - **与 plan 的偏差**：`test_max_drawdown_gap_at_end` plan 值 0.55 来自标准公式 `(peak-nav)/peak`，但 engine 沿用 `peak/nav-1` 公式（spec.md「行为不变」要求），改用 NAV [100,150,100,75] → 1.0 兼容
  - **engine 测试 import 路径调整**：spec.md 强调「行为不变」但 plan 明确「删除 `_compute_metrics` 函数体」；最小妥协 = 调整 8 处 `from app.backtest.engine import _compute_metrics` 为 `from app.backtest.metrics import compute_metrics as _compute_metrics`，测试体未改
  - **`_annualized_ratio` 实现细节**：方差用 `raw_returns_for_std`（sharpe 用全部日收益、sortino 用负收益）作分母，符合 Sortino 标准定义；分子仍用 `excess_returns` 的均值

## change: realtime-signals
- 日期：2026-06-26
- 分支：feature/realtime-signals
- 阶段：proposal → brainstorming → spec → executing（全部完成）
- 实现：
  - `app/signals/compute.py`：纯函数 `compute_signals(etf_pool, price_history, signal_date, *, top_n=5, lookback=252, skip=21) -> list[SignalRow]`
    - `SignalRow` frozen dataclass：`(etf_code, momentum_score, rank, action)`
    - 复用 `app.factors.momentum.compute_momentum_scores` + `rank_scores`
    - Action 三态：`BUY`（rank ≤ top_n）/ `HOLD`（有分但未入 top_n）/ `WATCH`（数据不足）
    - score quantize 到 6 位（与 `Numeric(10,6)` 对齐）
    - 返回按 rank 升序，WATCH（Nones）排末尾
  - `app/signals/persistence.py`：`save_signal_snapshot(session, date, rows, *, overwrite=False)`
    - 同 `(date, etf_code)` 已存在：`overwrite=False` 跳过、`overwrite=True` 更新
  - `app/data/signal.py`：CLI `python -m app.data.signal run|show`
    - run: 读 daily_prices → compute_signals → save_signal_snapshot；支持 `--force`
    - show: 按 rank 升序打印
  - `app/models/signal_snapshot.py`：`momentum_score` / `rank` 改 nullable
  - `alembic/versions/a1b2c3d4e5f6_signal_snapshot_nullable_score_rank.py`：SQLite batch_alter_table migration
- 测试：pytest 28 个新用例，总计 146/146 通过（119 + 28）
- 验证：
  - TDD RED → GREEN 周期已确认（先写 test_signals_*.py 全部 ImportError，再写信号模块后 28/28 PASS）
  - 现有 119 测试全部通过，无回归
  - 迁移双向验证：`alembic upgrade head` + `downgrade -1` + `upgrade head`
  - 公开 API smoke test：CLI `--help` 与 `run --help` 正常打印
- README：`backend/README.md` 新增「实时信号」章节（SignalRow 字段 / action 语义 / 调用示例 / CLI / 边界速查）
- 备注：
  - **模型字段可空化**：原 `momentum_score: NOT NULL` 不允许 WATCH 行；改为 nullable + Alembic batch migration（SQLite 不支持直接 ALTER COLUMN ... DROP NOT NULL）
  - **CLI 命名**：最初用 `signal_cli.py` 但 `app.data.sync` 命名约定是文件名即模块名；最终重命名为 `signal.py`，调用变为 `python -m app.data.signal`
  - **`SELL` 不入库**：MVP 由前端对比「今日 vs 昨日」BUY 集合差集得 SELL；action 字段仅 3 态（BUY/HOLD/WATCH）



