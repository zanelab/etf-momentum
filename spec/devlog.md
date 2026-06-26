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


