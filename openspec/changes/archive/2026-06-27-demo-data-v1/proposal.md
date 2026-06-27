## Why

v1.0 最后一项「演示数据预置」尚未完成。当前的首跑体验（参见 `README.md` 快速开始章节）依赖 akshare 实时拉数据：

1. `python -m app.data.sync etfs` — 拉全市场 800+ 只 ETF 主数据（≈30 秒）
2. `python -m app.data.sync prices --codes 510300,510500,159915 --full` — 拉 3 只 ETF 3 年日线（≈1-2 分钟）
3. `python -m app.data.signal run ...` — 算信号（≈10 秒）

问题：
- **离线 / 限频用户跑不动**：akshare 依赖东方财富 HTTP 接口，断网或限频时首跑直接失败
- **首次打开 Dashboard 空**：用户必须等拉完数据才能看动量排名，没有"开箱即用"
- **演示场景不便**：做技术分享时不能保证网络，无法快速展示系统能力
- **CI / 演示录像不可重现**：akshare 返回数据每次可能略有差异

需要在仓库内自带一份"演示数据集" + "一键灌入"命令，让用户在不依赖 akshare 的前提下 5 秒内看到完整 Dashboard 数据。

## What Changes

- **新增 `backend/scripts/seed_demo/generate.py`**（一次性使用）：通过 `AkshareHttpClient` 拉取 15 只代表性 ETF 的 ~750 个交易日（约 3 年）历史行情，dump 成 `backend/app/data/fixtures/demo_data.json`。仅 dev 环境使用，不入 CI 流水线
- **新增 `backend/app/data/fixtures/demo_data.json`**（入仓，约 200-500 KB）：包含 ETF 主数据 + 日线 + 预计算 signal snapshot + 示例 pool
- **新增 `backend/app/data/seed_demo.py`**（CLI）：`python -m app.data.seed_demo`，读取 fixture JSON 并通过现有 `upsert_etf` / `upsert_daily_price` / `save_signal_snapshot` 写入 SQLite。幂等（基于 upsert）
- **新增 `Makefile` target `seed-demo`**：包装上述 CLI
- **新增 `backend/tests/test_seed_demo.py`**：测试 loader 正确性、幂等性、生成数据完整性
- **更新 `README.md`** 快速开始章节：在 sync 路径之外新增 `make seed-demo` 快捷路径；新增"演示数据 vs 真实数据"决策说明
- **更新 `backend/README.md`** CLI 命令章节：新增 `seed_demo` 说明

**数据范围**（15 只 ETF）：
- **10 只宽基**：510300 (沪深300) / 510500 (中证500) / 159915 (创业板) / 588000 (科创50) / 510880 (红利) / 510050 (上证50) / 159901 (深100) / 510330 (华夏300) / 510180 (上证180) / 159905 (深红利)
- **5 只行业**：512760 (半导体) / 512170 (医疗) / 512690 (酒) / 159928 (消费) / 518880 (黄金)
- **时间窗口**：最近 750 个交易日（约 3 年，截至生成日）
- **预计算内容**：1 个 signal snapshot（最近一个交易日）+ 1 个示例 pool（"宽基三杰"：510300/510500/159915）

## Capabilities

### New Capabilities
- `demo-data-loader`: `python -m app.data.seed_demo` 把 `demo_data.json` 灌入 SQLite。约束：幂等 / 失败回滚 / 完成后打印摘要（写入行数 + 末日期 + 信号条数）。
- `demo-data-fixture`: `backend/app/data/fixtures/demo_data.json` 数据契约。约束：包含 15 只 ETF 主数据 + ≥ 700 个交易日 / 每只 + 1 个 signal snapshot + 1 个 pool；schema 版本号；UTF-8 编码。

### Modified Capabilities
无（仅新增 loader + fixture + 测试 + 文档；现有 CLI / API 不变）

## Impact

- **新增文件**：
  - `backend/app/data/seed_demo.py`
  - `backend/app/data/fixtures/demo_data.json`（约 200-500 KB）
  - `backend/scripts/seed_demo/generate.py`
  - `backend/tests/test_seed_demo.py`
- **修改文件**：
  - `Makefile`（新增 `seed-demo` target）
  - `README.md`（快速开始章节新增演示数据快捷路径）
  - `backend/README.md`（CLI 章节新增 `seed_demo`）
- **依赖**：无新增依赖（复用 `AkshareHttpClient` + `upsert_*` + `save_signal_snapshot`）
- **数据库**：fixture 中的 ETF codes / dates 与现有 schema 完全兼容，无 alembic 迁移
- **运行影响**：执行 `python -m app.data.seed_demo` 约 5-10 秒；幂等无副作用
- **API**：现有 18 个端点不动；调用 `/api/v1/etfs/count` 在灌入后返回 15（之前为 0）

## Out of Scope

- 不预置回测运行记录（用户可通过 `POST /api/v1/backtest` 自助跑）
- 不预置实时信号的多日历史（仅 1 个 snapshot；多日历史通过重复 `signal run --date ...` 累积）
- 不提供"恢复出厂"命令（用户可用 `make clean` 重置 volume）
- 不为 demo fixture 写专门的 alembic seed migration（fixture 通过 Python 代码灌入，避免 alembic data migration 的复杂性）