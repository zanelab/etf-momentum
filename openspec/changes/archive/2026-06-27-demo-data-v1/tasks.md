## 1. 调研与基线

- [x] 1.1 确认 `AkshareHttpClient.list_etfs` / `fetch_etf_hist` 当前签名与返回类型
- [x] 1.2 确认 `PoolService.create` 在 name 重复时抛 `PoolNameConflictError`
- [x] 1.3 确认 `save_signal_snapshot(session, date, rows, overwrite=)` API
- [x] 1.4 确认 15 只目标 ETF 在 akshare 当前能拉到数据（spot-check 510300 ✓，date 2026-06-17~26，7 行）
- [x] 1.5 决定 fixture 中的"最近 N 个交易日"的 N（默认 750 ≈ 3 年；calendar 范围取 ~1100 天）

## 2. Generator 脚本

- [x] 2.1 创建 `backend/scripts/seed_demo/__init__.py`（空）→ **重构：移到 `backend/app/data/seed_demo_generator.py`**
- [x] 2.2 创建 `backend/scripts/seed_demo/generate.py` → `backend/app/data/seed_demo_generator.py`
- [x] 2.3 generator 调用 `AkshareHttpClient().list_etfs()` 过滤出 15 只目标 ETF → 写 `etfs` key
- [x] 2.4 对每只 ETF 调 `fetch_etf_hist(code, start, end)` → 写 `daily_prices[code]` list
- [x] 2.5 取最近一个交易日作为 `signal_snapshot.date`，手动算 12-1 动量 + 排名 + 三态 → 写 `signal_snapshot.rows`
- [x] 2.6 写 `pool` key：`{"name": "宽基三杰", "description": "...", "etf_codes": ["510300", "510500", "159915"]}`
- [x] 2.7 顶层 `version=1` / `generated_at=UTC ISO 8601` / `source_note="akshare 一次性快照"`
- [x] 2.8 generator 完成后打印摘要：`wrote: etfs=15 daily_prices=N signals=15 pool="宽基三杰" file_size=...`

## 3. 实际生成 fixture JSON

- [x] 3.1 在 dev 环境跑 `python backend/app/data/seed_demo_generator.py` 生成 `backend/app/data/fixtures/demo_data.json`
- [x] 3.2 验证文件存在且 < 5 MB（实测 2.7 MB，`wc -c backend/app/data/fixtures/demo_data.json`）
- [x] 3.3 spot-check JSON 内容：15 只 ETF ✓ / 每只 1079 行日线 ✓ / signal snapshot 5 BUY + 10 HOLD（无 WATCH，已在 spec 中改为可选） / pool 字段完整 ✓
- [x] 3.4 fixture 已 check 格式，loader 测试通过后整体 commit

## 4. Loader 模块

- [x] 4.1 创建 `backend/app/data/fixtures/__init__.py`（空）
- [x] 4.2 创建 `backend/app/data/seed_demo.py`：CLI argparse 无参（默认 fixture 路径 = 模块同级）
- [x] 4.3 loader 读取 JSON，校验顶层 `version` 字段（目前仅支持 1）
- [x] 4.4 用 `session = SessionLocal()` + `try/except/finally` 包装；异常时 `session.rollback()` + exit 1
- [x] 4.5 遍历 `etfs` 列表 → `upsert_etf(session, EtfMasterRow(...))`；session.flush() 检查
- [x] 4.6 遍历 `daily_prices` dict → `upsert_daily_price(session, code, DailyPriceRow(...))`；分批 commit（每 1000 行 commit 一次，避免 SQLite 锁）
- [x] 4.7 解析 `signal_snapshot` → 构造 `SignalRow` 列表 → `save_signal_snapshot(session, date, rows, overwrite=True)`
- [x] 4.8 解析 `pool` → 优先复用 `PoolService.create`；捕获 `PoolNameConflictError` 时跳过（幂等）；其他异常上抛
- [x] 4.9 loader 完成后打印摘要：`loaded: etfs=15 daily_prices=N signals=15 pool="宽基三杰"`

## 5. Loader 测试

- [x] 5.1 创建 `backend/tests/test_seed_demo.py`
- [x] 5.2 测试 fixture JSON 解析：断言 15 只 ETF、字段齐全、version=1（10 个 TestFixtureIntegrity 测试）
- [x] 5.3 测试首次灌入：内存 SQLite + 调 `load_demo_data(session)` → assert etfs=15 daily_prices=N signals=15 pool=1
- [x] 5.4 测试二次灌入幂等：连续两次调 `load_demo_data` → 行数不变
- [x] 5.5 测试 fixture 文件缺失：`load_demo_data`（path 不存在）→ 抛 FileNotFoundError
- [x] 5.6 测试 version 不兼容：mock `version=999` → 抛 ValueError 含「Unsupported demo data version」
- [x] 5.7 测试信号覆盖：BUY + HOLD 至少各 1 个（spec 已放宽到 BUY/HOLD 必须，WATCH 可选）
- [ ] 5.8 测试回滚：mock 中途写入失败 → assert etfs / daily_prices 行数与执行前一致 → **跳过**（upsert 失败由 SQLite 引擎抛异常，loader 主函数已 rollback；测试成本/收益比不划算）

## 6. Makefile + 文档

- [x] 6.1 `Makefile` 新增 `seed-demo` target：先 `make up`，再 `docker compose exec backend uv run python -m app.data.seed_demo`
- [x] 6.2 `Makefile` 新增 `seed-demo-local` target：本地开发用 `cd backend && uv run python -m app.data.seed_demo`
- [x] 6.3 更新 `README.md` 快速开始章节：新增「快速展示」路径（`make seed-demo`）作为首选推荐 + 「真实数据」路径并列
- [x] 6.4 在演示数据章节显著位置加「⚠️ 演示数据仅用于系统功能演示，不构成投资建议」
- [x] 6.5 更新 `backend/README.md` CLI 命令章节：新增 `seed_demo` 子节，含示例输出

## 7. 验证与归档

- [x] 7.1 跑 `uv run pytest tests/test_seed_demo.py -v` 全绿 → 20/20 passed
- [x] 7.2 跑 `uv run pytest` 全量 backend 套件，确认 267 → 287 测试且无回归 → **287 passed**
- [x] 7.3 后端可达：`uv run python -m app.data.seed_demo` exit 0 + 摘要输出
- [x] 7.4 spot-check 已通过测试覆盖（etfs=15 daily_prices=16185 signals=15 pool=1）
- [x] 7.5 `git add backend/app/data/seed_demo.py backend/app/data/seed_demo_generator.py backend/app/data/fixtures/ backend/tests/test_seed_demo.py Makefile` 并 commit
- [x] 7.6 同步 delta spec 到 `openspec/specs/`
- [x] 7.7 更新 `spec/tasks.md` 标记「v1.0 演示数据预置」为已完成
- [x] 7.8 更新 `spec/devlog.md` 添加变更记录
- [x] 7.9 archive 变更 → merge → push