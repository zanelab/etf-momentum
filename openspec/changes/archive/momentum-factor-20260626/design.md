# Design: 动量因子计算模块

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 4 项关键决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 窗口参数 | `lookback=252, skip=21` 交易日 | 12-1 动量经典定义；252 ≈ 1 年交易日，21 ≈ 1 个月「skip」避开短期反转；业界 / AQR / Carhart 标准 |
| 计算原语 | 纯函数，不读 DB 不写 DB | 与数据层解耦，单测无需 DB；后续回测引擎 / 实时信号模块都能复用 |
| 数据类型 | `Decimal`，不量化 | 与 DailyPrice.Numeric(10,4) 同类型族；不预设下游存储精度，调用方按需 `quantize(Decimal('0.0001'))` |
| 同分排名 | **并列同名次**（competition ranking），输入顺序作稳定次序 | 标准学术风格 `1,2,2,4`；Python `sorted` 稳定性保证同分时的确定性 |
| None 分数 | 保留在列表末尾，`rank=None`，不占名次槽 | UI 一目了然哪些 ETF 无数据；调用方仍可遍历到 |
| 异常价格 | `<= 0` 视为脏数据 → 返回 None 静默跳过 | 与「数据不足」同等处理；纯函数不抛异常中断批量计算 |
| 模块组织 | `app/factors/` 新包，未来可扩展其他因子 | 与 `app/data/` 同级；按计算原语分目录，便于后续 value / quality 因子加入 |
| API 形态 | 三个函数：`compute_momentum_score`（单只）/ `compute_momentum_scores`（批量 dict）/ `rank_scores`（排名） | 单只是基础原语，批量是常用入口，排名是 UI 消费形态；职责单一 |
| 不写 signal_snapshots | 本 change 仅算不算入 DB | 持久化责任放在后续「实时信号计算与排名」change，避免本 change 涉及 DB 写入事务 |

## 模块结构

```
backend/app/
└── factors/
    ├── __init__.py             # 暴露 compute_momentum_score / compute_momentum_scores / rank_scores
    └── momentum.py             # 三个核心函数 + 内部 _validate_closes 辅助
```

未来 `app/factors/` 包内可加 `value.py` / `quality.py` / `__init__.py` 统一 re-export。

## 函数签名

```python
from decimal import Decimal

def compute_momentum_score(
    closes: list[Decimal],
    lookback: int = 252,
    skip: int = 21,
) -> Decimal | None:
    """12-1 动量：(closes[-skip-1] / closes[-skip-1-lookback]) - 1

    返回 None 的情况：
    - closes 为空 / None
    - len(closes) < skip + lookback + 1（数据不足）
    - 越界访问（理论上已由长度检查覆盖；额外保险）
    - 任一有效 close <= 0（异常价格）
    """


def compute_momentum_scores(
    price_history: dict[str, list[Decimal]],
    lookback: int = 252,
    skip: int = 21,
) -> dict[str, Decimal | None]:
    """对 dict 中每个 code 调用 compute_momentum_score，返回新 dict"""


def rank_scores(
    scores: dict[str, Decimal | None],
) -> list[tuple[str, int | None, Decimal | None]]:
    """按分数降序排名；同分并列同名次（competition ranking）；None 排末尾，rank=None

    返回 [(code, rank, score)]，rank 从 1 起；同分跳号；None 项 (code, None, None) 排末位
    """
```

## 12-1 动量公式

```
momentum(t) = close(t - skip - 1) / close(t - skip - 1 - lookback) - 1
```

举例（默认参数 `lookback=252, skip=21`）：
- `closes[-22]` = 12 个月前的最近一根收盘价（跳过最近 21 个交易日，即「skip」）
- `closes[-22-252]` = `closes[-274]` = 24 个月前的收盘价
- ratio = `closes[-22] / closes[-274]`；再 -1 得到动量

## 排名算法

```
1. 把 scores 拆为 (有效 dict) 与 (None 列表)
2. sorted_items = sorted(有效 dict.items(), key=lambda kv: kv[1], reverse=True)
   # Python sorted 是稳定的，相同 score 保持原 dict 插入顺序
3. 遍历 sorted_items，跳号赋 rank：
   rank = 1
   prev_score = None
   for i, (code, score) in enumerate(sorted_items):
       if i == 0:
           code 的 rank = 1
       elif score == prev_score:
           code 的 rank = 同上一个 rank（并列）
       else:
           rank = i + 1  # 跳过被并列占用的名次
           code 的 rank = rank
       prev_score = score
4. None 列表追加：[(code, None, None), ...]
```

验证示例：`{a: 0.1, b: 0.1, c: 0.05, d: None, e: None}`
→ `[(a, 1, 0.1), (b, 1, 0.1), (c, 3, 0.05), (d, None, None), (e, None, None)]`

## 异常值处理

```python
def _validate_closes(closes, lookback, skip):
    if closes is None or not closes:
        return False
    if len(closes) < skip + lookback + 1:
        return False
    # 计算所需索引处的 close
    recent = closes[-skip - 1]
    past = closes[-skip - 1 - lookback]
    if not isinstance(recent, Decimal) or not isinstance(past, Decimal):
        return False
    if recent <= 0 or past <= 0:
        return False
    return True
```

Decimal 类型校验确保调用方传对的类型，避免隐式 float 转 Decimal 时精度丢失。

## 测试策略

- **test_compute_momentum_score**：手算预期值的几条 fixture（如 `closes = [Decimal('1.0')] * 273 + [Decimal('1.2')]` → 0.2）
- **test_compute_momentum_score_edge_cases**：
  - 空 list → None
  - None 输入 → None
  - 长度刚好 = skip + lookback + 1 → 正常返回
  - 长度 = skip + lookback → None
  - 含 0 / 负数 → None
  - 含 float（不是 Decimal）→ None
- **test_compute_momentum_scores**：批量 dict 场景，部分 None 部分有效
- **test_rank_scores_basic**：3 只不同分数 → `[(A,1),(B,2),(C,3)]`
- **test_rank_scores_tie**：2 同分 → `[(A,1),(B,1),(C,3)]`
- **test_rank_scores_with_nones**：1 有效 + 2 None → 有效排名 1，None 末尾
- **test_rank_scores_empty**：空 dict → []
- **test_rank_scores_all_none**：全 None → 全部末尾（rank=None）
- **test_rank_scores_negative**：正负混合，负收益排最后

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| Decimal 算术性能 | 252 个元素以下无压力；后续如要 5000+ 时间窗口，再考虑向量化 |
| 调用方误传 float | `_validate_closes` 校验类型，返回 None（不静默 cast） |
| 越界 IndexError | 长度判断先于索引访问 |
| 排名不稳定（同名次顺序） | 利用 Python `sorted` 稳定性，输入 dict 顺序作 tiebreaker |
| 同分名次跳号 vs 不跳号 | 文档明确：competition ranking（标准学术） |

## 不在本 change 范围

- 多窗口（1/3/6/12 月同时计算）—— 后续如需要可加 `compute_momentum_multi_window`
- winsorize / clip 异常值 —— MVP 假设数据干净
- 行业中性化 / 风险因子调整 —— 学术延伸
- 写入 `signal_snapshots` —— 后续「实时信号计算与排名」change
- 回测引擎集成 —— 后续「回测引擎」change
- 前端展示 —— 后续 UI change