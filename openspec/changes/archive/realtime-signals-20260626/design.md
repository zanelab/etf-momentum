# Design: 实时信号计算与排名

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 4 项关键决策 + 提案阶段 2 项决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 模块位置 | `app/signals/`（新顶级目录） | signals 是独立领域（实时 vs 历史的回测），不归 backtest 包 |
| Action 语义 | `BUY` / `HOLD` / `WATCH` 三态 | MVP 不算 SELL；SELL 由前端对比昨日 BUY 集合差集得出 |
| ETF 池 | `--pool` 必传，逗号分隔 | 避免无意识全市场扫；明确调用意图 |
| 缺数据处理 | `WATCH` 落库（score=None） | 看板能解释「为什么这只不在」 |
| 重复落库 | 默认跳过 + `--force` 全量覆盖 | 补算与重写意图分离 |
| `--date` 必传 | 必须显式 | 「今天」存在歧义；明确调用意图，测试可复现 |
| Top-N 默认 | 5（与回测一致） | 与 BacktestParams.top_n 默认对齐 |
| 价格历史来源 | CLI 内部从 DB 读 `daily_prices` 表 | 不接 akshare 实时拉（避免慢 + 不一致） |
| 复用 | `app.factors.momentum.compute_momentum_scores` + `rank_scores` | 不重新实现动量逻辑 |
| 精度 | `momentum_score` quantize 到 6 位小数 | 与 ORM `Numeric(10,6)` 对齐 |
| 测试策略 | 纯函数 + mock session；CLI 用 capsys | 与 backtest-engine / metrics-extraction 保持一致 |

## 模块结构

```
backend/app/
├── signals/
│   ├── __init__.py             # re-export SignalRow, compute_signals, save_signal_snapshot
│   ├── compute.py              # 纯函数 compute_signals + SignalRow
│   └── persistence.py          # save_signal_snapshot：upsert SignalSnapshot
├── data/
│   └── signal_cli.py           # python -m app.data.signal run|show
└── ...

backend/tests/
├── test_signals_compute.py     # 纯函数测试
└── test_signals_persistence.py # mock session 测试
```

## API 设计

### `app.signals.compute`

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import date


@dataclass(frozen=True)
class SignalRow:
    etf_code: str
    momentum_score: Decimal | None  # quantize 到 6 位小数；None → WATCH
    rank: int | None                 # WATCH 时为 None
    action: str                      # "BUY" / "HOLD" / "WATCH"


def compute_signals(
    etf_pool: list[str],
    price_history: dict[str, list[tuple[date, Decimal]]],
    signal_date: date,
    *,
    top_n: int = 5,
    lookback: int = 252,
    skip: int = 21,
) -> list[SignalRow]:
    """给定 ETF 池 + 价格历史，输出 signal_date 当天的动量排名 + action。

    行为：
    1. 对 pool 中每只 ETF 取 signal_date 之前 (lookback+skip+1) 个 close；
       价格不够的 ETF → WATCH，rank=None
    2. compute_momentum_scores 算 12-1 动量（复用 app.factors.momentum）
    3. rank_scores 算排名（competition ranking；None 排末尾）
    4. 排名前 top_n → BUY；其余有分数 → HOLD；无分数 → WATCH
    5. 按 rank 升序排序后返回（ties 用 etf_code 字典序 tiebreak 由 rank_scores 保证）
    """
```

### `app.signals.persistence`

```python
def save_signal_snapshot(
    session: Session,
    signal_date: date,
    rows: list[SignalRow],
    *,
    overwrite: bool = False,
) -> list[SignalSnapshot]:
    """写 SignalSnapshot 行。

    - overwrite=False (默认): 跳过已存在 (date, etf_code) 的行
    - overwrite=True: 全量覆盖（同 date+code 已存在则更新）

    写入时 momentum_score 转为 Decimal(Numeric(10,6))；None → NULL。
    """
```

### CLI（`python -m app.data.signal`）

```
$ python -m app.data.signal run --help
usage: signal run [-h] --date DATE --pool POOL [--top-n TOP_N] [--force]

options:
  --date DATE        信号日期 YYYY-MM-DD（必传）
  --pool POOL        ETF 池，逗号分隔，如 510300,510500
  --top-n TOP_N      top N 买入（默认 5）
  --force            覆盖已存在的同 date 快照

$ python -m app.data.signal show --help
usage: signal show [-h] --date DATE

按 rank 升序打印 snapshot。
```

## 数据流

```
CLI: python -m app.data.signal run --date 2024-12-31 --pool 510300,510500
   ↓
1. open Session
2. 查 daily_prices：pool 中每只 ETF 的 (date < 2024-12-31) 历史，limit (lookback+skip+1)
3. build price_history dict
4. compute_signals(etf_pool, price_history, signal_date)
5. save_signal_snapshot(session, signal_date, rows, overwrite=force)
6. commit + 打印统计
```

## 边界处理

| 输入 | 行为 |
|------|------|
| `etf_pool=[]` | 返回 `[]`；save_signal_snapshot 写 0 行 |
| 价格历史 < lookback+skip+1 | 该 ETF → `WATCH`，score=None, rank=None；落库 |
| 价格历史全 None（数据缺失） | 全部 WATCH；落库 |
| 同 (date, etf_code) 已存在 | `overwrite=False` 跳过（返回 inserted/total 统计）；`overwrite=True` 更新 |
| pool 包含 DB 不存在的 code | 价格历史为空 → WATCH；落库 score=None（不抛错，让 CLI 决定如何提示） |
| top_n > len(etf_pool) | 全部 BUY |
| top_n <= 0 | raise ValueError |

## 测试策略

- **test_compute_signals_top_n**：5 只 ETF → 前 2 个 BUY，其余 HOLD
- **test_compute_signals_with_watch**：1 只 ETF 历史不足 → WATCH，rank=None
- **test_compute_signals_empty_pool**：返回 `[]`
- **test_compute_signals_uses_momentum**：mock compute_momentum_scores 验证调用参数
- **test_compute_signals_orders_by_rank**：返回按 rank 升序
- **test_compute_signals_quantize**：score 量化到 6 位
- **test_compute_signals_top_n_exceeds_pool**：pool 2 只 + top_n=5 → 全 BUY
- **test_compute_signals_invalid_top_n**：top_n=0 / 负数 → ValueError
- **test_compute_signals_input_not_mutated**：输入 price_history 不变
- **test_compute_signals_ties**：两个 ETF 同分 → 同 rank（来自 rank_scores）
- **test_compute_signals_single_etf**：pool 1 只 → 1 个 BUY
- **test_compute_signals_score_none_rank_none**：WATCH 的 row 字段
- **test_save_signal_snapshot_inserts**：mock session 验证 add 调用
- **test_save_signal_snapshot_skip_existing**：overwrite=False 跳过
- **test_save_signal_snapshot_overwrite**：overwrite=True 更新
- **test_save_signal_snapshot_empty_rows**：不调 session.add
- **test_save_signal_snapshot_none_score**：score=None 写入 NULL
- **test_save_signal_snapshot_quantize**：score 6 位小数
- **test_save_signal_snapshot_commit**：commit 调用一次
- **test_cli_run_happy_path**：mock 全部依赖；assert 写入行数
- **test_cli_run_missing_args**：argparse 退出码 2
- **test_cli_run_force_flag**：--force → overwrite=True
- **test_cli_show_no_data**：DB 空 → 友好提示

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| 价格历史加载慢（pool 大、lookback 长） | CLI 单 pool 不超过 50 只，每只 < 300 个 close，毫秒级 |
| 同 (date, etf_code) 重复 | overwrite=False 默认跳过；--force 显式覆盖 |
| `momentum_score` 精度损失 | 显式 quantize(Decimal("0.000001"))；落库前断言 |
| rank 跳号（competition ranking 1,1,3,4） | 复用 rank_scores 行为；不重新实现 |
| pool 包含 DB 不存在的 code | price_history 为空 → WATCH；不抛错 |
| top_n 大于 pool 长度 | 全部 BUY，行为可预测 |

## 不在本 change 范围

- 实时盘中信号（每分钟刷新）
- 推送 / 通知
- 多策略对比
- REST API 端点（前端 change）
- 用户自定义池管理（用 CLI --pool 显式传）
- 仓位大小建议（只输出 BUY/HOLD，不输出 weight）
- 业绩指标快照（用 BacktestRun）
