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



