# Implementation Plan: 动量因子计算模块

## Prerequisites
- [x] 切换到 feature/momentum-factor 分支
- [x] 确认 backend 目录存在，数据模型 + akshare sync 已就位
- [x] 确认 Python 3.11+ 与 uv 可用

## Dependencies
- [x] 无新增运行时依赖（仅用 stdlib `decimal.Decimal`）
- [x] 确认 `backend/pyproject.toml` 无需更新

## Module Structure
- [x] `app/factors/__init__.py` 创建空包文件
- [x] `app/factors/__init__.py` 从 `app.factors.momentum` re-export 三个公开函数

## Core Implementation
- [x] `app/factors/momentum.py` 定义 `_validate_closes(closes, lookback, skip) -> bool` 辅助函数
  - [x] 处理 None / 空 list → False
  - [x] 处理长度不足 → False
  - [x] 处理非 Decimal 元素 → False
  - [x] 处理 close <= 0 → False
- [x] `app/factors/momentum.py` 定义 `compute_momentum_score(closes, lookback=252, skip=21) -> Decimal | None`
  - [x] 走 `_validate_closes` 校验，失败返 None
  - [x] 计算 `closes[-skip-1] / closes[-skip-1-lookback] - 1`，全部 Decimal 算术
  - [x] 不 quantize，保留完整精度
- [x] `app/factors/momentum.py` 定义 `compute_momentum_scores(price_history, lookback=252, skip=21) -> dict[str, Decimal | None]`
  - [x] 对 dict 中每个 code 调用 `compute_momentum_score`
  - [x] 返回新 dict，不修改入参
- [x] `app/factors/momentum.py` 定义 `rank_scores(scores) -> list[tuple[str, int | None, Decimal | None]]`
  - [x] 拆分有效分数 / None 两组
  - [x] 用 Python sorted 降序（reverse=True）保持稳定性
  - [x] 遍历时按 competition ranking 跳号赋 rank
  - [x] None 列表追加 `[(code, None, None), ...]`
  - [x] 输入 dict 顺序在 sorted 后仍作为同分 tiebreaker（依赖 sorted 稳定性）

## Testing
- [x] `tests/test_momentum.py` 创建
- [x] `test_compute_momentum_score_basic`：手算预期值（280 个 close，1.20/1.00 - 1 = 0.20）
- [x] `test_compute_momentum_score_insufficient_history`：长度 = skip+lookback → None
- [x] `test_compute_momentum_score_min_length`：长度 = skip+lookback+1 → 有效分数
- [x] `test_compute_momentum_score_empty_list`：空 list → None
- [x] `test_compute_momentum_score_none_input`：None 入参 → None
- [x] `test_compute_momentum_score_invalid_zero_or_negative`：含 0 / 负数 → None
- [x] `test_compute_momentum_score_float_input`：含 float → None（不静默 cast）
- [x] `test_compute_momentum_score_custom_window`：lookback=60, skip=5 → 用对应索引
- [x] `test_compute_momentum_scores_batch`：dict 批量，部分 None 部分有效
- [x] `test_compute_momentum_scores_empty_dict`：空 dict → {}
- [x] `test_rank_scores_basic_order`：3 个不同分数 → 1,2,3
- [x] `test_rank_scores_tie_competition_ranking`：2 同分 + 1 较低 → 1,1,3（跳号）
- [x] `test_rank_scores_tie_uses_input_order`：同分时按原 dict 顺序
- [x] `test_rank_scores_with_nones`：有效 + None → 有效排名，None 末尾 rank=None
- [x] `test_rank_scores_all_none`：全 None → 全部末尾
- [x] `test_rank_scores_empty_dict`：{} → []
- [x] `test_rank_scores_negative_last`：正 + 负混合 → 负收益排最后但仍有 rank

## TDD Verification
- [x] 写完 17 个测试后运行 pytest 全部通过

## Build & Runtime Verification
- [x] `cd backend && uv run pytest` → 全部通过（58/58：原有 41 + 新增 17）
- [x] `cd backend && uv run python -c "from app.factors import compute_momentum_score, rank_scores; print(compute_momentum_score([__import__('decimal').Decimal('1.0')]*273 + [__import__('decimal').Decimal('1.2')]))"` → `0.2`

## Documentation
- [x] `backend/README.md` 增补「动量因子」章节：
  - 12-1 公式说明
  - `lookback` / `skip` 参数含义
  - 三个函数的 API 用法示例
  - 三条设计决策说明（同分并列、None 末尾、异常价格 None）
  - 「不在本 change 范围」说明（不写 signal_snapshots、不做回测）

## Acceptance Check
- [x] 逐条对照 `proposal.md` 的 13 项 Acceptance Criteria，全部满足
- [x] 逐条对照 `spec.md` 的 8 个 Requirement 至少一个 Scenario 通过