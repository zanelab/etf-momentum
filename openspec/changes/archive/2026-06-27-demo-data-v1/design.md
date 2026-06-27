## Context

- v1.0 最后一项「演示数据预置」尚未完成
- 用户画像：个人投资者（首次跑通）+ 策略研究员（理解能力边界）+ 演示场景（断网/限频/CI）
- 当前首跑路径：3 步 CLI（`sync etfs` / `sync prices` / `signal run`），耗时 ≈2 分钟，依赖 akshare HTTP 接口
- akshare 真实数据每条 ETF ≈30-50 KB JSON 序列化（含 750 日线）；15 只 ≈500 KB
- 现有 `upsert_etf` / `upsert_daily_price` / `save_signal_snapshot` 均支持幂等写入
- 现有 `AkshareHttpClient` 已封装 akshare 接口，generator 复用即可

约束：
- 必须幂等（重复执行不报错、不污染）
- 必须不依赖运行时网络（loader 仅读本地 JSON）
- 数据集必须随 akshare 漂移可重新生成（generator 是独立脚本，不入 CI）
- 文件大小控制在 < 5 MB（避免 git clone 体积膨胀；演示数据非 git LFS）
- 单一 JSON schema，不引入 SQL dump / CSV / pickle 等异构格式

## Goals / Non-Goals

**Goals:**
- 用户首次 `make up` 后可立即（≤ 10 秒）看到完整 Dashboard 数据
- 离线 / 限频环境下首跑路径仍可走通
- 演示数据与真实数据并存：`seed-demo` 是 `sync etfs/prices/signal` 的快捷等价物，可随时切换
- 演示数据可重复生成（generator + 手动记录日期即可）

**Non-Goals:**
- 不为每只 ETF 配 10 年数据（仅 3 年足够展示动量 + 调仓 + 回测）
- 不在 fixture 中塞回测运行记录（用户跑一次 demo 回测即可）
- 不维护 fixture 数据的实时更新（明确标注「截至 YYYY-MM-DD 生成」）
- 不为演示数据加 alembic migration（data migration 用 Python 代码灌入即可，避免 alembic 复杂度）
- 不做 fixture 加密 / 压缩（JSON 明文即可，git LFS 也不需要）

## Decisions

### 决策 1：JSON 单一文件 vs 多文件 / SQLite dump

**选择**：单一 `demo_data.json` 文件，包含 5 个顶层 key：
```json
{
  "version": 1,
  "generated_at": "2026-06-27T...",
  "source_note": "akshare 真实一次性快照",
  "etfs": [{...}, ...],
  "daily_prices": {"510300": [{date, open, high, low, close, volume}, ...], ...},
  "signal_snapshot": {"date": "2026-06-26", "rows": [...]},
  "pool": {"name": "宽基三杰", "etf_codes": ["510300", "510500", "159915"]}
}
```

**理由**：
- 单文件 git diff 直观（一次提交全部变更）
- loader 一次 `json.load()` 拿到全部数据，无需拼接
- schema 演进靠顶层 `version` 字段

**取舍**：15 只 × 1079 天 ≈ 16K 行 JSON，单文件 ~2.7 MB（实测）。 ≤ 5 MB 上限可接受；> 5MB 时考虑改 SQLite dump 或减少日线长度。

### 决策 2：generator 脚本不入 CI

**选择**：`backend/scripts/seed_demo/generate.py` 是"开发者手工工具"，仅当需要刷新 fixture 时手动跑。**不**在 CI / pytest 中调用。

**理由**：
- akshare 依赖网络，CI 跑不通
- fixture 已 check-in，CI 只需验证 loader 不需验证 generator
- generator 的"正确性"靠人眼 review 即可（10 只 ETF 输出对得上价格即可）

**取舍**：fixture 漂移（akshare API 改）时没人自动重生成，需要维护者定期手动跑 + commit。

### 决策 3：幂等性靠 upsert 自然获得

**选择**：loader 完全复用现有 `upsert_etf` / `upsert_daily_price` / `save_signal_snapshot`（均基于 SQLite `ON CONFLICT DO UPDATE`）。

**理由**：
- 零额外代码
- 用户多次跑 / 与 akshare 同步混合跑都不会冲突
- 测试只需验"二次执行不报错" + "行数不增长"

**取舍**：`save_signal_snapshot` 的 `overwrite=False` 默认跳过已存在行；loader 需传 `overwrite=True` 才能重写 signal。

### 决策 4：fixture 中不预置回测记录

**选择**：仅预置 ETF + 日线 + 1 个 signal snapshot + 1 个 pool。回测通过 `POST /api/v1/backtest` 由用户触发（或通过 `make backtest-demo` 包装）。

**理由**：
- 回测结果是派生的，可重复生成
- fixture 体积更小
- 用户看到自己跑的回测更有体感

**取舍**：用户首跑 dashboard 时若想看"已有回测"会失望；README 明确标注"回测需自助跑"。

### 决策 5：pool 的持久化用 ORM 还是 fixture 自定义？

**选择**：复用现有 `EtfPool` 模型（如果有的话），否则在 fixture 中只标 `etf_codes`，由 loader 写池。

**理由**：避免重复造 CRUD。

**实施前需验证**：`PoolsPage` + `/api/v1/pools` 后端 ORM model 是否已存在（看 `app/models/`）。如有 `EtfPool` ORM，loader 直接 `session.add(EtfPool(...))`；如无，本次 change 不引入 pool 持久化（fixture 仅保留 metadata，loader 跳过 pool key）。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| fixture 漂移（akshare API 变更 / 个股退市） | 在 README 标注「生成日期 + 适用版本」；generator 脚本保留在仓库，开发者可一键重生成 |
| fixture 体积膨胀 | 单文件 ≤ 1 MB；超阈值时改 SQLite dump 或拆多个 JSON |
| demo 数据与真实 akshare 数据混淆 | fixture 中 `source_note` 显式标注「akshare 一次性快照」；README 明确两条路径互斥但可混跑 |
| loader 写失败时部分写入无回滚 | 单次 session.commit，失败整批回滚；测试覆盖「半数失败后 DB 干净」场景 |
| 用户误把 demo 数据当成回测建议 | README 显著位置加「⚠️ 演示数据仅用于系统功能演示，不构成投资建议」 |
| 生成脚本依赖 akshare 但 akshare 不在 dev 依赖 | `pyproject.toml` 已含 akshare（v1.0 阶段已加），无需新增 |
| docker 容器内 generate 失败 | generator 不入容器；仅在 dev 主机跑；Makefile 不暴露 generate target |

## Migration Plan

无（纯新增，无破坏性变更）。部署即生效。

**回滚**：删除 `backend/app/data/fixtures/demo_data.json` + `seed_demo.py` + `Makefile` 中 `seed-demo` target + README 章节即可。

## Open Questions

| 问题 | 决策 |
|------|------|
| 是否预置 pool？ | **是**，但需要先查 ORM 模型是否存在 `EtfPool`（如不存在则 fixture 不写 pool，loader 跳过） |
| 是否预置回测运行？ | **否**，见决策 4 |
| 是否提供 `make backtest-demo` 一键跑示例回测？ | **是**，是独立于本 change 的可选 follow-up |
| fixture 路径放哪？ | `backend/app/data/fixtures/`（与 `app/data/` 同级，作为 app 子包；`backend/app/data/fixtures/__init__.py` 空文件） |