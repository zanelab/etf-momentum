# Implementation Plan: 后端 FastAPI 脚手架

## Prerequisites
- [x] 确认 Python 3.11+ 可用（`uv python list` 显示 cpython-3.11.15）
- [x] 确认 uv 已安装（`uv --version` → 0.11.7）

## Project Skeleton
- [x] 创建 `backend/` 子目录：`backend/app/`、`backend/app/api/`、`backend/tests/`
- [x] 在 `backend/` 下创建空文件 `app/__init__.py`、`app/api/__init__.py`、`tests/__init__.py`

## Dependency Management (uv)
- [x] 在 `backend/` 下创建 `pyproject.toml`，声明项目元数据与依赖
- [x] 添加依赖：fastapi、uvicorn[standard]、pytest、httpx
- [x] 执行 `uv sync` 生成 `.venv/` 与 `uv.lock`（fastapi 0.138.1, uvicorn 0.49.0, pytest 9.1.1, httpx 0.28.1）

## FastAPI Application
- [x] 创建 `backend/app/main.py`，定义 FastAPI 实例与 lifespan
- [x] 注册健康检查路由 `GET /health`（独立模块 `backend/app/api/health.py`）
- [x] 在 `main.py` 中 include 业务路由前缀 `/api/v1`，并预留下属路由文件的占位（`backend/app/api/v1/__init__.py`、`backend/app/api/v1/router.py`）
- [x] 在 `app/main.py` 中暴露 `app` 对象供 uvicorn 引用

## Tests
- [x] 在 `backend/tests/` 创建 `test_health.py`，使用 `fastapi.testclient.TestClient`
- [x] 断言 `GET /health` 返回 200 与 `{"status":"ok"}`
- [x] 在 `pyproject.toml` 中配置 pytest，使 `uv run pytest` 可直接运行

## Documentation
- [x] 在 `backend/` 下创建 `README.md`，包含：
  - 项目简介
  - 安装步骤（`uv sync`）
  - 启动命令（`uv run uvicorn app.main:app --reload`）
  - 测试命令（`uv run pytest`）
  - 目录结构图

## Verification
- [x] 执行 `uv sync` 安装依赖，无报错
- [x] 执行 `uv run uvicorn app.main:app --port 8765`（后台），确认启动日志
- [x] `curl http://localhost:8765/health` 返回 `{"status":"ok"}`
- [x] `curl http://localhost:8765/docs` 返回 Swagger HTML
- [x] `curl http://localhost:8765/redoc` 返回 ReDoc HTML
- [x] 执行 `uv run pytest` 全绿（4 passed）
- [x] 运行 TDD 验证脚本：`speccoding-tdd.sh verify app/api/health.py`（PASS）
