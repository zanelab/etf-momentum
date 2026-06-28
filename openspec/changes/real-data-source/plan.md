# Implementation Plan: real-data-source

## Prerequisites

- [x] 1.1 [后端] 添加 `akshare` 到 `backend/pyproject.toml` 依赖（dev 依赖，避免生产必须装）
- [x] 1.2 [后端] 在 `.env.example` 与 README 添加 `ETF_DATA_SOURCE` 环境变量说明
- [x] 1.3 [共享] 确认 git 已切到 `feature/real-data-source` 分支（off main）

## Backend — 数据模型

- [x] 2.1 [后端] 新建 `backend/app/models/market_bar_cache.py`（SQLModel `MarketBarCache`，复合主键 `(code, date)`）
- [x] 2.2 [后端] 在 `backend/app/models/__init__.py` 注册 `MarketBarCache`
- [x] 2.3 [后端] 新建 `backend/app/models/dynamic_pool.py`（SQLModel `DynamicPoolEntry`，主键 `code`）
- [x] 2.4 [后端] 在 `backend/app/models/__init__.py` 注册 `DynamicPoolEntry`
- [x] 2.5 [后端] 写 `tests/test_market_bar_cache.py`：创建/查询/复合主键唯一性
- [x] 2.6 [后端] 写 `tests/test_dynamic_pool_model.py`：创建/查询/is_enabled 默认值

## Backend — 韧性工具

- [x] 3.1 [后端] 新建 `backend/app/data_sources/retry.py`（`retry_with_backoff(fn, max_retries, backoff_factor, initial_delay)`）
- [x] 3.2 [后端] 写 `tests/test_retry.py`：成功路径、瞬时失败后成功、全失败抛错、退避次数正确

## Backend — AkShare 适配器

- [x] 4.1 [后端] 新建 `backend/app/data_sources/akshare_source.py`（`AkShareSource`，字段映射，降级）
- [x] 4.2 [后端] 写 `tests/test_akshare_source.py`（mock akshare）：history 字段映射、snapshot 取末行、all_etfs 列表、未装包抛 ImportError、失败降级
- [x] 4.3 [后端] 在 `pyproject.toml` 加 `akshare` 为可选依赖（`[project.optional-dependencies] realtime = ["akshare>=1.16"]`）

## Backend — 缓存装饰器

- [x] 5.1 [后端] 新建 `backend/app/data_sources/cache.py`（`CachedSource`，复合 `(code, date)` 读写、stats 计数）
- [x] 5.2 [后端] 写 `tests/test_cached_source.py`：snapshot 命中/未命中、history 部分命中、stats 计数、clear
- [x] 5.3 [后端] 确认 `CachedSource` 复用项目根 `etf_momentum.db`（与 `ETF_DB_PATH` 一致）

## Backend — 源选择器

- [x] 6.1 [后端] 新建 `backend/app/data_sources/__init__.py`（`make_source(name=None)`）
- [x] 6.2 [后端] 写 `tests/test_make_source.py`：默认 fixture / env=akshare / 显式 name / 未知 name 抛错
- [x] 6.3 [后端] 替换 `backend/app/api/market.py` 的 `_market()` 为 `make_source(source)`
- [x] 6.4 [后端] 替换 `backend/app/api/screening.py` 的 `_market()` 为 `make_source(source)`
- [x] 6.5 [后端] 替换 `backend/app/api/backtest.py` 的 `_market()` 为 `make_source(source)`
- [x] 6.6 [后端] 三个 API 路由增加 `source: str | None = None` 参数透传

## Backend — 动态池 API

- [x] 7.1 [后端] 在 `backend/app/api/configs.py` 新增 `GET /api/configs/pool/dynamic`（列出所有 DynamicPoolEntry）
- [x] 7.2 [后端] 新增 `POST /api/configs/pool/dynamic/sync`（拉 akshare、UPSERT）
- [x] 7.3 [后端] 新增 `PATCH /api/configs/pool/dynamic/{code}`（toggle is_enabled）
- [x] 7.4 [后端] 写 `tests/test_dynamic_pool_api.py`：list/sync (mock akshare)/patch 启用与 404

## Backend — Health & 缓存观测

- [ ] 8.1 [后端] 扩展 `GET /api/health`：当 source 为 CachedSource 时返回 `cache_hit`、`cache_miss`（通过 `?stats=1` 显式启用避免每次都读 counter）
- [ ] 8.2 [后端] 写 `tests/test_health_stats.py`：fixture 默认不返回 cache stats、akshare + stats=1 返回

## Frontend — DataSource 页面

- [ ] 9.1 [前端] 在 `frontend/src/api/hooks.ts` 添加 `useHealthStats`、`useDynamicPool`、`useSyncDynamicPool`、`useToggleDynamicEntry` hooks
- [ ] 9.2 [前端] 新建 `frontend/src/pages/DataSource.tsx`：源类型 / 末次同步 / 缓存命中统计 / 同步按钮 / 动态池列表
- [ ] 9.3 [前端] 在 `frontend/src/App.tsx` 增加 `/datasource` 路由与导航项
- [ ] 9.4 [前端] 在 `frontend/src/api/client.ts` 暴露 `DataSourceStats`、`DynamicPoolEntry` 类型

## Testing — 集成与回归

- [ ] 10.1 [共享] 确认 `pytest backend/tests/` 74 个旧用例全部继续通过
- [ ] 10.2 [后端] `pytest` 至少新增 6 个测试文件（market_bar_cache / dynamic_pool_model / retry / akshare_source / cached_source / make_source / dynamic_pool_api / health_stats）
- [ ] 10.3 [共享] `ruff check backend/app/ backend/tests/` 通过
- [ ] 10.4 [前端] `tsc --noEmit` 通过
- [ ] 10.5 [前端] `npm run build` 通过

## Docs

- [ ] 11.1 [共享] 更新 `README.md`：API 端点表新增 3 个动态池端点 + 缓存统计字段
- [ ] 11.2 [共享] 更新 `README.md` 已知限制段：标注 akshare 接入情况（仍需手动同步、未做定时）
- [ ] 11.3 [共享] 更新 `.env.example`：新增 `ETF_DATA_SOURCE` 行

## Submission

- [ ] 12.1 [共享] 提交所有变更到 `feature/real-data-source`
- [ ] 12.2 [共享] 在 commit message 中标注 `fix:` / `feat:` 前缀
