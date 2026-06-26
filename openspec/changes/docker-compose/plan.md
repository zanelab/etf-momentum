# Implementation Plan: Docker Compose 本地启动

## Prerequisites
- [x] 切换到 feature/docker-compose 分支
- [x] 确认 host 已安装 Docker 20.10+ 与 Compose v2（实测 29.3.1 + v5.1.1）
- [x] 确认 backend + frontend 代码在 main 分支已就位

## Infrastructure Files
- [x] `docker-compose.yml`（项目根目录）：backend / frontend / etf-net / etf-db / backend-venv / frontend-node-modules
- [x] `backend/Dockerfile`：基于 `python:3.11-slim`，装 uv，`uv sync --frozen --extra dev`，CMD uvicorn reload
- [x] `backend/.dockerignore`：排除 `.venv/`、`__pycache__/`、`.pytest_cache/`、`*.db`、`.env` 等
- [x] `frontend/Dockerfile`：基于 `node:24-alpine`，corepack + pnpm 11，`pnpm install --frozen-lockfile`，CMD vite dev --host
- [x] `frontend/.dockerignore`：排除 `node_modules/`、`dist/`、`.vite/`、`*.tsbuildinfo` 等
- [x] `frontend/.npmrc`：`minimum-release-age=0`（pnpm 11 dev 镜像）
- [x] 根 `Makefile`：up / down / logs / ps / rebuild / shell-backend / shell-frontend / verify / clean / help
- [x] `scripts/verify-docker.sh`：bash 脚本，chmod +x，校验 config + 启动后 curl 三个端点

## compose 配置细节
- [x] backend 服务：build `./backend`、ports 8000:8000、volumes 子目录挂载 + backend-venv + etf-db、env DATABASE_URL、networks etf-net
- [x] frontend 服务：build `./frontend`、ports 5173:5173、volumes 子目录挂载 + frontend-node-modules、env VITE_API_BASE_URL + CHOKIDAR_USEPOLLING、depends_on backend、networks etf-net
- [x] 顶层 volumes: etf-db / backend-venv / frontend-node-modules（各自 name）
- [x] 顶层 networks: etf-net (name: etf-momentum-net)

## Dockerfile 配置细节
- [x] backend Dockerfile WORKDIR=/app，先 COPY pyproject.toml + uv.lock，再 `uv sync --frozen --extra dev`，再 COPY . .，EXPOSE 8000
- [x] frontend Dockerfile WORKDIR=/app，先 COPY package.json + pnpm-lock.yaml + .npmrc，再 `pnpm install --frozen-lockfile`（env: PNPM_CONFIG_MINIMUM_RELEASE_AGE=0 / PNPM_CONFIG_DANGEROUSLY_ALLOW_ALL_BUILDS=true），再 COPY . .，EXPOSE 5173

## Makefile 配置细节
- [x] `.PHONY` 列出所有 target
- [x] 每个 target 调用 `docker compose` 对应子命令

## 验证脚本
- [x] `scripts/verify-docker.sh` 内容：config 校验 + up -d --build + 等待 /health 60s + curl 三端点
- [x] `chmod +x scripts/verify-docker.sh`

## Validation
- [x] `docker compose config --quiet` → 退出码 0
- [x] `docker compose build` → 两镜像构建成功（backend + frontend）
- [x] `docker compose up -d` → 两服务 Up
- [x] `curl localhost:8000/health` → `{"status":"ok"}`
- [x] `curl localhost:8000/api/v1/etfs/count` → `{"count":1}`（含测试行，数据从 volume 恢复）
- [x] `curl -I localhost:5173/` → HTTP 200
- [x] `docker compose exec backend uv run alembic upgrade head` → 迁移成功
- [x] `docker compose down` → 容器停止；volume 保留
- [x] `docker compose up -d` 再次启动 → 数据保留（named volume 验证通过）
- [x] `docker compose exec backend uv run pytest` → 41/41 通过

## Documentation
- [x] 根 `README.md` 增补「快速启动（Docker Compose）」章节：前置条件、make up、首次迁移、常用命令、数据持久化
- [x] `backend/README.md` 增补「Docker」章节：Dockerfile 说明 + 容器内 CLI 用法
- [x] `frontend/README.md` 增补「Docker」章节：Dockerfile + .npmrc + bind mount HMR 说明

## Acceptance Check
- [x] 逐条对照 `proposal.md` 的 13 项 Acceptance Criteria，全部满足
- [x] 逐条对照 `spec.md` 的 12 个 Requirement 至少一个 Scenario 通过
