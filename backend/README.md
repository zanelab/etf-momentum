# etf-momentum Backend

A 股 ETF 动量策略系统的后端服务。基于 FastAPI，使用 `uv` 管理依赖。

## 项目简介

本目录是 etf-momentum 项目的后端实现。当前阶段为最小可运行脚手架，提供：

- FastAPI 应用入口（`app/main.py`）
- 健康检查端点 `GET /health`
- 业务路由前缀占位 `/api/v1`
- 自动化测试覆盖（`pytest` + `TestClient`）

后续将在此基础上添加数据同步、回测引擎、信号计算等业务模块。

## 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 0.11+

## 安装

```bash
cd backend
uv sync --extra dev
```

这会创建 `.venv/` 虚拟环境并安装所有依赖（含 dev 工具：pytest、httpx）。

## 启动开发服务器

```bash
uv run uvicorn app.main:app --reload --port 8000
```

服务监听 `http://localhost:8000`。

- `GET /health` — 健康检查，返回 `{"status":"ok"}`
- `GET /docs` — Swagger UI
- `GET /redoc` — ReDoc

## 运行测试

```bash
uv run pytest
```

## 项目结构

```
backend/
├── app/                          # 应用代码
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   └── api/
│       ├── __init__.py
│       ├── health.py             # 健康检查路由
│       └── v1/                   # 业务 API 路由聚合
│           ├── __init__.py
│           └── router.py         # v1 路由（占位）
├── tests/                        # 测试
│   ├── __init__.py
│   └── test_health.py            # 健康检查测试
├── pyproject.toml                # 项目元数据与依赖
├── uv.lock                       # 依赖锁文件
└── README.md                     # 本文档
```

## 后续计划

- 数据同步模块（`app/data/`，接入 akshare / baostock）
- 业务 API（`app/api/v1/`）：ETF 池管理、回测、信号
- 数据库（SQLite + SQLAlchemy）
- 任务调度（每日数据更新）
