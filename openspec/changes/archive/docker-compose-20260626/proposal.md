# Proposal: Docker Compose 本地启动

## What
为 etf-momentum 提供本地一键启动的 Docker Compose 编排，封装后端 (FastAPI) 与前端 (Vite dev server) 两个服务：

- **backend 服务**：`python:3.11-slim` 镜像 + uv 安装依赖；`uvicorn --reload` 启动；源码 bind mount 实现热更新；SQLite 数据库用 named volume 持久化
- **frontend 服务**：`node:24-alpine` 镜像 + pnpm 安装依赖；`vite --host 0.0.0.0` 启动 dev server；源码 bind mount 实现 HMR
- **`docker-compose.yml`**：定义两服务 + 网络 + 卷；`docker compose up` 一键启动
- **`backend/Dockerfile`** 与 **`frontend/Dockerfile`**：分别构建后端与前端镜像
- **`.dockerignore`**：避免把 `.venv`、`node_modules`、`__pycache__` 等塞进镜像
- **根目录 `Makefile`**（可选）：提供 `make up / down / logs / shell-backend` 等便捷命令
- **README 增补**：「Docker 启动」章节，记录 `docker compose up` 用法与已知端口

## Why
当前启动流程需要本地安装 Python 3.11、Node 24、uv、pnpm 四套工具链，新人 onboarding 成本高；不同 OS 的 Python/Node 行为差异也会造成「我这里能跑」的问题。

Compose 化后：
- 单一命令 `docker compose up` 拉起完整开发环境
- 团队成员环境一致，避免依赖漂移
- 数据通过 named volume 持久化，容器重建不丢数据
- 为后续 CI 集成、staging 环境奠定基础

## Scope
- [x] backend
- [x] frontend
- [x] infra（docker-compose.yml、Dockerfile、.dockerignore、Makefile）

## Out of Scope（本 change 不做）
- 生产环境镜像（multi-stage build、最小化镜像）；MVP 仅 dev 镜像
- 反向代理 / nginx / TLS；dev 阶段直接 `vite` 与 `uvicorn` 暴露端口即可
- CI 集成（GitHub Actions）；后续独立 change
- 数据初始化脚本（自动 akshare 同步）；MVP 需手动 `docker compose exec backend uv run python -m app.data.sync etfs`

## Acceptance Criteria
- [ ] `docker-compose.yml` 在项目根目录，定义 `backend` 与 `frontend` 两个 service，共享一个 `etf-net` 网络
- [ ] `backend/Dockerfile`：基于 `python:3.11-slim`，安装 `uv`，`COPY pyproject.toml uv.lock`，`uv sync`，暴露 8000 端口，启动 `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- [ ] `frontend/Dockerfile`：基于 `node:24-alpine`，启用 corepack + pnpm，`COPY package.json pnpm-lock.yaml`，`pnpm install --frozen-lockfile`，暴露 5173 端口，启动 `pnpm dev --host 0.0.0.0`
- [ ] `backend/.dockerignore` 与 `frontend/.dockerignore`：排除 `.venv`、`__pycache__`、`.pytest_cache` 等
- [ ] backend 服务 bind mount `./backend` 到 `/app`（除 `.venv`），named volume `etf-db` 持久化 SQLite
- [ ] frontend 服务 bind mount `./frontend` 到 `/app`（除 `node_modules`）
- [ ] backend depends_on frontend（仅启动顺序，无 healthcheck gating）
- [ ] `docker compose config` 验证通过（语法 / 引用）
- [ ] `docker compose up -d` 后：
  - `curl http://localhost:8000/health` 返回 `{"status":"ok"}`
  - `curl http://localhost:8000/api/v1/etfs/count` 返回 `{"count":0}`
  - `curl http://localhost:5173/` 返回 HTML
- [ ] `docker compose down -v` 后 SQLite 数据可重建（验证 volume 隔离正常）
- [ ] 根 `Makefile` 提供 `up`、`down`、`logs`、`ps`、`rebuild` 命令
- [ ] README「Docker 启动」章节说明前置条件（Docker 20.10+、Compose v2）与常用命令
- [ ] 不引入新的 Python / Node 依赖；仅基础设施变更

## Status
- [x] 提案已确认
