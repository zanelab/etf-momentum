# Brainstorming: akshare-real-data

---

## 1. akshare 数据源 — 深入分析

### 1.1 接口覆盖度

| 功能 | 接口 | 状态 |
|------|------|------|
| ETF 历史日线 | `fund_etf_hist_em(symbol, period="daily")` | ✅ 实测可用 |
| ETF 实时行情/列表 | `fund_etf_spot_em()` | ✅ 实测可用 |
| 指数 PE/PB | `stock_index_pe_lg(symbol="沪深300")` | ✅ 可用（非 ETF，但用于宏观信号） |
| M2 年率 | `macro_china_m2_yearly()` | ✅ 可用 |
| 10年国债 | FRED CSV `DGS10` | ✅ 无需 API key |

### 1.2 缓存策略细化

`CachedSource` 现有实现：
- Key: `(code, start_date, end_date, tuple(sorted(fields)))`
- 存储: SQLite `market_bar_cache` 表
- TTL: 未设置（永久缓存，直到手动清理）

**问题**: akshare 数据随时间更新，历史 K 线不变但最新交易日数据会变。

**决策**: 缓存分区策略
- `hist_{code}_{start}_{end}`: 历史数据（不变，永久缓存）
- `spot_{code}_{date}`: 当日快照（TTL=1小时，防止盘中数据陈旧）

实际实现：在 `CachedSource` key 中加入 `date` 维度，或在 `AkShareSource` 层处理缓存逻辑。

### 1.3 代码归一化问题

akshare 返回的 ETF 代码是 6 位数字字符串（如 `"510300"`），项目内部使用 `"510300.XSHG"` 格式。

现有 `codes.py` 中 `normalize_etf_code()` 处理转换。

**需确认**: `fund_etf_spot_em()` 返回的代码是否带交易所后缀？实测是纯 6 位数字，需在 `all_etf_entries()` 中统一加上 `.XSHG` 或 `.XSHE`。

### 1.4 fixture fallback 移除的风险

当前 `AkShareSource` 有 `_fallback = FixtureCSVSource(fixtures_dir)`，网络失败时自动降级到 CSV。

**移除 fallback 后**：
- 网络失败 → 抛出 `DataNotFoundError`
- 前端 UI 需处理「数据拉取失败」状态（error boundary）
- API 需返回有意义的 HTTP 错误（不要 500，尽量 502/504）

**决策**: 
- 不再 fallback 到 fixture
- 但保留 `AkShareSource` 自身的重试逻辑（`retry_with_backoff`，3次重试，backoff 2x）
- 网络持续失败时，API 返回 502 + 错误信息

---

## 2. Portfolio 数据库设计

### 2.1 现有调用方分析

```
portfolio_mock.py::get_mock_portfolio()
  ├── signals.py::generate_signal()  [读取持仓算 P&L]
  ├── screening.py::screen_etfs()    [读取当前持仓过滤]
  └── today.py::get_today_display()  [读取持仓算浮动盈亏]
```

### 2.2 DB Schema 设计

**方案 A: 简单单表**

```sql
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,      -- "510300.XSHG"
    name TEXT NOT NULL,             -- "华夏沪深300ETF"
    shares INTEGER NOT NULL,
    cost_price REAL NOT NULL,       -- 保留 4 位小数
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**方案 B: 持仓快照（时间机器）**

```sql
CREATE TABLE portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of DATE NOT NULL,            -- 快照日期
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    shares INTEGER NOT NULL,
    cost_price REAL NOT NULL,
    UNIQUE(as_of, code)
);
```

**决策**: 方案 A（简单单表），因为：
- 当前需求是「读取当前持仓」，不需要历史快照
- 后续变更（`etf-holdings-workflow`）会处理手动操作流程，再扩展快照

**Seed 数据**: `backend/app/seed.py` 已有 `seed_portfolio()` 函数框架，需实现：

```python
def seed_portfolio():
    """Insert initial holdings from environment or data/portfolio.json."""
    # 从 data/portfolio.json 读取，或 env 变量
```

---

## 3. Docker 部署 — 深入分析

### 3.1 多阶段构建策略

**后端 (Dockerfile)**:
```dockerfile
# Stage 1: builder
FROM python:3.12-slim AS builder
RUN pip install uv
COPY backend/requirements.txt /tmp/
RUN uv pip install --system -r /tmp/requirements.txt

# Stage 2: runtime
FROM python:3.12-slim
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY backend/ /app/
WORKDIR /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**前端 (Dockerfile.frontend)**:
```dockerfile
FROM node:20-alpine AS builder
COPY frontend/ /app/
RUN cd /app && npm install && npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
```

### 3.2 docker-compose.yml 结构

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
      - ./data:/app/data        # SQLite DB 持久化
    environment:
      - ETF_DATA_SOURCE=akshare
      - DATABASE_URL=sqlite:///./data/etf.db
    networks:
      - etf-net
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - etf-net
    restart: unless-stopped

networks:
  etf-net:
    driver: bridge
```

**注意**: 前端 `VITE_API_BASE_URL` 应为 `http://backend:8000`（容器内通信），宿主机访问用 `localhost:3000`。

### 3.3 数据持久化

- **SQLite**: 挂载 `./data:/app/data`，容器重建不丢数据
- **akshare 缓存**: 同上，SQLite 文件在 `./data/` 下
- **无需持久化**: fixture 文件（已删除）

### 3.4 健康检查

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

## 4. 测试策略

### 4.1 后端测试改造

**删除**:
- `test_fixture_source.py` — 完全删除
- `test_cached_source.py` — fixture 场景删除，需重写
- `conftest.py` 中 `FIXTURES_DIR` 相关 fixture

**保留但改造**:
- `test_akshare_source.py` — mock `akshare.fund_etf_hist_em` 和 `fund_etf_spot_em`
- `test_daily_sync.py` — mock `AkShareSource` 而非 `FixtureCSVSource`

**新增**:
- `test_portfolio_db.py` — 测试 portfolio service 读写 DB

### 4.2 Mock 策略

使用 ` unittest.mock.patch` 覆盖 `akshare.fund_etf_hist_em` 等函数：

```python
from unittest.mock import patch, MagicMock
import pandas as pd

@pytest.fixture
def mock_akshare():
    with patch("app.data_sources.akshare_source._import_akshare") as mock:
        akshare_mock = MagicMock()
        # mock return values...
        mock.return_value = akshare_mock
        yield mock
```

### 4.3 前端测试

前端测试不直接依赖数据源（API mock），不受影响。

---

## 5. 精确删除清单

### 5.1 完整删除文件/目录

```
backend/data/fixtures/           # 整个目录（47 CSV 文件）
backend/app/data_sources/fixture.py
backend/app/services/portfolio_mock.py
backend/scripts/generate_fixtures.py
backend/tests/test_fixture_source.py
backend/tests/test_portfolio_cash.py   # 依赖 portfolio_mock
```

### 5.2 需改造的文件

| 文件 | 改动 |
|------|------|
| `backend/app/data_sources/__init__.py` | 移除 `fixture` 分支，默认 `akshare` |
| `backend/app/data_sources/akshare_source.py` | 移除 `_fallback`，清理 import |
| `backend/app/data_sources/base.py` | 无改动 |
| `backend/app/services/signals.py` | `get_mock_portfolio` → `get_portfolio_from_db` |
| `backend/app/services/screening.py` | 同上 |
| `backend/app/services/today.py` | 同上 |
| `backend/app/services/portfolio.py` | 新建，从 DB 读持仓 |
| `backend/app/db.py` | 确认 `portfolio` 表 schema |
| `backend/app/seed.py` | 实现 `seed_portfolio()` |
| `backend/tests/conftest.py` | 移除 `FIXTURES_DIR` fixture |
| `backend/tests/test_akshare_source.py` | 更新 mock 策略 |

### 5.3 新增文件

```
Dockerfile
Dockerfile.frontend
docker-compose.yml
.dockerignore
frontend/nginx.conf              # 前端 Docker nginx 配置
backend/app/services/portfolio.py  # portfolio service
backend/tests/test_portfolio_db.py
```

---

## 6. 潜在陷阱

### 6.1 akshare 接口限制

- `fund_etf_hist_em` 单次查询跨度太大会超时，需在 `daily_sync.py` 中分小段拉取（每次最多 1 年）
- `fund_etf_spot_em` 返回全市场 ETF（约 800+），首次调用慢（约 5-10s），但有缓存

### 6.2 SQLite 并发写入

akshare 缓存写入使用 SQLite，FastAPI 多 worker 模式下可能有写锁竞争。

**缓解**: 
- 使用 `check_same_thread=False`
- 或限制 FastAPI 只跑 1 worker（`--workers 1`），Docker 场景够用

### 6.3 前端 API 地址

开发环境: `http://localhost:8000`
Docker 环境: `http://backend:8000`（容器内）/ `http://localhost:8000`（宿主机）

**解决**: `.env.docker` 文件，`docker-compose.yml` 注入 `VITE_API_BASE_URL`。

### 6.4 akshare 网络超时

容器内网络可能受限（如 DNS、超时），需设置合理的 timeout（`retry_with_backoff` 已处理）。

### 6.5 ETF 代码交易所后缀

`fund_etf_spot_em` 返回纯 6 位数字（如 `510300`），需归一化为 `510300.XSHG` 或 `510300.XSHE`。

**验证**: 通过 `normalize_etf_code()` 处理，但需确认沪市/深市判断逻辑（通常 51 开头沪市，15/16 开头深市）。

---

## 7. 实施顺序建议

1. **Phase 1**: Docker 骨架（Dockerfile + docker-compose），不涉及业务代码，先跑通
2. **Phase 2**: Portfolio DB 实现 + seed，删除 portfolio_mock
3. **Phase 3**: 数据源切换（删除 fixture，接入 akshare）
4. **Phase 4**: 测试改造 + CI 验证

---

## 8. 开放问题（需用户确认）

1. **Portfolio 初始数据**: 第一次启动时是否从 `data/portfolio.json` 读取初始化？还是空数据库让用户手动添加？
2. **akshare 缓存 TTL**: 历史数据永久缓存，当日数据 1 小时，是否合适？
3. **FastAPI workers**: 是否接受 `--workers 1`（单 worker，避免 SQLite 并发问题）？