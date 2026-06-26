# Implementation Plan: 后端 REST API

## Prerequisites
- [x] 切换到 feature/rest-api 分支
- [x] 确认 backend 服务可启动（已通过 146 测试）
- [x] 确认 Pydantic v2 在用（与 SQLAlchemy 2.0 配套）

## Dependencies
- [x] 无新增运行时依赖（FastAPI / Pydantic 已就位）
- [x] 确认 `backend/pyproject.toml` 无需更新

## Module Structure
- [x] `app/api/v1/schemas.py` 创建
- [x] `app/api/v1/etfs.py` 扩展
- [x] `app/api/v1/signals.py` 创建
- [x] `app/api/v1/backtest.py` 创建
- [x] `app/api/v1/sync.py` 创建
- [x] `app/api/v1/router.py` 聚合
- [x] `app/main.py` 加 CORS

## Schemas
- [x] `ETFPydantic` / `ETFListPydantic`
- [x] `DailyPricePydantic`
- [x] `SignalRowPydantic` / `SignalSnapshotPydantic`
- [x] `BacktestRequestPydantic` / `BacktestRunPydantic` / `BacktestListPydantic`
- [x] `NavPointPydantic` / `NavSeriesPydantic`
- [x] `SyncPricesRequestPydantic` / `SyncResponsePydantic`
- [x] `ListResponsePydantic` 通用泛型

## ETF Router
- [x] `GET /etfs?limit=50&offset=0&category=...`
- [x] `GET /etfs/{code}` (404 on not found)
- [x] `GET /etfs/{code}/prices?start=...&end=...&limit=500`
- [x] `GET /etfs/count` (保留冒烟)

## Signal Router
- [x] `GET /signals?date=...` 不传 date → DB MAX(date)
- [x] `GET /signals/latest`

## Backtest Router
- [x] `POST /backtest`（同步执行 run_backtest + save_backtest_run）
- [x] `GET /backtest?limit=20&offset=0`
- [x] `GET /backtest/{id}` (404 on not found)
- [x] `GET /backtest/{id}/nav` (404 on not found)

## Sync Router
- [x] `POST /sync/etfs` 调 sync_etf_master
- [x] `POST /sync/prices` 调 sync_daily_prices

## CORS
- [x] `app/main.py` 加 `CORSMiddleware` allow_origins=localhost:5173 + 127.0.0.1:5173

## Pagination Utility
- [x] `_clamp_limit(limit: int | None) -> int` clamp [1, 500]，默认 50
- [x] `_clamp_offset(offset: int | None) -> int` clamp ≥ 0，默认 0

## Testing
- [x] `tests/test_api_schemas.py` 创建（15 tests）
- [x] `test_decimal_serialized_as_string`：Decimal → str
- [x] `test_backtest_request_defaults`
- [x] `test_etf_from_orm`
- [x] `tests/test_api_etfs.py` 创建（11 tests）
- [x] `test_list_etfs_empty` / `test_list_etfs_pagination` / `test_list_etfs_category_filter`
- [x] `test_list_etfs_limit_clamp` / `test_list_etfs_offset_clamp`
- [x] `test_get_etf_detail` / `test_get_etf_not_found_404`
- [x] `test_get_etf_prices_date_range` / `test_get_etf_prices_default_limit`
- [x] `test_etfs_count_smoke`
- [x] `tests/test_api_signals.py` 创建（7 tests）
- [x] `test_signals_by_date` / `test_signals_by_date_empty`
- [x] `test_signals_no_date_returns_latest` / `test_signals_explicit_latest`
- [x] `tests/test_api_backtest.py` 创建（12 tests）
- [x] `test_post_backtest_happy_path`
- [x] `test_post_backtest_empty_pool_422`
- [x] `test_post_backtest_start_after_end_422`
- [x] `test_post_backtest_missing_price_history_422`
- [x] `test_get_backtest_list` / `test_get_backtest_list_pagination`
- [x] `test_get_backtest_detail` / `test_get_backtest_detail_404`
- [x] `test_get_backtest_nav` / `test_get_backtest_nav_404`
- [x] `tests/test_api_sync.py` 创建（6 tests）
- [x] `test_post_sync_etfs`
- [x] `test_post_sync_prices_with_codes`
- [x] `test_post_sync_prices_with_date_range`
- [x] `tests/test_api_cors.py` 创建（3 tests）

## TDD Verification
- [x] 写完所有测试后运行 pytest 全部通过（200/200）

## Build & Runtime Verification
- [x] `cd backend && uv run pytest` → 200 全部通过（146 原有 + 54 新增 = 200）
- [x] `cd backend && uv run uvicorn app.main:app --port 8000` 启动 + curl 各端点 200
- [x] 启动后访问 `http://localhost:8000/docs` 看到 12 个新端点 + 1 个现有

## Documentation
- [x] `backend/README.md` 增补「REST API」章节：
  - 端点表（method / path / 用途 / 关键参数）
  - 4 个 curl 示例（list / post backtest / signals latest / sync etfs）
  - 错误格式说明（FastAPI 默认 `{detail: ...}`）
  - CORS 配置（默认 origin 列表）
  - 分页约定（limit/offset 默认值）

## Acceptance Check
- [x] 逐条对照 proposal.md 的 12 项 Acceptance Criteria，全部满足
- [x] 逐条对照 spec.md 的 11 个 Requirement 至少一个 Scenario 通过
