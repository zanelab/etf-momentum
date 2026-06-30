# Proposal: akshare-real-data

## 基本信息

- **变更名称**: akshare-real-data
- **分支**: feature/akshare-real-data
- **父分支**: main (5d23c34)
- **日期**: 2026-06-30
- **用户决策**:
  1. 数据源: akshare（删除所有 mock 数据）
  2. 回测粒度: 日级
  3. 部署形态: Docker

---

## 1. 背景与目标

当前项目使用 CSV fixture 模拟市场数据（`data/fixtures/` 目录下 47 个 ETF 的历史 CSV），portfolio 使用硬编码 mock（`portfolio_mock.py`）。

本次变更目标：
1. **接入 akshare 真实数据源**，删除所有 CSV fixture 数据
2. **删除 portfolio mock**，替换为真实持仓数据（数据库）
3. **Docker 部署**，提供标准化的容器化运行环境

---

## 2. 范围

### 2.1 数据源切换（akshare）

**删除**:
- `backend/data/fixtures/` 整个目录（47 个 ETF CSV 文件）
- `backend/app/data_sources/fixture.py`（`FixtureCSVSource`）
- `backend/app/data_sources/fixture.py` 相关测试
- `backend/scripts/generate_fixtures.py`（fixture 生成脚本）
- `FIXTURES_DIR` 环境变量及相关逻辑

**保留**:
- `backend/app/data_sources/akshare_source.py`（`AkShareSource`）— 已实现，清理 fallback 逻辑
- `backend/app/data_sources/__init__.py` — 移除 `fixture` source 选项，只保留 `akshare`
- `backend/app/data_sources/cache.py`（`CachedSource`）— akshare 缓存层保留

**改造**:
- `AkShareSource` 移除 `_fallback` 参数（不再 fallback 到 fixture）
- `make_source()` 默认改为 `akshare`，移除 `fixture` 分支
- 移除 `FIXTURES_DIR` 环境变量支持

### 2.2 Portfolio Mock 删除

**删除**:
- `backend/app/services/portfolio_mock.py`

**改造**:
- 持仓数据从数据库 `portfolios` 表读取（schema 需新增）
- `app/services/portfolio.py`（新建）：从 DB 读取真实持仓，替代 `get_mock_portfolio`
- 涉及持仓读取的所有调用方（`signals.py`、`screening.py` 等）需改造

### 2.3 Docker 部署

**新增文件**:
- `Dockerfile`（后端 Python FastAPI）
- `docker-compose.yml`（后端 + 前端 + SQLite DB 持久化）
- `.dockerignore`
- `Dockerfile.frontend`（前端 Node 构建）

**目录结构**:
```
etf-momentum/
├── Dockerfile          # 后端
├── Dockerfile.frontend # 前端
├── docker-compose.yml  # 编排
└── .dockerignore
```

**环境变量**:
- `ETF_DATA_SOURCE=akshare`（固定，不可切换）
- `DATABASE_URL=sqlite:///./data/etf.db`（容器内路径）
- 前端 `VITE_API_BASE_URL` 指向后端容器地址

### 2.4 测试调整

- 删除所有使用 fixture source 的测试（`test_fixture_source.py` 等）
- 更新 `conftest.py` 中的 `make_source` fixture，默认返回 `akshare`
- 保留 akshare 相关测试（`test_akshare_source.py`），mock `akshare` 调用
- 数据库持仓测试新增（测试 portfolio service 读 DB）

---

## 3. 关键设计决策

### 3.1 akshare ETF 列表获取

`AkShareSource.all_etf_entries()` 使用 `akshare.fund_etf_spot_em()` 获取全市场 ETF 列表（代码 + 名称）。这是已实现的，不需要改动。

### 3.2 数据缓存策略

akshare 每次调用做缓存（`CachedSource`），缓存 key = `(code, start, end, fields)`，TTL = 1 天。避免重复拉取同一区间的历史数据。

### 3.3 Portfolio 数据库 schema

```sql
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,          -- ETF 代码，如 "510300.XSHG"
    name TEXT NOT NULL,          -- ETF 名称
    shares INTEGER NOT NULL,     -- 持有份额
    cost_price REAL NOT NULL,    -- 成本价
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 Docker 网络

- `docker-compose.yml` 定义 `network: etf-net`
- 后端容器名: `etf-backend`，端口 `8000:8000`
- 前端容器名: `etf-frontend`，端口 `3000:3000`
- 前端通过 `http://etf-backend:8000` 访问后端 API

---

## 4. 已知限制

- akshare 为第三方数据源，网络波动可能导致拉取失败；`CachedSource` 缓存层提供一定保护
- `fund_etf_hist_em` 接口返回历史日线数据，实测稳定（参考 speccoding skill `akshare-etf-data.md`）
- fund_etf_spot_em 返回全市场 ETF 列表，包含部分已退市或流动性极差的品种，筛选层需注意

---

## 5. 非范围（后续变更处理）

- 回测功能（`backtest.py`）使用 akshare 日线数据，后续如有粒度变更（分钟级）在独立变更中处理
- ETF 筛选逻辑（动量因子等）保持不变，只改数据源
- 飞书推送、持仓管理 UI 在后续变更中迭代

---

## 6. 成功标准

1. `ETF_DATA_SOURCE=akshare` 时，API 能返回真实市场数据（不读任何 CSV）
2. `docker-compose up` 能完整启动前后端 + 数据库
3. 后端测试 `uv run pytest -q` 全部通过（akshare 调用 mock）
4. 前端测试 `npm test` 全部通过
5. `docker-compose build` 成功，无报错