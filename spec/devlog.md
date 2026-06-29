# 开发日志

## 初始化

- 日期：2026-06-28 初始化 SpecCoding 结构
- OpenSpec CLI v1.3.1 已配置（spec-driven）
- 工作流骨架就位：spec/、openspec/、AGENTS.md、backend/、frontend/
- 架构选型确认：全栈 React 前端 + Python 后端
- Git 仓库初始化（main 分支，commit `7529e74`）
- 启动首个变更 `bootstrap-fullstack`（feature 分支，commit `8a5648d`）
- 状态：phase=init，可进入 proposal 阶段

## bootstrap-fullstack 变更归档

- 日期：2026-06-28（plan 72/72，10 个 commit）
- 分支：`feature/bootstrap-fullstack`
- 归档目录：`openspec/changes/archive/bootstrap-fullstack-20260628/`
- 范围：完整前后端骨架 + 全部 M0–M8 里程碑
- 关键产物：
  - **后端**：FastAPI + SQLModel + SQLite；11 个端点；74 个 pytest 用例
  - **前端**：React + Vite + TS + TanStack Query + recharts；8 个页面
  - **筛选核心**：`filter_etfs` 从 `main.py` 迁移至 `backend/app/services/screening.py`，移除 JoinQuant 全局依赖
  - **JoinQuant 兼容**：`_jq_shim.py` + `test_screening_parity.py` 三个对照测试（default / industry-diverse / ma-filter-off）确认迁移后行为与原版一致
  - **回测引擎**：日级重放 + equal-weight + 净值序列 + 5 项统计
  - **数据同步（mock）**：`daily_sync.sync_today()` 写 `data/daily_sync/YYYY-MM-DD.json`
  - **CI 验证**：`pytest` 74 passed / `ruff check` 通过 / `tsc --noEmit` 通过 / `npm run build` 通过
- 已知限制：
  - 行情数据为 GBM mock fixture（10 只 ETF × 500 天）
  - 持仓为 `portfolio_mock` 硬编码
  - 当日解析以 fixture 末日代替真实交易日历

## real-data-source 变更归档

- 日期：2026-06-29（plan 43/43，11 个 commit）
- 分支：`feature/real-data-source`
- 归档目录：`openspec/changes/archive/real-data-source-20260629/`
- 范围：真实数据源接入（akshare）+ 缓存装饰器 + 动态池管理 + 数据源观测面板
- 关键产物：
  - **`make_source(name)` 工厂**：根据 `ETF_DATA_SOURCE` 环境变量或 per-request 参数选择 `fixture` 或 `akshare`；akshare 路径自动包一层 `CachedSource`
  - **`AkShareSource`**：接入 akshare 的 `fund_etf_hist_em`（K 线）和 `fund_etf_spot_em`（全市场 ETF 列表，~1500 条）；含中文列名映射、指数退避重试、fixture 降级
  - **`CachedSource` 装饰器**：读穿透缓存到 SQLite `market_bar_cache` 表；暴露 `stats() / clear()`；命中/未命中计数器
  - **`retry_with_backoff` 工具**：指数退避，可配置重试次数与初始延迟
  - **动态池**：`DynamicPoolEntry` SQLModel 表 + 3 个端点（GET 列表 / POST sync / PATCH 切换启用）；sync 强制走 akshare（不受 `ETF_DATA_SOURCE` 影响），失败返回 503/502 明确错误
  - **观测**：`GET /api/health?stats=1` 在 CachedSource 时返回 `cache_hit` / `cache_miss` 计数
  - **前端**：`/datasource` 页面展示健康/缓存统计/动态池列表 + 同步按钮 + 行内启用开关
  - **CI 验证**：`pytest` 116 passed（新增 42 个用例）/ `ruff check` 通过（忽略 UP045 因为 venv 锁 py3.9）/ `tsc --noEmit` 通过 / `npm run build` 通过
- 已知限制：
  - 动态池同步仍需手动触发（`POST /sync` 或前端按钮），未做定时调度
  - akshare 返回 6 位裸码（如 `512650`），与静态池带后缀格式（如 `512650.XSHG`）未做归一化，`filter_etfs` 合并两池时需补一步
  - CachedSource 对 `history` 使用"日历超集"启发式，存在少量过度刷写缓存的情况
  - 同步任务尚未接入定时器（手动调用 `sync_today()`）
- 下一步：merge 阶段合入 main

## akshare-code-normalization 变更（执行中，2026-06-29）

- 日期：2026-06-29（real-data-source 归档后启动的新迭代）
- 范围：ETF 代码格式归一化（akshare 6 位裸码 ↔ 静态池带后缀格式）
- 关键产物：
  - **`app/data_sources/codes.py`**：新增 `normalize_etf_code(code) -> str` 与 `same_etf(a, b) -> bool`；规范格式 `XXXXXX.XSHG/XSHE`；交易所推断规则为首字符 5/6→SH、1/0/3→SZ
  - **`AkShareSource.all_etf_entries`**：返回前对每个 code 应用归一化（裸码 → canonical，非法 code 静默丢弃）
  - **`filter_etfs` 合并**：用 `{normalize_etf_code(c) for c in static + dynamic}` 去重；defensive 比对用 `normalize_etf_code(params.defensive_etf)`
  - **`load_display_names` 双查**：先按原 code 查 `static_pool`，未命中再按 canonical form 查；输出 key 保持输入形式
  - **动态池 sync upsert key**：sync 前先把存量裸码 row 迁移到 canonical form（同一标的不会出现两个 row）；PATCH 路径也对 code 参数做归一化
- CI 验证：`pytest` 159 passed（116 + 新增 43）/ `ruff check` 通过 / `tsc --noEmit` 通过 / `npm run build` 通过
- 设计依据：对照 `main.py:282` 显式融合逻辑（`list(set(STATIC_ETF_POOL + g_dynamic_pool))`）与 `main.py:131-133` 原版动态池拉取（JoinQuant `get_all_securities` 自带后缀），确认 akshare 与 JoinQuant 格式差异才是真正的语义不一致源
- 已知限制（仍是 M9 原始限制）：动态池手动同步、CachedSource 启发式过刷写
