# Spec: Docker Compose 本地启动

## ADDED Requirements

### Requirement: docker-compose.yml 编排两服务
根目录 `docker-compose.yml` 定义 `backend` 与 `frontend` 两个 service，共享 `etf-net` 网络。

#### Scenario: 顶层结构
- Given 项目根目录存在 `docker-compose.yml`
- When 检查文件
- Then 包含 `services:`、`networks:`、`volumes:` 三个顶层键；services 含 `backend` 与 `frontend`

#### Scenario: 共享网络
- Given backend 与 frontend 服务都声明 `networks: [etf-net]`
- When 容器启动
- Then 两者可互相通过 service 名解析（`backend:8000` / `frontend:5173`）

### Requirement: backend Dockerfile 基于 python:3.11-slim + uv
`backend/Dockerfile` 使用官方 Python slim 镜像，安装 uv 后通过 `uv sync` 装依赖。

#### Scenario: 基础镜像与依赖安装
- Given `backend/Dockerfile` 第一行 `FROM python:3.11-slim`
- And `RUN pip install --no-cache-dir uv`
- And `RUN uv sync --frozen --extra dev`
- When 镜像构建
- Then `uv` 与全部 Python 依赖（含 dev extras）安装成功

#### Scenario: 启动命令
- Given Dockerfile 末尾 `CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]`
- When 容器启动
- Then uvicorn 监听 0.0.0.0:8000，源码改动触发 reload

### Requirement: frontend Dockerfile 基于 node:24-alpine + pnpm
`frontend/Dockerfile` 使用 node alpine 镜像，通过 corepack 启用 pnpm。

#### Scenario: 基础镜像与依赖安装
- Given `frontend/Dockerfile` 第一行 `FROM node:24-alpine`
- And `RUN corepack enable && corepack prepare pnpm@latest --activate`
- And `RUN pnpm install --frozen-lockfile`
- When 镜像构建
- Then `pnpm` 与全部 frontend 依赖安装成功

#### Scenario: 启动 Vite dev server
- Given Dockerfile 末尾 `CMD ["pnpm", "dev", "--host", "0.0.0.0"]`
- When 容器启动
- Then Vite 监听 0.0.0.0:5173，支持外部访问

### Requirement: 源码 bind mount 实现热更新
compose 中 backend 与 frontend 都将源码 bind mount 到容器内。

#### Scenario: backend 源码热更新
- Given compose 中 `./backend:/app`
- When host 修改 `backend/app/main.py`
- Then uvicorn reload 自动重启，无需重建镜像

#### Scenario: frontend HMR
- Given compose 中 `./frontend:/app` 加 anonymous volume `/app/node_modules`
- When host 修改 `frontend/src/App.tsx`
- Then Vite HMR 推送更新到浏览器

### Requirement: SQLite 持久化到 named volume
backend 服务挂载 named volume `etf-db` 到 `/app/data`，env 中 `DATABASE_URL` 指向该路径。

#### Scenario: 容器重建数据保留
- Given `etf-db` volume 存在且含数据库
- When `docker compose down` 后 `docker compose up -d`
- Then 数据库内容保留（volume 未被 `-v` 删除）

#### Scenario: 首次启动空数据库
- Given volume 首次创建
- When `docker compose up -d` 启动
- Then `/app/data/etf_momentum.db` 不存在；需手动 `alembic upgrade head`

### Requirement: 端口映射与网络可达
compose 暴露 8000（backend）与 5173（frontend）到 host。

#### Scenario: backend 端点可访问
- Given backend 容器运行
- When `curl http://localhost:8000/health`
- Then 返回 `{"status":"ok"}`

#### Scenario: frontend 端点可访问
- Given frontend 容器运行
- When `curl -I http://localhost:5173/`
- Then 返回 HTTP 200 与 HTML 头

### Requirement: VITE_API_BASE_URL 指向 backend
frontend 服务环境变量 `VITE_API_BASE_URL=http://localhost:8000`（或 backend service name）。

#### Scenario: 跨域 API 调用成功
- Given 浏览器访问 `http://localhost:5173/health`
- When 页面加载并调用 `/api/v1/etfs/count`（通过 Vite proxy 或 env）
- Then 实际请求打到 backend:8000 并返回 JSON

### Requirement: .dockerignore 排除无关文件
backend 与 frontend 各自 `.dockerignore` 排除构建无关文件。

#### Scenario: backend 镜像不含 .venv
- Given `backend/.dockerignore` 含 `.venv/`
- When `docker build` backend
- Then 镜像层不包含 host 上 `.venv/` 内容

#### Scenario: frontend 镜像不含 node_modules
- Given `frontend/.dockerignore` 含 `node_modules/`
- When `docker build` frontend
- Then 镜像层不包含 host 上 `node_modules/` 内容

### Requirement: depends_on 启动顺序
frontend 服务 depends_on backend（仅启动顺序，不等待 health）。

#### Scenario: 启动顺序
- Given `docker compose up -d`
- When 启动流程执行
- Then backend 先于 frontend 开始启动

### Requirement: docker compose config 通过
compose 文件语法与引用合法。

#### Scenario: config 校验通过
- Given 项目根目录
- When 运行 `docker compose config --quiet`
- Then 退出码 0，无错误输出

### Requirement: 验证脚本（手动冒烟）
`scripts/verify-docker.sh` 提供 `docker compose config` 校验与启动后 curl 验证。

#### Scenario: 验证脚本成功
- Given 容器已 up
- When 运行 `bash scripts/verify-docker.sh`
- Then 输出 `✓ config valid`、 `/health OK`、`{"count":0}`、 `HTTP 200`

### Requirement: Makefile 便捷命令
根目录 `Makefile` 提供 `up`、`down`、`logs`、`ps`、`rebuild`、`shell-backend`、`shell-frontend`、`verify` 命令。

#### Scenario: make up 启动
- Given 项目根目录
- When 运行 `make up`
- Then `docker compose up -d` 被调用

### Requirement: README 增补 Docker 启动章节
根 `README.md` 与 `backend/README.md` / `frontend/README.md` 增补 Docker 用法。

#### Scenario: 根 README 含 Docker 章节
- Given 阅读根 `README.md`
- When 查找「Docker 启动」
- Then 包含前置条件（DOCKER 20.10+、Compose v2）、`make up`、首次启动步骤（alembic 迁移）
