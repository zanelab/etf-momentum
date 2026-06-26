# Spec: 实时信号计算与排名

## ADDED Requirements

### Requirement: compute_signals 公开 API
`compute_signals(etf_pool, price_history, signal_date, *, top_n=5, lookback=252, skip=21)` 返回 list[SignalRow]。

#### Scenario: 基础调用返回 N 个 SignalRow
- Given 5 只 ETF 池 + 完整 273 天历史
- When 调用 `compute_signals(pool, history, date(2024,12,31), top_n=2)`
- Then 返回 5 个 SignalRow，按 rank 升序；前 2 个 action='BUY'，其余有分 action='HOLD'

#### Scenario: 空池
- Given `etf_pool=[]`
- When 调用
- Then 返回 `[]`

### Requirement: 12-1 动量复用
`compute_signals` 内部调用 `app.factors.momentum.compute_momentum_scores` 与 `rank_scores`，不重新实现。

#### Scenario: 动量算法一致
- Given 同一组 price_history
- When 分别 `compute_signals(...)` 与 `compute_momentum_scores(...) + rank_scores(...)`
- Then `score` 与 `rank` 字段完全一致

### Requirement: action 三态语义
- `BUY`：rank ≤ top_n 且 score 非 None
- `HOLD`：rank > top_n 或 score 非 None 但未进入 top_n
- `WATCH`：score = None（数据不足）

#### Scenario: BUY / HOLD 分布
- Given 10 只 ETF，top_n=3
- When 调用
- Then 前 3 个 row action='BUY'，其余 7 个 action='HOLD'

#### Scenario: WATCH 落库
- Given 5 只 ETF，其中 1 只有 100 天历史（< 273）
- When 调用
- Then 该 ETF row score=None, rank=None, action='WATCH'；仍出现在返回列表

### Requirement: momentum_score 精度
写入与返回值均 quantize 到 6 位小数（与 ORM `Numeric(10,6)` 对齐）。

#### Scenario: score 量化
- Given 价格历史计算原始 score = Decimal("0.123456789")
- When 调用
- Then 返回的 `SignalRow.momentum_score == Decimal("0.123457")`

### Requirement: 输入不变性
`compute_signals` 不修改输入 `price_history` / `etf_pool`。

#### Scenario: 调用后输入未变
- Given price_history 与 etf_pool
- When 调用 `compute_signals`
- Then 原 dict 与 list 内容未变

### Requirement: save_signal_snapshot 写入 ORM
`save_signal_snapshot(session, signal_date, rows, *, overwrite=False)` 写 `SignalSnapshot` 行；同 `(date, etf_code)` 已存在时按 `overwrite` 决定行为。

#### Scenario: 默认跳过已存在
- Given 同 `(2024-12-31, 510300)` 已存在
- When `overwrite=False`
- Then 跳过该行；其余新增；返回写入行数

#### Scenario: --force 覆盖
- Given 同 `(2024-12-31, 510300)` 已存在
- When `overwrite=True`
- Then 更新该行 score / rank / action；返回写入行数

#### Scenario: 空 rows 不调 add
- Given rows=[]
- When 调用
- Then `session.add` 调用 0 次；commit 仍调用

#### Scenario: score=None 落库为 NULL
- Given row.score=None
- When 调用
- Then 写入的 `momentum_score` 为 None（SQL NULL）

### Requirement: CLI run 子命令
`python -m app.data.signal run --date YYYY-MM-DD --pool <codes> [--top-n N] [--force]` 从 DB 读 price_history，算信号并落库。

#### Scenario: 必需参数缺失
- Given 缺 `--date` 或 `--pool`
- When 调用
- Then argparse 退出码 2，打印 usage

#### Scenario: happy path
- Given 3 只 ETF 池 + 完整历史已落 daily_prices
- When 调用 `python -m app.data.signal run --date 2024-12-31 --pool 510300,510500,510880`
- Then 读 3 只 ETF 历史 → 算信号 → 落库 3 行 → 打印 "wrote 3 rows to signal_snapshots"

#### Scenario: --force 行为
- Given 2024-12-31 已存在 3 行快照
- When `--force` 重复调用
- Then 覆盖更新 3 行（score/rank/action 重算）

### Requirement: CLI show 子命令
`python -m app.data.signal show --date YYYY-MM-DD` 按 rank 升序打印 snapshot。

#### Scenario: 显示当日快照
- Given 2024-12-31 已有 5 行
- When 调用
- Then 按 rank 升序打印 5 行（code / score / rank / action）

#### Scenario: 当日无数据
- Given 2024-12-31 无 snapshot
- When 调用
- Then 打印 `No snapshot for 2024-12-31`，退出码 0

### Requirement: 异常路径
- `top_n <= 0` → `ValueError`
- 同 `(date, etf_code)` 已存在且 `overwrite=False` → 跳过（不抛错）

#### Scenario: top_n 非法
- Given top_n=0 或 -1
- When 调用
- Then `compute_signals` raise `ValueError`

### Requirement: pytest 测试覆盖
新增 `tests/test_signals_compute.py`（≥12 个）与 `tests/test_signals_persistence.py`（≥6 个），加上 CLI 测试若干。

#### Scenario: 全套通过
- Given backend 目录运行 `uv run pytest`
- When 收集所有 `tests/test_*.py`
- Then 全部通过；退出码 0（119 原有 + 新增 ≥ 18 = ≥ 137）

### Requirement: README 增补实时信号小节
backend/README.md 新增「实时信号」章节：调用示例 + CLI 用法 + action 语义。

#### Scenario: README 含三态说明
- Given 阅读 backend/README.md
- When 查找「实时信号」章节
- Then 含 `BUY` / `HOLD` / `WATCH` 语义表 + CLI 命令示例
