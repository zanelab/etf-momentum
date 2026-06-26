# Proposal: 后端 FastAPI 脚手架

## What
在 `backend/` 目录下建立 FastAPI 项目的最小可运行骨架，作为后续业务模块（数据同步、回测引擎、信号计算）的基础设施。

具体包含：
- FastAPI 应用入口与生命周期管理（lifespan）
- 路由结构占位（`/health`、`/api/v1/...` 前缀预留）
- 健康检查端点 `GET /health`，返回 `{status: "ok"}`
- 依赖管理使用 `uv`，提供 `pyproject.toml` 与 `uv.lock`
- 基础项目目录结构：`backend/app/`、`backend/tests/`
- `README.md` 描述启动命令与项目结构

## Why
当前 `backend/` 为空目录，缺少可启动的 FastAPI 应用。后续每个业务模块（回测、信号、数据同步）都将依赖这个骨架作为基础。提早建立脚手架可以让后续 change 专注于业务逻辑而非基础设施搭建。

## Scope
- [x] backend
- [ ] frontend

## Acceptance Criteria
- [ ] `backend/pyproject.toml` 存在，使用 uv 管理依赖
- [ ] `backend/app/main.py` 提供 FastAPI 应用实例，启动后监听 8000 端口
- [ ] `GET /health` 返回 200 与 `{"status":"ok"}`
- [ ] `GET /docs` 与 `GET /redoc` 可访问 OpenAPI 文档
- [ ] `backend/tests/` 包含对 `/health` 的最小测试，`pytest` 全绿
- [ ] `backend/README.md` 说明启动命令（`uv sync`、`uv run uvicorn ...`）与项目结构
- [ ] 目录结构与 `spec/design.md` 中的「目录布局」一致

## Status
- [x] 提案已确认
