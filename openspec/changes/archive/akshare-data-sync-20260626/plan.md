# Implementation Plan: akshare 数据同步脚本

## Prerequisites
- [x] 切换到 feature/akshare-data-sync 分支
- [x] 确认 backend 目录存在，FastAPI + 数据模型就位
- [x] 确认 Python 3.11+ 与 uv 可用

## Dependencies
- [x] `uv add akshare`（运行时依赖）
- [x] 确认 `backend/pyproject.toml` 已记录新依赖

## Data Types
- [x] `app/data/__init__.py` 空包文件
- [x] `app/data/client.py` 定义 `EtfMasterRow` / `DailyPriceRow` dataclass

## Client Layer
- [x] `AkshareClient` Protocol 定义（`list_etfs` / `fetch_etf_hist`）
- [x] `AkshareHttpClient` 类：内部 `import akshare as ak`（懒加载），实现两个方法
- [x] `FakeAkshareClient` 类：构造函数接预设 etfs + prices dict，实现两个方法

## Upsert Utilities
- [x] `app/data/upsert.py`：`upsert_etf(session, row)` 使用 `sqlite.insert(...).on_conflict_do_update`
- [x] `app/data/upsert.py`：`upsert_daily_price(session, code, row)` 使用 `sqlite.insert(...).on_conflict_do_update(index_elements=[code, date])`

## Sync Functions
- [x] `app/data/etf_master.py`：`sync_etf_master(session, client)` 遍历 client.list_etfs()，逐条 upsert_etf，commit，返回汇总 dict
- [x] `app/data/daily_prices.py`：`sync_daily_prices(session, client, codes, start, end, full=False)` 遍历 codes，try/except 包裹 fetch + upsert，失败 log warning 并 continue，最后返回汇总 dict；增量模式查 DB 最后日期

## CLI Entry
- [x] `app/data/sync.py`：argparse 顶层 parser + 两个子命令 `etfs` 与 `prices`
- [x] 子命令 `etfs`：调用 `sync_etf_master`，打印汇总（成功/失败数），退出码 0/1
- [x] 子命令 `prices`：解析 `--codes` / `--start` / `--end` / `--full`，调用 `sync_daily_prices`，打印汇总
- [x] `__main__` 入口：构造 SessionLocal + AkshareHttpClient，调用对应子命令

## Testing
- [x] `tests/conftest.py` 已存在（sqlite-data-model 提供），无需修改
- [x] `tests/test_akshare_client.py`：`FakeAkshareClient` 单测（list_etfs / 日期过滤 / Protocol 检查）
- [x] `tests/test_etf_master_sync.py`：首次同步 / 重复同步 upsert（name 更新） / 空响应
- [x] `tests/test_daily_prices_sync.py`：首次 / 重复 upsert / 单只失败不影响后续 / full / 增量默认
- [x] `tests/test_upsert.py`：`upsert_etf` / `upsert_daily_price` 直接调用
- [x] `tests/test_sync_cli.py`：parser / cmd_etfs / cmd_prices / main entry，全部 stub fake client

## TDD Verification
- [x] 写完 20 个新测试后运行 pytest 全部通过（41/41 GREEN）

## Build & Runtime Verification
- [x] `cd backend && uv run pytest` → 41/41 通过
- [x] `cd backend && python -m app.data.sync --help` → 打印 usage
- [x] `cd backend && python -m app.data.sync etfs --help` 与 `prices --help` → 打印子命令 usage

## Documentation
- [x] `backend/README.md` 增补「数据同步（akshare）」章节：CLI 用法、Protocol 抽象说明、退出码

## Acceptance Check
- [x] 逐条对照 `proposal.md` 的 9 项 Acceptance Criteria，全部满足
- [x] 逐条对照 `spec.md` 的 9 个 Requirement 至少一个 Scenario 通过
