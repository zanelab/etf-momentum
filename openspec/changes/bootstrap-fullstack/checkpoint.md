# Checkpoint

**写入时间**: 2026-06-28T08:52:56Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: bootstrap-fullstack
**分支**: feature/bootstrap-fullstack
**父分支**: main
**Plan 进度**: 7/72

## 未完成的 Plan 项

```
19:- [ ] 2.1 [后端][TDD] 创建 `backend/app/main.py`：FastAPI 实例 + CORS + `/api/health`
20:- [ ] 2.2 [后端][TDD] 创建 SQLModel 模型：`StaticPool`、`ThemeKeyword`、`StrategyParam`（`backend/app/models/`）
21:- [ ] 2.3 [后端] 创建 `backend/app/db.py`：engine + session + 初始化逻辑
22:- [ ] 2.4 [后端] 创建 `backend/app/seed.py`：首次启动时种入默认数据（静态池 ~145 只、主题词典 17 类、策略参数）
23:- [ ] 2.5 [后端][TDD] 实现 `GET/POST/PUT/DELETE /api/configs/pool`（`backend/app/api/configs.py`）
24:- [ ] 2.6 [后端][TDD] 实现 `GET/PUT /api/configs/themes`
25:- [ ] 2.7 [后端][TDD] 实现 `GET/PUT /api/configs/strategy`
26:- [ ] 2.8 [后端][TDD] 配置 API 单测：`backend/tests/test_configs.py`
30:- [ ] 3.1 [后端] 定义 `MarketDataSource` Protocol（`backend/app/data_sources/base.py`）
31:- [ ] 3.2 [后端][TDD] 实现 `FixtureCSVSource`（`backend/app/data_sources/fixture.py`）
32:- [ ] 3.3 [后端] fixture 生成脚本 `backend/scripts/generate_fixtures.py`：为 10 只代表性 ETF 生成 2 年日级 CSV（GBM 模拟 + 真实 ETF 量级噪声）
33:- [ ] 3.4 [后端] 生成 fixture 文件，写入 `backend/data/fixtures/`，提交到 git
34:- [ ] 3.5 [后端][TDD] 数据源单测：`backend/tests/test_fixture_source.py`
38:- [ ] 4.1 [后端][TDD] 定义 `StrategyParams`、`ScreeningContext` Pydantic 模型（`backend/app/services/types.py`）
39:- [ ] 4.2 [后端][TDD] 迁移 `filter_etfs()` 签名：`filter_etfs(as_of, static_pool, dynamic_pool, themes, params, market) -> list[str]`
40:- [ ] 4.3 [后端][TDD] 迁移双均线过滤逻辑（`backend/app/services/screening.py`）
41:- [ ] 4.4 [后端][TDD] 迁移动量评分逻辑（加权对数回归 + R²）
42:- [ ] 4.5 [后端][TDD] 迁移行业分散选取逻辑（含兜底补齐）
43:- [ ] 4.6 [后端][TDD] 单测覆盖：无目标、行业分散、动量异常值、成交量过滤、防御 ETF 排除
44:- [ ] 4.7 [后端] 对照测试：3 组 fixture 输入，原 `main.py`（带 shim 适配）vs 新实现，结果一致
```

## 最近修改的文件

```
8a5648d chore: start bootstrap-fullstack change
7529e74 chore: bootstrap SpecCoding workflow and fullstack architecture
```
