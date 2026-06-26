# Design: Docker Compose 本地启动

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 4 项关键决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Python 镜像 | `python:3.11-slim` + 现场装 uv | 官方镜像、依赖成熟；现场 `pip install uv` 简单可靠 |
| SQLite 存储 | Named volume `etf-db` 挂到 `/app/data` | 容器重建不丢数据；host 端无路径依赖；后续切 PG 时可改 env |
| 前端模式 | Vite dev server + HMR | 与本地开发体验一致；bind mount 源码 → 即时反映修改 |
| 验证策略 | 冒烟 shell 脚本（非 CI） | 开发者本地手动验证；不阻塞 PR；CI 集成后续单独 change |

## 服务拓扑

```
┌─────────────── etf-net (bridge) ───────────────┐
│                                                │
│  ┌─────────────┐         ┌─────────────────┐  │
│  │  backend    │         │   frontend      │  │
│  │  :8000      │         │   :5173         │  │
│  │             │         │                 │  │
│  │  uvicorn    │         │  vite dev       │  │
│  │  --reload   │         │  --host 0.0.0.0 │  │
│  │             │         │                 │  │
│  │  bind mount │         │  bind mount     │  │
│  │  ./backend  │         │  ./frontend     │  │
│  │  → /app     │         │  → /app         │  │
│  │             │         │                 │  │
│  │  vol: etf-db│         │                 │  │
│  │  → /app/data│         │                 │  │
│  └─────────────┘         └─────────────────┘  │
│         ▲                                        │
│         │ proxy: VITE_API_BASE_URL=http://backend:8000
└─────────┼────────────────────────────────────────┘
          │
   host: localhost:8000 (backend)
         localhost:5173 (frontend)
```

## Dockerfile 设计

### backend/Dockerfile

```dockerfile
FROM python:3.11-slim

# 安装 uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# 先 COPY 依赖文件，利用 layer cache
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev

# 再 COPY 源码（dev 阶段以 bind mount 覆盖）
COPY . .

# 数据目录
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

注意：`uv sync --frozen` 严格锁版本（CI/团队一致）；`--extra dev` 装 pytest 等开发依赖。

### frontend/Dockerfile

```dockerfile
FROM node:24-alpine

# 启用 corepack 激活 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# 先 COPY 依赖文件
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]
```

## docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    container_name: etf-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app                # 源码热更新
      - etf-db:/app/data              # SQLite 持久化
    environment:
      - DATABASE_URL=sqlite:////app/data/etf_momentum.db
    networks:
      - etf-net

  frontend:
    build: ./frontend
    container_name: etf-frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app               # 源码 + HMR
      - /app/node_modules             # 匿名 volume 防止 host 覆盖容器内 node_modules
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - etf-net

volumes:
  etf-db:
    name: etf-momentum-db

networks:
  etf-net:
    name: etf-momentum-net
```

## .dockerignore

### backend/.dockerignore

```
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/
.env
.env.local
*.db
*.sqlite
README.md
```

### frontend/.dockerignore

```
node_modules/
dist/
.vite/
*.tsbuildinfo
vite.config.d.ts
vite.config.js
README.md
```

## Makefile

```makefile
.PHONY: up down logs ps rebuild shell-backend shell-frontend verify

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

rebuild:
	docker compose build --no-cache

shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

verify:
	./scripts/verify-docker.sh
```

## 验证脚本（scripts/verify-docker.sh）

`docker compose config` 语法校验 + 提示用户手动 curl 三个端点（不强制）；不阻塞本地流程。

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[verify-docker] docker compose config..."
docker compose config --quiet && echo "✓ config valid"

echo ""
echo "[verify-docker] bring up (if not running)..."
docker compose up -d --build

echo "[verify-docker] waiting for backend health (max 30s)..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null; then
        echo "✓ /health OK"
        break
    fi
    sleep 1
done

echo "[verify-docker] /api/v1/etfs/count:"
curl -s http://localhost:8000/api/v1/etfs/count
echo ""

echo "[verify-docker] frontend root:"
curl -sf -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5173/
```

## 数据持久化与迁移

- 首次启动时 `etf_momentum.db` 不存在，需手动初始化：
  ```bash
  docker compose exec backend uv run alembic upgrade head
  ```
- 后续启动数据自动保留（volume 持久化）
- README 增补首次启动必须步骤

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| bind mount 与 `.venv` / `node_modules` 冲突 | `.dockerignore` + 容器内建一次；host 修改不触发重建 |
| Windows bind mount 性能差 | 仅 macOS / Linux 文档化；Windows 推荐 WSL2 |
| akshare 需外网 | 文档明确：容器内 `python -m app.data.sync etfs` 需 host 网络通畅 |
| HMR 在某些 OS 不工作 | 前端 `--host 0.0.0.0` + 端口 5173 暴露，浏览器手动访问 |
| 端口冲突 | README 提示可改 `compose.yaml` 端口映射 |

## 不在本 change 范围

- 生产 multi-stage build（distroless / 最终精简镜像）
- 反向代理 / nginx / TLS
- GitHub Actions CI 集成
- 数据初始化（自动 akshare 同步）
- 数据库备份 / 恢复脚本
