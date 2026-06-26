# Design: 回测引擎

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 4 项关键决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 权重策略 | **等权**（每只入选 ETF 拿 1/top_n 资金） | 学术标准、AQR 默认；不足 top_n 时按比例摊分剩余 |
| 调仓日规则 | MONTHLY = 「该月最后一个交易日」；QUARTERLY = 「3/6/9/12 月最后交易日」 | A 股业界惯例；与「月末效应」一致 |
| 退市 ETF | 最后有数据的一日按 close 卖出，转为现金；下个调仓日从其他 ETF 中再选 | NAV 保持连续；避免估值冻结 |
| 净值跟踪 | **每日跟踪**，用每日 close 重估持仓总市值 | max_drawdown 准确；UI 曲线完整 |
| 计算与持久化分离 | `run_backtest()` 纯函数（不读 DB）；`save_backtest_run()` 单独函数（写 ORM） | 单测只测计算逻辑；持久化 mock session |
| 数据来源 | 调用方传入 `dict[code, list[(date, Decimal)]]` | 与 akshare sync、DailyPrice ORM 解耦；可在容器外跑回测 |
| 动量复用 | 直接调用 `app.factors.momentum.compute_momentum_scores` + `rank_scores` | 不重写动量逻辑；单一事实源 |
| 业绩指标内置 | total_return / annualized_return / max_drawdown / sharpe_ratio 直接在引擎里算 | MVP 不引入独立 PerformanceTracker；后续 change 抽取 |
| NAV 精度 | 全程 `Decimal`；最终指标也 Decimal | 与 DailyPrice.Numeric(10,4) 同族；sharpe 用 `Decimal.sqrt()` (Py 3.11+) |
| 不模拟摩擦 | 无手续费、无滑点、无印花税、无分红再投资 | MVP 简化；后续可加 fee/slippage 参数 |

## 模块结构

```
backend/app/
└── backtest/
    ├── __init__.py             # re-export BacktestParams / run_backtest / BacktestResult
    ├── engine.py               # 纯计算：run_backtest + 内部辅助
    └── persistence.py          # 持久化：save_backtest_run
```

未来 `app/backtest/` 可加 `metrics.py`（独立指标计算）、`strategies/`（多策略）等。

## 类型定义

```python
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class RebalanceFrequency(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass(frozen=True)
class BacktestParams:
    etf_pool: list[str]
    start: date
    end: date
    initial_cash: Decimal
    lookback: int = 252
    skip: int = 21
    top_n: int = 5
    rebalance_freq: RebalanceFrequency = RebalanceFrequency.MONTHLY


@dataclass(frozen=True)
class RebalanceEvent:
    date: date
    scores: dict[str, Decimal | None]
    selected: list[str]
    weights: dict[str, Decimal]


@dataclass
class BacktestResult:
    nav_series: list[tuple[date, Decimal]]
    rebalance_log: list[RebalanceEvent]
    metrics: dict[str, Decimal | None]
```

## 主算法

```python
def run_backtest(params, price_history):
    # 1. Validate
    _validate_params(params, price_history)
    
    # 2. Build trading calendar (union of all dates in [start, end])
    calendar = _build_calendar(price_history, params.start, params.end)
    
    # 3. Find rebalance dates
    rebalance_dates = _find_rebalance_dates(calendar, params.rebalance_freq)
    
    # 4. State: current shares + cash
    shares: dict[str, Decimal] = {}     # code -> shares held
    cash: Decimal = params.initial_cash
    
    # 5. Iterate
    nav_series = []
    rebalance_log = []
    
    for current_date in calendar:
        # Mark-to-market for NAV (using previous holdings)
        day_close_map = _close_at(price_history, current_date)
        nav = cash + sum(shares.get(c, Decimal(0)) * day_close_map.get(c, Decimal(0))
                         for c in shares)
        nav_series.append((current_date, nav))
        
        # Rebalance?
        if current_date in rebalance_dates:
            # Score using lookback window ending at skip before current_date
            scores = _compute_scores(price_history, params, current_date)
            ranked = rank_scores(scores)
            top = [(c, r) for (c, r, s) in ranked if s is not None][:params.top_n]
            if len(top) == 0:
                continue  # skip this rebalance (no data)
            
            # Sell all at close → cash
            cash = nav
            
            # Buy equal-weight
            new_shares = {}
            weight = Decimal(1) / len(top)  # 按实际入选数摊分（不足 top_n）
            for code, _ in top:
                close = day_close_map.get(code)
                if close is None or close <= 0:
                    continue  # 该 ETF 当日无数据，跳过
                allocation = cash * weight
                new_shares[code] = allocation / close
                cash -= allocation
            
            shares = new_shares
            
            selected = list(new_shares.keys())
            weights = {c: Decimal(1) / len(selected) for c in selected} if selected else {}
            rebalance_log.append(RebalanceEvent(
                date=current_date,
                scores=scores,
                selected=selected,
                weights=weights,
            ))
    
    # 6. Metrics
    metrics = _compute_metrics(nav_series, params.initial_cash)
    
    return BacktestResult(nav_series, rebalance_log, metrics)
```

## 调仓日确定

```python
def _find_rebalance_dates(calendar, freq):
    # calendar: sorted list[date]
    by_period = {}
    for d in calendar:
        if freq == RebalanceFrequency.MONTHLY:
            key = (d.year, d.month)
        else:  # QUARTERLY
            q = (d.month - 1) // 3 + 1
            key = (d.year, q)
        if key not in by_period or d > by_period[key]:
            by_period[key] = d
    return set(by_period.values())
```

## 动量分数窗口切片

```python
def _compute_scores(price_history, params, rebalance_date):
    # 取 [rebalance_date - (lookback+skip+1) 个交易日, rebalance_date) 中的数据
    # 按 akshare sync 的「调整后」价格计算
    end_idx = _index_of(price_history, rebalance_date)  # 当日索引（不参与计算）
    # 实际用 [end_idx - skip - 1 - lookback : end_idx - skip - 1]
    ...
    return compute_momentum_scores({c: slice_series for c in params.etf_pool},
                                    lookback=params.lookback, skip=params.skip)
```

简化版：直接对每个 ETF 取该日往前 lookback+skip+1 个交易日的 closes，传给 `compute_momentum_score`。

## 业绩指标公式

| 指标 | 公式 |
|------|------|
| total_return | (final_nav / initial_cash) - 1 |
| annualized_return | (final_nav / initial_cash) ** (365 / days) - 1（days > 0） |
| max_drawdown | max over all t of (peak(t) / nav(t) - 1)，peak(t) = max nav[0..t] |
| sharpe_ratio | mean(daily_returns) / std(daily_returns) * sqrt(252)（无风险利率 = 0）；std = 0 时 None |

全部用 `Decimal` 算术；sharpe 用 `Decimal.sqrt()`（Python 3.11+）。

## 持久化

ORM 字段（已存在）：
- `id` (PK, autoincrement)
- `name` (String(128), nullable)
- `etf_pool` (JSON, list[str])
- `momentum_window` (Integer, 映射 `params.lookback`)
- `rebalance_freq` (String(16))
- `start_date`, `end_date` (Date)
- `metrics` (JSON, dict)
- `created_at` (DateTime, server_default=func.now())

```python
def save_backtest_run(session, params, result):
    final_nav = result.nav_series[-1][1] if result.nav_series else None
    metrics_json = {
        **{k: str(v) if v is not None else None for k, v in result.metrics.items()},
        # BacktestParams 完整快照放进 metrics 便于复现
        "params": {
            "lookback": params.lookback,
            "skip": params.skip,
            "top_n": params.top_n,
            "initial_cash": str(params.initial_cash),
            "final_nav": str(final_nav) if final_nav is not None else None,
        },
    }
    run = BacktestRun(
        name=None,  # 后续 UI 可加
        etf_pool=list(params.etf_pool),  # SQLAlchemy JSON 列接受 list
        momentum_window=params.lookback,
        rebalance_freq=params.rebalance_freq.value,
        start_date=params.start,
        end_date=params.end,
        metrics=metrics_json,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
```

ORM 中没有 skip / top_n / initial_cash 列；把这些放进 `metrics["params"]` JSON 字段，便于审计与复现。

## 测试策略

- **test_run_backtest_basic**：3 只 ETF 月末调仓，手算预期 NAV
- **test_run_backtest_single_etf**：单只 ETF → 全部资金进一只
- **test_run_backtest_no_rebalance**：所有 ETF 数据不足 → rebalance_log 空，NAV 平直
- **test_run_backtest_short_window**：日期范围 < 273 天 → 不调仓
- **test_rebalance_frequency_monthly_vs_quarterly**：同一段日期，MONTHLY 触发 ≥ QUARTERLY
- **test_metrics_total_return**：已知 final/initial → 手算
- **test_metrics_annualized**：1 年 +50% → annualized 0.5
- **test_metrics_max_drawdown**：NAV 曲线先涨 1.2 后跌 0.6 → max_dd = 0.5
- **test_metrics_sharpe**：已知 daily returns → 手算
- **test_price_insufficient_skip_rebalance**：中途某 ETF 数据断 → rebalance_log 少一条，NAV 连续
- **test_delisted_etf_sold_to_cash**：中间 ETF 数据终止 → 卖出转现金
- **test_persistence_save_backtest_run**：mock session 验证 BacktestRun 字段
- **test_persistence_metrics_serialized**：metrics dict 正确 JSON 化
- **test_top_n_lte_pool**：top_n > 实际可用数 → 全部入选

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| Decimal.sqrt 性能 | 回测通常 < 10 年；Decimal sqrt 比 float 慢但精度高；如性能瓶颈可换 Decimal → float |
| 回测期间 ETF 退市 | 已决策「卖出转现金」，逻辑清晰 |
| 调仓日 ETF 无 close | 跳过该次调仓，不强制买入 |
| 大量 Decimal 内存 | NAV 每日一条，10 年 ≈ 2500 条，几十 KB；可接受 |
| 业绩指标 sharpe 在 0 std 时返回 None | 文档明确语义（无波动率无法算 sharpe） |
| 跨调仓日「交易日历」漂移 | 用 union of dates，按日期序迭代，简单可靠 |

## 不在本 change 范围

- 业绩指标独立模块（下次 change 抽出）
- 手续费 / 滑点 / 印花税 / 分红再投资
- 多因子策略（如动量 + 价值）
- 行业 / 风险中性化
- 借贷 / 做空
- CVX 优化权重
- 指数基准（沪深 300）对比
- 任务调度（cron）
- 回测进度持久化（中断恢复）
- 前端 Backtest UI（后续前端 change）