# Design: 后端 REST API

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 6 项关键决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| API 路径前缀 | `/api/v1` | 与已有 `api_v1_router` 对齐 |
| 同步 vs 异步 | 全部同步（POST /backtest 直接执行 run_backtest） | MVP 单用户、< 10 秒、不需任务队列 |
| 列表分页 | `?limit=N&offset=M`，默认 limit=50、max=500 | 1k 级别 ETF 足够；深分页不是瓶颈 |
| Decimal 序列化 | 序列化为 `string` | 金融数据保精度；前端 parseFloat 用 |
| CORS origin | `localhost:5173` + `127.0.0.1:5173`（Vite dev 默认端口） | 满足本地 dev + Docker compose |
| 错误格式 | FastAPI 默认 `{detail: ...}` | 0 额外实现；OpenAPI 原生支持 |
| 写操作 | 仅 `POST /backtest` 与 `POST /sync/*` | ETF 数据由 akshare 同步，API 不提供增删改 |
| Response 模型 | Pydantic 单独放 `app/api/v1/schemas.py` | 与 router 解耦；可被多个 router 复用 |
| 复用 | router 直接调已有 service 层（backtest engine / signals compute / sync） | 不重新实现业务逻辑 |
| 测试 | FastAPI `TestClient` + 内存 SQLite（已有 conftest） | 端到端 HTTP 行为验证 |

## 模块结构

```
backend/app/
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── router.py            # 聚合 4 个 router（改）
│       ├── etfs.py              # 扩展：list / detail / prices / count
│       ├── signals.py           # 新增：list-by-date / latest
│       ├── backtest.py          # 新增：create / list / detail / nav
│       ├── sync.py              # 新增：etfs / prices
│       └── schemas.py           # 新增：Pydantic models
├── main.py                       # 改：加 CORS middleware
└── ...

backend/tests/
├── test_api_etfs.py              # 新增
├── test_api_signals.py           # 新增
├── test_api_backtest.py          # 新增
├── test_api_sync.py              # 新增
└── test_api_schemas.py           # 新增
```

## 端点表

### `/api/v1/etfs`（扩展现有）

| 方法 | 路径 | 用途 | 关键参数 |
|------|------|------|---------|
| GET | `/etfs` | 列表（分页 + category 过滤） | `?limit=50&offset=0&category=...` |
| GET | `/etfs/{code}` | 详情 | — |
| GET | `/etfs/{code}/prices` | 日线历史 | `?start=YYYY-MM-DD&end=YYYY-MM-DD&limit=500` |
| GET | `/etfs/count` | 总数（冒烟测试用） | — |

**Response 格式**（GET /etfs）：
```json
{
  "items": [
    {"code": "510300", "name": "沪深300ETF", "market": "SH", "category": "指数"},
    ...
  ],
  "total": 800,
  "limit": 50,
  "offset": 0
}
```

### `/api/v1/signals`（新增）

| 方法 | 路径 | 用途 | 关键参数 |
|------|------|------|---------|
| GET | `/signals?date=YYYY-MM-DD` | 指定日期 snapshot | 不传 date → 最新 |
| GET | `/signals/latest` | 显式 latest（=DB MAX(date)） | — |

**Response 格式**：
```json
{
  "date": "2024-12-31",
  "rows": [
    {"etf_code": "510300", "momentum_score": "0.123456", "rank": 1, "action": "BUY"},
    ...
  ]
}
```

### `/api/v1/backtest`（新增）

| 方法 | 路径 | 用途 | Body |
|------|------|------|------|
| POST | `/backtest` | 提交新回测 | `{etf_pool, start, end, initial_cash, lookback, skip, top_n, rebalance_freq}` |
| GET | `/backtest` | 列出历史运行（分页） | `?limit=20&offset=0` |
| GET | `/backtest/{id}` | 详情 | — |
| GET | `/backtest/{id}/nav` | NAV 序列 | — |

**POST 同步执行** `run_backtest` → `save_backtest_run` → 返回完整 BacktestRun。
**Response 格式**（GET /backtest/{id}）：
```json
{
  "id": 1,
  "name": null,
  "etf_pool": ["510300", "510500"],
  "momentum_window": 252,
  "rebalance_freq": "monthly",
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "metrics": {
    "total_return": "0.200000",
    "annualized_return": "0.400000",
    "max_drawdown": "0.100000",
    "sharpe_ratio": "1.500000",
    "sortino_ratio": null,
    "calmar_ratio": "2.000000",
    "params": {...},
    "final_nav": "120000"
  },
  "created_at": "2024-12-31T10:00:00Z"
}
```

**GET /backtest/{id}/nav**：
```json
{
  "id": 1,
  "nav_series": [
    {"date": "2024-01-02", "nav": "100000"},
    ...
  ]
}
```

### `/api/v1/sync`（新增）

| 方法 | 路径 | 用途 | Body |
|------|------|------|------|
| POST | `/sync/etfs` | 同步 ETF 主数据 | — |
| POST | `/sync/prices` | 同步日线 | `{codes, start?, end?, full?}` |

**Response 格式**（POST /sync/prices）：
```json
{
  "succeeded": 3,
  "failed": 0,
  "skipped": 0
}
```

## Pydantic Schemas

```python
# app/api/v1/schemas.py

class ETFPydantic(BaseModel):
    code: str
    name: str
    market: str
    category: str | None
    
    @classmethod
    def from_orm(cls, etf: ETF) -> "ETFPydantic":
        return cls(code=etf.code, name=etf.name, market=etf.market, category=etf.category)


class DailyPricePydantic(BaseModel):
    code: str
    date: date
    open: str   # Decimal → str
    high: str
    low: str
    close: str
    volume: int


class SignalRowPydantic(BaseModel):
    etf_code: str
    momentum_score: str | None
    rank: int | None
    action: str


class SignalSnapshotPydantic(BaseModel):
    date: date
    rows: list[SignalRowPydantic]


class BacktestRequestPydantic(BaseModel):
    etf_pool: list[str]
    start: date
    end: date
    initial_cash: str  # Decimal → str
    lookback: int = 252
    skip: int = 21
    top_n: int = 5
    rebalance_freq: str = "monthly"  # "monthly" | "quarterly"


class NavPointPydantic(BaseModel):
    date: date
    nav: str


class NavSeriesPydantic(BaseModel):
    id: int
    nav_series: list[NavPointPydantic]


class ListResponsePydantic(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

## CORS 配置

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 错误处理

- **404**：`raise HTTPException(status_code=404, detail="ETF not found")`
- **422**：Pydantic 自动校验（请求体格式错误、日期格式错误）
- **500**：`@app.exception_handler(Exception)` 兜底（可选，FastAPI 默认会返回 500 + traceback）

## 数据流（POST /backtest）

```
Client → POST /api/v1/backtest {etf_pool, start, end, ...}
  ↓
1. Pydantic 校验请求体
2. 从 DB 读 daily_prices（每只 ETF 在 [start-lookback-skip, end] 的历史）
3. 构造 price_history dict
4. 调 run_backtest(BacktestParams, price_history)  ← 纯函数
5. 调 save_backtest_run(session, params, result)  ← 写 ORM
6. 返回 BacktestRun JSON（含 metrics + etf_pool + 期间信息）
```

## 边界处理

| 输入 | 行为 |
|------|------|
| `limit < 1` 或 `> 500` | clamp 到 [1, 500] |
| `offset < 0` | clamp 到 0 |
| `etf_pool=[]` | 422（BacktestParams 校验） |
| 某只 ETF DB 无数据 | 422（详细说明缺哪几只） |
| `start > end` | 422 |
| `date` 格式错误 | 422（FastAPI/Pydantic 自动） |
| 信号日期无 snapshot | 返回 200 + `{date, rows: []}` |
| BacktestRun id 不存在 | 404 |

## 测试策略

每 router 一个 test file：

- `test_api_etfs.py`：
  - test_list_etfs_empty
  - test_list_etfs_pagination
  - test_list_etfs_category_filter
  - test_list_etfs_limit_clamp
  - test_get_etf_detail
  - test_get_etf_not_found_404
  - test_get_etf_prices_date_range
  - test_get_etf_prices_default_limit
  - test_etfs_count_smoke

- `test_api_signals.py`：
  - test_signals_latest_no_data → 200 + 空 rows
  - test_signals_by_date
  - test_signals_by_date_not_found → 200 + 空 rows
  - test_signals_explicit_latest

- `test_api_backtest.py`：
  - test_post_backtest_happy_path
  - test_post_backtest_invalid_pool_empty
  - test_post_backtest_insufficient_data
  - test_get_backtest_list
  - test_get_backtest_detail
  - test_get_backtest_detail_not_found
  - test_get_backtest_nav
  - test_get_backtest_nav_not_found

- `test_api_sync.py`：
  - test_post_sync_etfs
  - test_post_sync_prices
  - test_post_sync_prices_with_dates

- `test_api_schemas.py`：
  - test_decimal_serialized_as_string
  - test_backtest_request_defaults
  - test_etf_from_orm

合计 ≥ 25 个测试。

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| 同步 POST /backtest 阻塞太久 | 限制 etf_pool ≤ 50、end - start ≤ 5 年；超限返回 422 |
| Decimal 精度损失 | 全部序列化为 string；前端 parse 后用 toFixed 还原 |
| 价格历史加载慢 | query 加 `(date < end).limit(lookback+skip+1 + 1)`；索引已建 |
| BacktestRun.metrics 嵌套 JSON 序列化 | 用 Pydantic model + jsonable_encoder |
| CORS 错误 | 明确 allow_origins；OPTIONS 预检由 CORSMiddleware 自动处理 |
| 测试 client 慢 | TestClient 已用 requests-style，同步执行够快 |

## 不在本 change 范围

- 鉴权 / 登录 / 多用户
- WebSocket 实时推送
- 限流 / 配额
- Cursor 分页
- API 版本化（除 v1 prefix 外）
- GraphQL / tRPC
- 写操作：ETF 增删改
- 异步数据库驱动
- 任务队列
- API 文档自定义（OpenAPI 自动生成）
