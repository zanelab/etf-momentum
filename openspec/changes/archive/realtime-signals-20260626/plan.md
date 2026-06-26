# Implementation Plan: 实时信号计算与排名

## Prerequisites
- [x] 切换到 feature/realtime-signals 分支
- [x] 确认 backend 目录存在
- [x] 确认 daily_prices 表已通过 akshare 同步（CLI 内部读此表）

## Dependencies
- [x] 无新增运行时依赖
- [x] 确认 `backend/pyproject.toml` 无需更新

## Module Structure
- [x] `app/signals/__init__.py` 创建并 re-export
- [x] `app/signals/compute.py` 创建
- [x] `app/signals/persistence.py` 创建
- [x] `app/data/signal.py` 创建（CLI 入口，与 `app.data.sync` 命名一致）

## Core Implementation
- [x] `app/signals/compute.py` 定义 `SignalRow`（frozen dataclass）
- [x] `app/signals/compute.py` 实现 `compute_signals(etf_pool, price_history, signal_date, *, top_n=5, lookback=252, skip=21) -> list[SignalRow]`
- [x] `app/signals/compute.py` 复用 `app.factors.momentum.compute_momentum_scores` + `rank_scores`
- [x] `app/signals/compute.py` `top_n <= 0` raise `ValueError`
- [x] `app/signals/compute.py` score quantize 到 6 位
- [x] `app/signals/persistence.py` 实现 `save_signal_snapshot(session, signal_date, rows, *, overwrite=False) -> list[SignalSnapshot]`
- [x] `app/signals/persistence.py` 同 `(date, etf_code)` upsert 逻辑（先 SELECT 检查 / overwrite=True 用 update）
- [x] `app/data/signal.py` 实现 `python -m app.data.signal run|show` 子命令（argparse）
- [x] `app/data/signal.py` run 子命令：开 session → 读 daily_prices → compute_signals → save_signal_snapshot → commit
- [x] `app/data/signal.py` show 子命令：按 rank 升序打印
- [x] `app/models/signal_snapshot.py` `momentum_score` / `rank` 改 nullable
- [x] `alembic/versions/a1b2c3d4e5f6_*.py` SQLite 兼容 migration（batch_alter_table）

## Testing
- [x] `tests/test_signals_compute.py` 创建（15 个测试）
- [x] `test_top_n_buy_distribution`：5 只 + top_n=2 → 2 BUY + 3 HOLD
- [x] `test_with_watch`：1 只有 100 天历史 → WATCH，rank=None
- [x] `test_empty_pool`：返回 []
- [x] `test_score_quantize_6dp` & `test_score_quantize_with_full_history`：score 6 位量化
- [x] `test_input_not_mutated`：price_history 不变
- [x] `test_invalid_top_n_zero` & `test_invalid_top_n_negative`：ValueError
- [x] `test_orders_by_rank`：返回按 rank 升序
- [x] `test_top_n_exceeds_pool`：pool 2 只 + top_n=5 → 全 BUY
- [x] `test_single_etf`：pool 1 只 → 1 BUY
- [x] `test_score_none_rank_none`：WATCH row 字段
- [x] `test_ties_share_rank`：同分同 rank
- [x] `test_default_top_n_is_5`：默认 top_n=5
- [x] `tests/test_signals_persistence.py` 创建（7 个测试）
- [x] `test_inserts_new_rows`：新 ETF 插入
- [x] `test_inserts_watch_with_none_score`：score=None 落库
- [x] `test_skip_existing_default`：overwrite=False 跳过
- [x] `test_overwrite_existing`：overwrite=True 更新
- [x] `test_overwrite_partial`：部分覆盖
- [x] `test_empty_rows_no_commit_change`：rows=[] 不写入
- [x] `test_score_quantize_6dp`：score 6 位量化落库
- [x] `tests/test_signal_cli.py` 创建（6 个测试）
- [x] `test_run_happy_path`：mock DB + 算 + 写
- [x] `test_run_missing_date`：argparse exit 2
- [x] `test_run_missing_pool`：argparse exit 2
- [x] `test_run_force_flag`：--force → overwrite=True
- [x] `test_show_no_data`：exit 0 + 友好消息
- [x] `test_show_happy_path`：打印按 rank 升序

## TDD Verification
- [x] 写完所有测试后运行 pytest 全部通过

## Build & Runtime Verification
- [x] `cd backend && uv run pytest` → 全部通过（146 = 119 原有 + 27 新增）
- [x] `cd backend && uv run python -m app.data.signal --help` → 打印子命令列表
- [x] `cd backend && uv run python -c "from app.signals import compute_signals, SignalRow, save_signal_snapshot; from app.data.signal import main"` → 不抛 ImportError
- [x] `alembic upgrade head` 迁移成功
- [x] `alembic downgrade -1 && alembic upgrade head` 双向迁移验证

## Documentation
- [x] `backend/README.md` 增补「实时信号」章节

## Acceptance Check
- [x] 逐条对照 proposal.md 的 12 项 Acceptance Criteria，全部满足
- [x] 逐条对照 spec.md 的 10 个 Requirement 至少一个 Scenario 通过
