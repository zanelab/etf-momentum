# Spec: akshare-real-data

---

## 1. 概述

- **变更名称**: akshare-real-data
- **日期**: 2026-06-30
- **目标**: 接入 akshare 真实数据源，删除所有 mock/fixture 数据，Docker 容器化部署

---

## 2. 数据源切换

### 2.1 删除清单

| 删除项 | 路径 |
|--------|------|
| 所有 fixture CSV | `backend/data/fixtures/`（整个目录，47 个 CSV 文件） |
| FixtureSource | `backend/app/data_sources/fixture.py` |
| Fixture 生成脚本 | `backend/scripts/generate_fixtures.py` |
| Fixture 测试 | `backend/tests/test_fixture_source.py` |
| Portfolio mock | `backend/app/services/portfolio_mock.py` |
| Portfolio 现金测试 | `backend/tests/test_portfolio_cash.py` |
| FIXTURES_DIR 环境变量 | `__init__.py` 中相关逻辑 |

### 2.2 数据源改造

**文件**: `backend/app/data_sources/__init__.py`

```python
def make_source(name: Optional[str] = None) -> MarketDataSource:
    selected = (name or os.environ.get("ETF_DATA_SOURCE", "akshare")).lower()
    # 移除 "fixture" 分支，只保留 "akshare"
    if selected == "akshare":
        inner = AkShareSource()
        src = CachedSource(inner, engine=get_engine())
    else:
        raise ValueError(f"Unknown data source: {selected!r}. Valid: 'akshare'.")
    _cache[selected] = src
    return src
```

**文件**: `backend/app/data_sources/akshare_source.py`

改动：
- 移除 `__init__` 的 `fixtures_dir: Optional[Path] = None` 参数
- 移除 `self._fallback = FixtureCSVSource(...)` 赋值
- 移除 `_fallback` 相关所有逻辑（`history()`、`snapshot()`、`all_etf_entries()` 中的 fallback 分支）
- 移除 `from app.data_sources.fixture import FixtureCSVSource` import
- 移除 `_import_akshare()` lazy import 外的 try/except（改为直接 import akshare）
- 保留重试逻辑 `retry_with_backoff`

### 2.3 缓存策略

**文件**: `backend/app/data_sources/cache.py`

`CachedSource` key 生成加入时间维度：
- 历史数据（start < today-1）：永久缓存，key = `(code, start, end, fields)`
- 当日数据：TTL = 3600 秒（1小时），key = `(code, date, "spot")`

实际实现：在 `CachedSource.get()` 中判断 `end >= date.today()` 则查 TTL。

### 2.4 ETF 代码归一化

`all_etf_entries()` 返回的代码通过 `normalize_etf_code()` 归一化为 `"XXXXXX.XSHG"` 或 `"XXXXXX.XSHE"` 格式。

沪市判断：6 位数字以 `51`、`52`、`50`、`58` 开头 → `.XSHG`
深市判断：6 位数字以 `15`、`16` 开头 → `.XSHE`
其他：默认 `.XSHG`

---

## 3. Portfolio 系统

### 3.1 数据库 Schema

**文件**: `backend/app/db.py`（或新建 `backend/app/models/portfolio.py`）

```sql
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,       -- "510300.XSHG"
    name TEXT NOT NULL,              -- "华夏沪深300ETF"
    shares INTEGER NOT NULL,         -- 持有份额（手）
    cost_price REAL NOT NULL,        -- 成本价（元）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Portfolio Service

**新文件**: `backend/app/services/portfolio.py`

```python
from app.db import get_engine
from app.models.portfolio import Portfolio

def get_all_holdings() -> list[Portfolio]:
    """从数据库读取所有持仓。"""
    with get_engine().connect() as conn:
        results = conn.execute(
            select(Portfolio).order_by(Portfolio.code)
        ).fetchall()
        return list(results)

def upsert_holding(code: str, name: str, shares: int, cost_price: float) -> None:
    """插入或更新一条持仓。"""
    with get_engine().connect() as conn:
        existing = conn.execute(
            select(Portfolio).where(Portfolio.code == code)
        ).fetchone()
        if existing:
            conn.execute(
                update(Portfolio).where(Portfolio.code == code).values(
                    name=name, shares=shares, cost_price=cost_price,
                    updated_at=func.now()
                )
            )
        else:
            conn.execute(
                insert(Portfolio).values(
                    code=code, name=name, shares=shares, cost_price=cost_price
                )
            )
        conn.commit()

def delete_holding(code: str) -> None:
    """删除一条持仓。"""
    with get_engine().connect() as conn:
        conn.execute(delete(Portfolio).where(Portfolio.code == code))
        conn.commit()
```

### 3.3 API 端点

**文件**: `backend/app/api/portfolio.py`（新文件）

```
GET    /api/portfolio            → list[PortfolioResponse]
POST   /api/portfolio            → PortfolioResponse  (body: PortfolioCreate)
PUT    /api/portfolio/{code}     → PortfolioResponse  (body: PortfolioUpdate)
DELETE /api/portfolio/{code}     → 204 No Content
```

**Schema**:
```python
class PortfolioResponse(BaseModel):
    code: str
    name: str
    shares: int
    cost_price: float
    updated_at: datetime

class PortfolioCreate(BaseModel):
    code: str
    name: str
    shares: int
    costs_price: float  # 拼写 costs 是错的，用 cost_price

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    shares: Optional[int] = None
    cost_price: Optional[float] = None
```

### 3.4 持仓页面（前端新页面）

**新页面**: `/settings/portfolio`（或 `/portfolio`）

功能：
1. 展示当前持仓列表（code、name、shares、cost_price）
2. 「添加持仓」按钮 → 弹窗表单（code 输入 + name 自动补全 + shares + cost_price）
3. 每行「编辑」「删除」按钮
4. 空状态：「暂无持仓，请添加您的第一个 ETF」
5. ETF code 输入时调用 `GET /api/market/etf-list` 自动补全 name

**组件**: `frontend/src/pages/PortfolioSettingsPage.tsx`
**Hook**: `frontend/src/api/hooks.ts` 新增 `usePortfolio`、`useUpsertHolding`、`useDeleteHolding`

### 3.5 调用方改造

以下文件将 `from app.services.portfolio_mock import get_mock_portfolio` 替换为 `from app.services.portfolio import get_all_holdings`：

| 文件 | 改动 |
|------|------|
| `backend/app/services/signals.py` | `get_mock_portfolio()` → `get_all_holdings()` |
| `backend/app/services/screening.py` | 同上 |
| `backend/app/services/today.py` | 同上 |

---

## 4. Docker 部署

### 4.1 Dockerfile（后端）

**路径**: `Dockerfile`

```dockerfile
FROM python:3.12-slim AS builder

RUN pip install uv
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN uv pip install --system -r /tmp/requirements.txt

COPY backend/ /app/

FROM python:3.12-slim
RUN pip install uv
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### 4.2 Dockerfile.frontend（前端）

**路径**: `Dockerfile.frontend`

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

### 4.3 nginx.conf（前端）

**路径**: `frontend/nginx.conf`

```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }
}
```

### 4.4 docker-compose.yml

**路径**: `docker-compose.yml`

```yaml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - etf-data:/app/data
    environment:
      - ETF_DATA_SOURCE=akshare
      - DATABASE_URL=sqlite:///./data/etf.db
    networks:
      - etf-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - etf-net
    restart: unless-stopped

volumes:
  etf-data:

networks:
  etf-net:
    driver: bridge
```

### 4.5 .dockerignore

**路径**: `.dockerignore`

```
__pycache__
*.pyc
.git
.gitignore
node_modules
dist
*.md
.openspec
spec
.env
*.log
```

---

## 5. 后端测试改造

### 5.1 删除测试

- `backend/tests/test_fixture_source.py` — 删除
- `backend/tests/test_portfolio_cash.py` — 删除

### 5.2 conftest.py 改造

移除：
- `FIXTURES_DIR` fixture
- `make_source("fixture")` 相关 fixture
- `reset_source_cache()` 调用

保留：
- `make_source("akshare")` 默认 fixture（mock akshare 调用）

### 5.3 新增测试

**文件**: `backend/tests/test_portfolio_db.py`

```python
def test_get_all_holdings_empty(db_conn):
    """空数据库返回空列表。"""
    assert get_all_holdings() == []

def test_upsert_and_get(db_conn):
    """upsert 后能读到正确数据。"""
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 10000, 3.85)
    holdings = get_all_holdings()
    assert len(holdings) == 1
    assert holdings[0].code == "510300.XSHG"
    assert holdings[0].shares == 10000

def test_upsert_updates_existing(db_conn):
    """相同 code 的 upsert 更新而非重复插入。"""
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 10000, 3.85)
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 20000, 4.00)
    holdings = get_all_holdings()
    assert len(holdings) == 1
    assert holdings[0].shares == 20000
    assert holdings[0].cost_price == 4.00

def test_delete_holding(db_conn):
    """delete 后列表中不再出现。"""
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 10000, 3.85)
    delete_holding("510300.XSHG")
    assert get_all_holdings() == []
```

### 5.4 akshare 测试改造

`test_akshare_source.py` 中 mock 策略：直接 patch `akshare.fund_etf_hist_em` 和 `akshare.fund_etf_spot_em`，不依赖 `akshare_source._import_akshare`。

---

## 6. 前端改动

### 6.1 新增页面

| 页面 | 路径 | 功能 |
|------|------|------|
| PortfolioSettingsPage | `src/pages/PortfolioSettingsPage.tsx` | 持仓配置 CRUD |

### 6.2 API 路由注册

`backend/app/main.py` 中注册 `/api/portfolio` 路由：

```python
from app.api.portfolio import router as portfolio_router
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])
```

---

## 7. 实施检查点

| 检查点 | 验证方式 |
|--------|----------|
| fixture 目录已删除 | `ls backend/data/fixtures/` 返回不存在 |
| `make_source()` 默认返回 akshare | 启动后 `GET /health` 不报 DataSource 错误 |
| portfolio API 可读写 | `POST /api/portfolio` + `GET /api/portfolio` |
| Docker build 成功 | `docker-compose build` 无报错 |
| Docker compose up 成功 | `docker-compose up -d` + `curl http://localhost:8000/health` |
| 后端测试通过 | `uv run pytest -q` |
| 前端测试通过 | `npm test` |

---

## 8. 依赖变更

### 8.1 requirements.txt 变更

移除：
- （无直接依赖，fixture 是代码层面的）

新增：
- `akshare`（如果尚未在 requirements-realtime.txt 中）

### 8.2 前端依赖

无新增依赖。