# Spec: 动量因子计算模块

## ADDED Requirements

### Requirement: 单只 ETF 动量分数计算
`compute_momentum_score(closes, lookback=252, skip=21)` 返回 12-1 动量，纯函数不读不写 DB。

#### Scenario: 标准 12-1 动量数值正确
- Given `closes` 列表共 280 个 Decimal，其中 `closes[-274] = Decimal('1.00')`，`closes[-22] = Decimal('1.20')`
- When 调用 `compute_momentum_score(closes)`
- Then 返回 `Decimal('0.20')`（即 `(1.20 / 1.00) - 1`）

#### Scenario: 历史数据不足返回 None
- Given `closes` 列表长度 = `skip + lookback = 273`
- When 调用 `compute_momentum_score(closes)`
- Then 返回 `None`（不抛 IndexError）

#### Scenario: 长度刚好满足返回分数
- Given `closes` 列表长度 = `skip + lookback + 1 = 274`
- When 调用 `compute_momentum_score(closes)`
- Then 返回有效 Decimal（不返回 None）

#### Scenario: 空输入 / None 输入返回 None
- Given `closes = []` 或 `closes = None`
- When 调用 `compute_momentum_score(closes)`
- Then 返回 `None`

#### Scenario: 含异常价格返回 None
- Given `closes` 列表中 `closes[-22] = Decimal('0')` 或 `Decimal('-1.5')`
- When 调用 `compute_momentum_score(closes)`
- Then 返回 `None`（与数据不足同等处理）

#### Scenario: 含 float 类型返回 None
- Given `closes` 列表含 Python `float` 而非 `Decimal`
- When 调用 `compute_momentum_score(closes)`
- Then 返回 `None`（不静默 cast）

#### Scenario: 自定义窗口参数
- Given `closes` 列表长度充足
- When 调用 `compute_momentum_score(closes, lookback=60, skip=5)`
- Then 使用对应窗口计算：`closes[-6] / closes[-66] - 1`

### Requirement: 批量 ETF 动量分数计算
`compute_momentum_scores(price_history, lookback=252, skip=21)` 对 dict 中每个 code 调用单只版本。

#### Scenario: 批量 dict 部分有效
- Given `price_history = {"510300": [...280 足够...], "510500": [...100 不足...]}`
- When 调用 `compute_momentum_scores(price_history)`
- Then 返回 `{"510300": Decimal("0.20"), "510500": None}`

#### Scenario: 空 dict 输入
- Given `price_history = {}`
- When 调用 `compute_momentum_scores(price_history)`
- Then 返回 `{}`

### Requirement: 排名函数（并列同名次）
`rank_scores(scores)` 按分数降序返回 `[(code, rank, score)]`，同分并列，None 末尾。

#### Scenario: 不同分数依次排名
- Given `scores = {"a": Decimal("0.20"), "b": Decimal("0.10"), "c": Decimal("0.05")}`
- When 调用 `rank_scores(scores)`
- Then 返回 `[("a", 1, Decimal("0.20")), ("b", 2, Decimal("0.10")), ("c", 3, Decimal("0.05"))]`

#### Scenario: 同分并列同名次跳号
- Given `scores = {"a": Decimal("0.10"), "b": Decimal("0.10"), "c": Decimal("0.05")}`
- When 调用 `rank_scores(scores)`
- Then 返回 `[("a", 1, Decimal("0.10")), ("b", 1, Decimal("0.10")), ("c", 3, Decimal("0.05"))]`（competition ranking 风格）

#### Scenario: 同分时输入顺序作 tiebreaker
- Given `scores = {"a": Decimal("0.10"), "b": Decimal("0.10")}`（按插入顺序 a 在前）
- When 调用 `rank_scores(scores)`
- Then 第一个元素是 `("a", 1, Decimal("0.10"))`（Python sorted 稳定）

#### Scenario: None 分数排在末尾
- Given `scores = {"a": Decimal("0.10"), "b": None, "c": Decimal("0.05")}`
- When 调用 `rank_scores(scores)`
- Then 返回 `[("a", 1, Decimal("0.10")), ("c", 2, Decimal("0.05")), ("b", None, None)]`

#### Scenario: 全 None 输入
- Given `scores = {"a": None, "b": None}`
- When 调用 `rank_scores(scores)`
- Then 返回 `[("a", None, None), ("b", None, None)]`

#### Scenario: 空 dict 输入
- Given `scores = {}`
- When 调用 `rank_scores(scores)`
- Then 返回 `[]`

#### Scenario: 负收益排最后但仍在有效段
- Given `scores = {"a": Decimal("0.20"), "b": Decimal("-0.05"), "c": Decimal("0.10")}`
- When 调用 `rank_scores(scores)`
- Then 返回 `[("a", 1, ...), ("c", 2, ...), ("b", 3, Decimal("-0.05"))]`

### Requirement: Decimal 全程无浮点
所有计算与中间结果使用 `Decimal`，不引入 `float`。

#### Scenario: 类型校验
- Given 任意输入
- When 调用 `compute_momentum_score` 或 `rank_scores`
- Then 返回值类型为 `Decimal` 或 `None`；不存在 `float`

### Requirement: pytest 测试覆盖
backend/tests/test_momentum.py 覆盖三个函数所有分支（无需 DB fixture）。

#### Scenario: pytest 全部通过
- Given backend 目录运行 `uv run pytest`
- When 收集所有 `tests/test_*.py`
- Then 全部通过；退出码 0

### Requirement: README 增补动量因子小节
backend/README.md 新增「动量因子」章节，说明 12-1 公式、参数含义、API 用法、设计决策。

#### Scenario: README 含 API 用法示例
- Given 阅读 `backend/README.md`
- When 查找「动量因子」章节
- Then 含 `compute_momentum_score` / `compute_momentum_scores` / `rank_scores` 调用示例，以及「同分并列」「None 末尾」「异常价格返回 None」三条设计决策说明