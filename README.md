# etf-momentum

A 股 ETF 动量策略系统。回测 + 实时信号监控。

## 项目结构

- `backend/` — FastAPI + SQLAlchemy + Alembic + akshare 数据同步
- `frontend/` — Vite + React + TypeScript + shadcn/ui
- `openspec/` — OpenSpec 配置与变更追踪
- `spec/` — 项目级 Spec（requirements / design / tasks / devlog / structure）
- `docker-compose.yml` — 一键启动后端 + 前端
- `Makefile` — Docker Compose 便捷命令

## 快速启动（Docker Compose）

### 前置条件

- Docker 20.10+
- Docker Compose v2（`docker compose version` 验证）
- macOS / Linux 推荐；Windows 推荐 WSL2

### 启动

```bash
make up          # 后台启动 backend + frontend
make logs        # 查看日志
make ps          # 查看运行状态
```

服务启动后：

- 前端：http://localhost:5173
- 后端：http://localhost:8000（`/docs` 查看 Swagger）

### 首次启动必须：初始化数据库

容器启动后数据库为空，需要执行迁移与（可选）数据同步：

```bash
# 1. 创建表结构
docker compose exec backend uv run alembic upgrade head

# 2. (可选) 拉取全市场 ETF 主数据
docker compose exec backend uv run python -m app.data.sync etfs

# 3. (可选) 拉取指定 ETF 的历史行情
docker compose exec backend uv run python -m app.data.sync prices --codes 510300,510500
```

### 验证

```bash
make verify      # 运行 scripts/verify-docker.sh：config + 三端点 curl
```

### 常用命令

```bash
make up              # 启动所有服务
make down            # 停止容器（保留 volume 与数据）
make logs            # tail 日志
make ps              # 列出运行服务
make rebuild         # 重建镜像（无缓存）
make shell-backend   # 进入 backend bash
make shell-frontend  # 进入 frontend sh
make clean           # 停止容器并删除 volume（数据丢失！）
```

### 数据持久化

SQLite 数据库保存在 Docker named volume `etf-momentum-db`，路径 `/app/data/etf_momentum.db`。
`make down` 不删 volume；`make clean` 删除 volume（含数据）。

### 本地开发（无 Docker）

如需绕过 Docker 直接本地开发：

```bash
# Backend
cd backend && uv sync --extra dev && uv run uvicorn app.main:app --reload

# Frontend（另一终端）
cd frontend && pnpm install && pnpm dev
```

## 文档

- 项目级 Spec：`spec/`
- 后端细节：`backend/README.md`
- 前端细节：`frontend/README.md`
- OpenSpec 变更记录：`openspec/changes/archive/`

## 里程碑

见 `spec/tasks.md`。
