# Proposal: 后端 REST API

## What
为前端 Dashboard / Backtest UI / ETF 池管理 暴露 REST 端点，复用已有的 `app.backtest`、`app.signals`、`app.data` 模块。

**新增 4 个 router：**

- **`app/api/v1/etfs.py`**（扩展现有）：ETF 查询 + 日线价格
  - `GET /api/v1/etfs` — 列表（分页 + category 过滤）
  - `GET /api/v1/etfs/{code}` — 详情
  - `GET /api/v1/etfs/{code}/prices?start=...&end=...&limit=...` — 日线历史
  - `GET /api/v1/etfs/count`（保留现有冒烟测试端点）

- **`app/api/v1/signals.py`**：信号快照查询
  - `GET /api/v1/signals?date=YYYY-MM-DD` — 指定日期 snapshot（无 date 取最新）
  - `GET /api/v1/signals/latest` — 显式 latest（=DB MAX(date)）

- **`app/api/v1/backtest.py`**：回测
  - `POST /api/v1/backtest` — 提交新回测（参数 + ETF 池），同步执行 → 返回 BacktestRun JSON
  - `GET /api/v1/backtest` — 列出历史运行（按 created_at desc）
  - `GET /api/v1/backtest/{id}` — 详情（含 metrics）
  - `GET /api/v1/backtest/{id}/nav` — NAV 序列（前端画图用）

- **`app/api/v1/sync.py`**：数据同步触发（便于前端手动同步按钮）
  - `POST /api/v1/sync/etfs` — 同步 ETF 主数据（返回 upserted count）
  - `POST /api/v1/sync/prices` — 同步指定 ETF 日线

**新增基础设施：**
- **`app/api/v1/schemas.py`**：Pydantic response/request 模型
  - `ETFPydantic` / `DailyPricePydantic` / `SignalRowPydantic` / `BacktestRunPydantic`
  - `BacktestRequestPydantic`（POST body）
  - `NavPointPydantic`（NAV 序列点）
  - Decimal → str 序列化（避免 float 精度损失）
- **`app/main.py`**：加 CORS middleware（允许 `http://localhost:5173`）
- **`app/api/v1/router.py`**：聚合 4 个 router

## Why
当前只有 1 个冒烟端点 `/api/v1/etfs/count`。前端 Dashboard 需要：
- 看到今天建议买哪些 ETF（→ GET /api/v1/signals/latest）
- 选定 ETF 池做回测（→ POST /api/v1/backtest）
- 看历史业绩（→ GET /api/v1/backtest/{id} + /nav）
- 知道有哪些 ETF 可选（→ GET /api/v1/etfs）
- 看某只 ETF 走势（→ GET /api/v1/etfs/{code}/prices）

不补 API，前端只能 mock 数据；手工跑 CLI 不可持续。

## Scope
- [x] backend
- [ ] frontend（前端展示另起 change）

## Out of Scope（本 change 不做）
- 鉴权 / 登录 / 多用户（个人投资者用，本地部署）
- WebSocket 实时推送
- 限流 / 配额
- 分页 cursor（先用 offset/limit）
- API 版本化（除 v1 prefix 外不维护 v2）
- GraphQL / tRPC
- OpenAPI 文档自定义（用 FastAPI 自动生成即可）
- 异步数据库驱动（保留同步 SQLAlchemy）
- 写操作：ETF 增删改（数据由 akshare 同步，API 不提供写）

## Acceptance Criteria
- [ ] `app/api/v1/schemas.py` 存在，定义至少 6 个 Pydantic 模型
- [ ] `app/api/v1/etfs.py` 提供 4 个端点（list / detail / prices / count）
- [ ] `app/api/v1/signals.py` 提供 2 个端点（list-by-date / latest）
- [ ] `app/api/v1/backtest.py` 提供 4 个端点（create / list / detail / nav）
- [ ] `app/api/v1/sync.py` 提供 2 个端点（etfs / prices）
- [ ] Decimal 字段序列化为 string（`Decimal("0.123456")` → `"0.123456"`）
- [ ] `app/main.py` 启用 CORS 允许 `http://localhost:5173`（前端 Vite dev）
- [ ] 错误处理：404（资源不存在）、422（Pydantic 校验）、500（异常）
- [ ] `tests/test_api_*.py` 至少 25 个端点测试覆盖 happy path + 主要错误
- [ ] 现有 146 个测试（数据模型 + akshare + 动量 + 回测 + 业绩 + 实时信号）全部仍然通过
- [ ] README 增补「REST API」章节：端点表 + 1-2 个 curl 示例

## 设计决策（脑暴沉淀）
> 待 brainstorming 阶段填充

## Status
- [x] 提案已确认（2026-06-26，4 router + 12 端点，同步 POST backtest）
