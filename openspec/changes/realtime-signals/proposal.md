# Proposal: 实时信号计算与排名

## What
实现「给定 ETF 池 + 价格历史 → 计算每日动量排名 + 调仓建议 → 持久化到 SignalSnapshot」端到端链路，让前端看板能查到「今天的买/卖/持」建议与排名。

- **`app/signals/compute.py`**：纯计算
  - `compute_signals(etf_pool, price_history, *, signal_date, top_n=5, lookback=252, skip=21) -> list[SignalRow]`
  - `SignalRow` frozen dataclass：`(etf_code, momentum_score, rank, action)`
  - 复用 `app.factors.momentum.compute_momentum_scores` 与 `rank_scores`
  - action 规则（默认）：`top_n` 以内 = `BUY`；其余有有效分数 = `HOLD`；分数 None = `WATCH`（无足够历史）
- **`app/signals/persistence.py`**：写 `SignalSnapshot` ORM 行
  - `save_signal_snapshot(session, signal_date, rows) -> list[SignalSnapshot]`
  - 同 `(date, etf_code)` 重复时 upsert（基于已存在的 `uq_signal_snapshots_date_etf`）
  - action 长度限制 8（与 ORM `String(8)` 对齐：`BUY`/`HOLD`/`WATCH`）
- **`app/data/signal_cli.py`**：命令行入口
  - `python -m app.data.signal run --date YYYY-MM-DD --pool <codes>` 算并落库
  - `python -m app.data.signal show --date YYYY-MM-DD` 读最新快照
- **`app/signals/__init__.py`**：re-export 公开 API

## Why
当前已有：
- `SignalSnapshot` ORM（`date, etf_code, momentum_score, rank, action` + UNIQUE(date, etf_code)）
- `app.factors.momentum` 提供 12-1 动量与排名算法
- `app.data.daily_prices.sync_daily_prices` 已能拉取 ETF 日线

**缺什么**：
1. 没有"今日信号"计算逻辑 — ORM 表空着
2. 没有"前端看板能查到的数据" — 即便后端算出来，没落库前端也读不到
3. 没有 `action` 字段的语义约定 — schema 有列但没人负责写入

补完后：
- 前端 GET `/api/signals/latest` 能返回 `{date, rows: [{code, score, rank, action}, ...]}`
- 调仓建议（top-N 买入、其余持有）以 `action` 字段直接呈现
- 历史快照可回放（"2024-06-15 那天的建议是哪些 ETF？"）

## Scope
- [x] backend
- [ ] frontend（前端展示另起 change）

## Out of Scope（本 change 不做）
- 实时（盘中）信号 — MVP 是 T+1 收盘后批量算
- 推送 / 通知（邮件 / 微信）
- 多策略对比
- 用户自定义池管理 UI / API（先用配置 / 命令行传入 pool）
- 业绩指标快照（业绩展示用 BacktestRun 即可）
- 仓位大小建议（只输出 BUY/HOLD，不输出 weight）

## Acceptance Criteria
- [ ] `app/signals/compute.py` 存在，导出 `compute_signals` 和 `SignalRow`
- [ ] `compute_signals(etf_pool, price_history, signal_date, *, top_n=5)` 返回 list[SignalRow]
- [ ] 行为：复用 `app.factors.momentum` 的 compute + rank；`top_n` 以内 `action='BUY'`，有有效分数但未入选 `action='HOLD'`，无有效分数 `action='WATCH'`
- [ ] 返回按 `rank` 升序；ties 由 `rank_scores` 的 competition ranking 决定
- [ ] momentum_score 写入时 quantize 到 6 位小数（与 `Numeric(10,6)` 对齐）
- [ ] `app/signals/persistence.py` 存在，导出 `save_signal_snapshot`
- [ ] `save_signal_snapshot(session, date, rows)` 写 SignalSnapshot 行；同 `(date, etf_code)` 已存在时更新（upsert）
- [ ] `app/data/signal_cli.py` 存在，提供 `run --date YYYY-MM-DD` 与 `show --date YYYY-MM-DD` 子命令
- [ ] `app/signals/__init__.py` re-export 公开 API
- [ ] 新增 `tests/test_signals_compute.py` 与 `tests/test_signals_persistence.py`，至少 12 + 6 = 18 个测试
- [ ] 现有 119 个测试（数据模型 + akshare + 动量 + 回测 + 业绩指标）全部仍然通过
- [ ] README 增补「实时信号」小节：调用示例 + CLI 用法 + action 语义

## 设计决策（脑暴沉淀）
> 待 brainstorming 阶段填充

## Status
- [x] 提案已确认（2026-06-26，BUY/HOLD/WATCH 三态，compute + persist + CLI，不含 API）
