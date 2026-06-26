# Proposal: 动量因子计算模块

## What
实现经典学术 12-1 动量因子（momentum factor）的纯计算模块：

- **`app/factors/__init__.py`**：factors 包入口
- **`app/factors/momentum.py`**：核心计算
  - `compute_momentum_score(closes: list[Decimal], lookback: int = 252, skip: int = 21) -> Decimal | None`
  - `compute_momentum_scores(price_history: dict[str, list[Decimal]], ...) -> dict[str, Decimal | None]`
  - `rank_scores(scores: dict[str, Decimal]) -> list[tuple[str, int, Decimal]]`（按分数降序）
- **数据来源**：从 `daily_prices` 表读取（不动 akshare / akshare 是上一 change）
- **输出**：纯函数，输入历史价格序列，返回分数 / 排名；**不写入** `signal_snapshots`（持久化由后续「实时信号计算与排名」change 负责）

## Why
阶段 1（基础设施）已完成：数据层（SQLite + akshare 同步脚本）就绪。下一阶段（核心能力）的第一步是「如何从历史价格算出动量得分」，这是回测引擎、信号计算、回测展示 UI 共同依赖的计算原语。

将动量因子抽成纯函数模块的好处：
- 单测容易：传入历史 close 序列即可验证
- 与数据层解耦：可独立测试计算逻辑，无需 DB
- 后续 change（回测 / 信号）只需调用 `compute_momentum_score`，无需重复实现

12-1 动量是 AQR / Carhart 等学术文献标准定义，业界惯例。

## Scope
- [x] backend
- [ ] frontend

## Out of Scope（本 change 不做）
- 写入 `signal_snapshots`（后续「实时信号计算与排名」change）
- 回测引擎（后续「回测引擎」change）
- 前端展示（后续前端 change）
- 多因子合成（如动量 + 价值 + 质量）；MVP 仅动量单因子
- 行业中性化、风险中性化（学术延伸处理）
- 异常值处理（winsorize / clip）；MVP 假设数据干净

## Acceptance Criteria
- [ ] `app/factors/__init__.py` 与 `app/factors/momentum.py` 文件存在
- [ ] `compute_momentum_score(closes, lookback=252, skip=21)`：返回 `(closes[-skip-1] / closes[-skip-1-lookback]) - 1`，类型 `Decimal`
- [ ] 历史数据不足（`len(closes) < skip + lookback + 1`）时返回 `None`（不抛异常）
- [ ] 输入为空 / `None` / 越界访问时安全返回 `None`，不抛 IndexError
- [ ] `closes` 中出现 `<= 0` 的异常值时返回 `None`（与数据不足同等处理，不抛异常）
- [ ] `compute_momentum_scores(price_history, ...)`：对 dict 中每个 code 应用 `compute_momentum_score`
- [ ] `rank_scores(scores: dict[str, Decimal | None])`：按分数降序返回 `[(code, rank, score)]`，None 排到最后
- [ ] `rank_scores` 中**同分并列同名次**：分数相等时 rank 相同，**跳过被占的名次**（如 `[1, 2, 2, 4]`）；输入 dict 顺序作为同分时的稳定次序
- [ ] `rank_scores` 中**有效分数的 rank 编号从 1 起**；None 项 `(code, None, None)` 排在列表末尾，不占用名次
- [ ] Decimal 精度：计算**不量化**，保留完整精度；调用方在写入 DB 时再 `quantize(Decimal('0.0001'))`
- [ ] 计算全程使用 `Decimal`，避免浮点误差
- [ ] pytest 套件（纯函数测试，无需 DB）：
  - 已知输入的 12-1 动量数值正确（手算预期值）
  - 边界：长度刚好 = skip + lookback + 1 满足；少 1 个返回 None
  - 异常值：closes 含 0 或负数 → None
  - 空输入 / None 输入 / 全 None scores → rank_scores 返回 []
  - rank_scores 排序正确（None 在最后）
  - rank_scores 同分并列：`{a: 0.1, b: 0.1, c: 0.05}` → `[(a, 1, 0.1), (b, 1, 0.1), (c, 3, 0.05)]`
  - 负收益 ETF 排名在最后
- [ ] README 增补「动量因子」小节：12-1 公式、参数含义、API 用法、上述三条设计决策

## 设计决策（脑暴沉淀）
1. **同分排名**：并列同名次（competition ranking，标准 `1, 2, 2, 4` 风格），输入 dict 顺序作稳定次序
2. **None 分数**：保留在列表末尾，`rank=None`，不占用名次槽位
3. **Decimal 精度**：不 quantize，调用方按需量化
4. **异常价格**：`<= 0` 视为脏数据 → 返回 None 静默跳过

## Status
- [x] 提案已确认
