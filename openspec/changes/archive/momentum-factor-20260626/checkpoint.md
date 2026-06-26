# Checkpoint

**写入时间**: 2026-06-26T07:41:28Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: momentum-factor
**分支**: feature/momentum-factor
**父分支**: main
**Plan 进度**: 0/49

## 未完成的 Plan 项

```
4:- [ ] 切换到 feature/momentum-factor 分支
5:- [ ] 确认 backend 目录存在，数据模型 + akshare sync 已就位
6:- [ ] 确认 Python 3.11+ 与 uv 可用
9:- [ ] 无新增运行时依赖（仅用 stdlib `decimal.Decimal`）
10:- [ ] 确认 `backend/pyproject.toml` 无需更新
13:- [ ] `app/factors/__init__.py` 创建空包文件
14:- [ ] `app/factors/__init__.py` 从 `app.factors.momentum` re-export 三个公开函数
17:- [ ] `app/factors/momentum.py` 定义 `_validate_closes(closes, lookback, skip) -> bool` 辅助函数
18:  - [ ] 处理 None / 空 list → False
19:  - [ ] 处理长度不足 → False
20:  - [ ] 处理非 Decimal 元素 → False
21:  - [ ] 处理 close <= 0 → False
22:- [ ] `app/factors/momentum.py` 定义 `compute_momentum_score(closes, lookback=252, skip=21) -> Decimal | None`
23:  - [ ] 走 `_validate_closes` 校验，失败返 None
24:  - [ ] 计算 `closes[-skip-1] / closes[-skip-1-lookback] - 1`，全部 Decimal 算术
25:  - [ ] 不 quantize，保留完整精度
26:- [ ] `app/factors/momentum.py` 定义 `compute_momentum_scores(price_history, lookback=252, skip=21) -> dict[str, Decimal | None]`
27:  - [ ] 对 dict 中每个 code 调用 `compute_momentum_score`
28:  - [ ] 返回新 dict，不修改入参
29:- [ ] `app/factors/momentum.py` 定义 `rank_scores(scores) -> list[tuple[str, int | None, Decimal | None]]`
```

## 最近修改的文件

```
10d84cd chore(state): mark code_pushed=true
52d98c2 chore(state): record merge phase progress
f3d8383 Merge feature/docker-compose: Docker Compose for backend + frontend dev environment
a6b9762 chore(archive): complete docker-compose change
e9c4906 feat: Docker Compose for backend + frontend dev environment
```
