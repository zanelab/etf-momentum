# Proposal: akshare 数据同步脚本

## What
为 etf-momentum 系统接入 akshare（A股开源行情库），建立从 akshare 到本地 SQLite 的数据同步链路：

- **ETF 主数据同步**：从 akshare 拉取全市场 ETF 列表，写入 `etfs` 表
- **日线行情同步**：按 code 拉取历史 OHLCV，写入 `daily_prices` 表（按 `(code, date)` upsert，幂等）
- **CLI 入口**：通过 `python -m app.data.sync ...` 子命令触发；支持 `--codes`、`--start`、`--end`、`--full` 等参数
- **Akshare 客户端抽象层**：将 akshare API 调用封装在接口后，便于单测时 mock

## Why
当前数据库已有 4 张表，但没有任何数据。后续所有业务模块都依赖历史价格：
- 阶段 2「核心能力」中的动量因子计算模块、回测引擎、业绩指标、实时信号都需要 `daily_prices` 数据
- 没有数据无法跑通端到端流，也无法做 UI 演示

数据同步是连接「数据层」与「业务层」的桥梁，提前实现可以让后续 change 立即可用。

## Scope
- [x] backend
- [ ] frontend

## Out of Scope（本 change 不做）
- baostock 接入（akshare 已经是 A 股的事实标准，MVP 不引入第二数据源）
- 任务调度 / cron / APScheduler（后续 Docker compose change 或独立 scheduling change 处理）
- 实时行情 / 分钟级数据（MVP 仅做日线）
- 数据校验与异常告警（首版仅记录错误日志）

## Acceptance Criteria
- [ ] `app/data/` 目录：客户端抽象 (`AkshareClient` Protocol) + 真实实现 (`AkshareHttpClient`) + Fake 实现 (`FakeAkshareClient`) 用于测试
- [ ] `app/data/sync.py` 提供两个同步函数：`sync_etf_master(session)` 与 `sync_daily_prices(session, codes, start, end)`
- [ ] `python -m app.data.sync etfs` CLI 命令：拉取全市场 ETF 并 upsert 到 `etfs`
- [ ] `python -m app.data.sync prices --codes 510300,510500 --start 2024-01-01` CLI 命令：拉取指定 ETF 的历史行情并 upsert 到 `daily_prices`
- [ ] `daily_prices` 写入使用 `INSERT ... ON CONFLICT(code, date) DO UPDATE`（SQLite upsert），重复运行不抛错
- [ ] `etfs` 写入使用 `INSERT ... ON CONFLICT(code) DO UPDATE`，名称/分类等可被刷新
- [ ] pytest 套件：
  - FakeAkshareClient 单测覆盖（无需网络）
  - sync_etf_master 集成测试（写入 etfs 后再 sync 一次应不重复）
  - sync_daily_prices 集成测试（写入 daily_prices 后再 sync 同区间应 upsert，不抛 IntegrityError）
  - CLI 入口冒烟测试（`subprocess` 调用 `python -m app.data.sync etfs --dry-run`）
- [ ] `backend/pyproject.toml` 增加 `akshare` 依赖（runtime）
- [ ] `backend/README.md` 增补「数据同步」章节
- [ ] 失败时记录日志并继续（非 fail-fast），便于部分 ETF 抓取失败时仍能完成大部分

## Status
- [x] 提案已确认
