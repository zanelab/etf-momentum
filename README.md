# etf-momentum

> A 股 ETF 动量策略系统：参数化回测 + 实时 BUY/HOLD/WATCH 信号 + Web Dashboard。

基于 12-1 动量因子，为 A 股 ETF 池提供历史回测（6 个业绩指标）与实时调仓建议。单体应用、单机部署、单用户场景；不接券商、不做实盘。

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [Docker 常用命令](#docker-常用命令)
- [本地开发（无 Docker）](#本地开发无-docker)
- [故障排查](#故障排查)
- [文档导航](#文档导航)
- [里程碑](#里程碑)

## 功能特性

v1.0 已交付的全部业务能力：

| 能力 | 说明 | 代码定位 |
|------|------|----------|
| **12-1 动量因子** | 纯函数计算 `closes[-22] / closes[-274] - 1`，可配置 lookback / skip | `backend/app/factors/momentum.py` |
| **参数化回测引擎** | ETF 池、动量窗口、调仓频率（monthly/quarterly）、top-N 等权；纯函数 + 日历取并集 + 末日调仓 + 退市清仓 | `backend/app/backtest/engine.py` |
| **6 个业绩指标** | 年化收益、最大回撤、夏普、Sortino、Calmar（Bessel 校正 + `sqrt(252)` 年化） | `backend/app/backtest/metrics.py` |
| **实时三态信号** | BUY / HOLD / WATCH，基于最新动量排名 + 阈值；CLI + DB 持久化 | `backend/app/signals/` + `backend/app/data/signal.py` |
| **18 个 REST 端点** | 健康检查 + ETF / Pool / Signal / Backtest / Sync 全套 API + CORS | `backend/app/api/v1/` + `backend/app/api/health.py` |
| **Web Dashboard** | 4 个页面：动量看板、回测工作台、ETF 池管理、健康检查 | `frontend/src/pages/` |

完整 API schema 以 `http://localhost:8000/docs`（Swagger UI）为准。

## 快速开始

### 前置条件

- Docker 20.10+ 与 Docker Compose v2（`docker compose version` 验证）
- macOS / Linux 推荐；Windows 推荐 WSL2

### 两条首跑路径

按需选择「快速展示」或「真实数据」：

| 路径 | 适用场景 | 耗时 | 依赖网络 |
|------|---------|------|---------|
| **A. 快速展示** | 技术分享、CI、Demo 录像、断网环境 | ≈ 30 秒 | ❌ 不依赖 akshare |
| **B. 真实数据** | 个人投资、研究分析 | ≈ 2-3 分钟 | ✅ 依赖 akshare |

#### 路径 A：快速展示（推荐新用户）

```bash
# 1. 克隆与启动
git clone https://github.com/zanelab/etf-momentum.git
cd etf-momentum
make up                    # 后台启动 backend + frontend

# 2. 创建数据库表结构（首次必做）
docker compose exec backend uv run alembic upgrade head

# 3. 灌入内置演示数据（15 只 ETF × 1079 天 ≈ 16185 行日线 + 1 个 signal snapshot + 1 个示例 pool）
make seed-demo
# 输出：loaded: etfs=15 daily_prices=16185 signals=15 pool=宽基三杰

# 4. 打开浏览器
#    Dashboard（动量排名）：    http://localhost:5173/dashboard
#    回测工作台：              http://localhost:5173/backtest
#    ETF 池管理：              http://localhost:5173/pools
#    健康检查：                http://localhost:5173/health
#    Swagger UI（后端 API）：  http://localhost:8000/docs
```

> ⚠️ **演示数据仅用于系统功能演示，不构成投资建议**。演示数据来自 akshare 一次性快照（约 3 年历史），生成日期见 `backend/app/data/fixtures/demo_data.json` 的 `generated_at` 字段。

#### 路径 B：真实数据

```bash
# 1-2. 同上（克隆 + 启动 + 迁移）
git clone https://github.com/zanelab/etf-momentum.git
cd etf-momentum
make up
docker compose exec backend uv run alembic upgrade head

# 3. 同步 ETF 主数据（全市场清单，约 800+ 只，约 30 秒）
docker compose exec backend uv run python -m app.data.sync etfs

# 4. 同步若干标的的历史价格（示例：沪深300 + 中证500 + 创业板；约 1-2 分钟）
docker compose exec backend uv run python -m app.data.sync prices \
    --codes 510300,510500,159915 --full

# 5. 计算今日实时信号（写入 signal_snapshots 表）
docker compose exec backend uv run python -m app.data.signal \
    run --date $(date +%Y-%m-%d) --pool 510300,510500,159915

# 6. 打开浏览器（同路径 A）
```

**两条路径可混跑**：演示数据 + 真实数据通过 upsert 自然合并，DB 行数累加。

### 自检命令

```bash
# 后端健康
curl http://localhost:8000/health
# 期望：{"status":"ok"}

# 后端 ETF 数量（路径 A：15；路径 B：800+）
curl http://localhost:8000/api/v1/etfs/count

# 拿最新信号
curl http://localhost:8000/api/v1/signals/latest

# 前端可达
curl -I http://localhost:5173/
# 期望：HTTP/1.1 200 OK
```

## 项目结构

```
etf-momentum/
├── backend/                 # FastAPI + SQLAlchemy + akshare + pytest
├── frontend/                # Vite + React + TypeScript + shadcn/ui + vitest
├── openspec/                # OpenSpec 变更追踪与归档
│   ├── config.yaml
│   ├── specs/               # 已沉淀的长期规格（按 capability 分目录）
│   └── changes/
│       └── archive/         # 已完成变更（按日期归档）
├── spec/                    # 项目级 Spec（requirements / design / tasks / devlog / structure）
├── scripts/
│   └── verify-docker.sh     # 容器化环境冒烟自检
├── docker-compose.yml       # 一键启动 backend + frontend
├── Makefile                 # Docker Compose 便捷命令
├── AGENTS.md                # AI 代理配置
└── README.md                # 本文件
```

## Docker 常用命令

`Makefile` 是 `docker compose` 的薄封装，所有命令幂等：

| 命令 | 作用 |
|------|------|
| `make up` | 后台启动所有服务 |
| `make down` | 停止容器（保留 volume 与数据） |
| `make logs` | tail 所有服务日志 |
| `make ps` | 列出运行中的服务 |
| `make rebuild` | 重建镜像（无缓存） |
| `make shell-backend` | 进入 backend bash |
| `make shell-frontend` | 进入 frontend sh |
| `make seed-demo` | 灌入内置演示数据（Docker 容器环境） |
| `make seed-demo-local` | 灌入内置演示数据（本地开发，跳过 Docker） |
| `make verify` | 运行冒烟自检（config + 3 端点 curl） |
| `make clean` | 停止容器 **并删除 volume**（数据丢失） |
| `make help` | 列出所有 target |

**数据持久化**：SQLite 库存在 Docker named volume `etf-momentum-db` 内（容器路径 `/app/data/etf_momentum.db`）。`make down` 保留 volume；`make clean` 删除 volume（含数据）。

## 本地开发（无 Docker）

如需绕过 Docker 直接本地开发（IDE 调试、热重载优化等）：

```bash
# Backend
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload        # http://localhost:8000

# Frontend（另一终端）
cd frontend
pnpm install
pnpm dev                                    # http://localhost:5173
```

详细开发规范、模块结构、测试命令分别见 `backend/README.md` 与 `frontend/README.md`。

## 故障排查

### Q1：前端能打开但 Dashboard / Backtest 页面是空的

**原因**：数据未同步。ETF 主数据、历史价格、实时信号至少缺一个。

**排查**：

```bash
# 检查 ETF 主数据数量
curl http://localhost:8000/api/v1/etfs/count
# 若 count=0 → 跑同步：
docker compose exec backend uv run python -m app.data.sync etfs

# 检查特定 ETF 的历史价格
curl 'http://localhost:8000/api/v1/etfs/510300/prices?limit=5'
# 若返回 [] → 跑价格同步：
docker compose exec backend uv run python -m app.data.sync prices --codes 510300 --full

# 检查今日信号是否已生成
curl 'http://localhost:8000/api/v1/signals/latest'
# 若 404 → 跑信号计算：
docker compose exec backend uv run python -m app.data.signal run --date YYYY-MM-DD --pool 510300
```

### Q2：后端容器启动失败 / `8000` 端口被占用

**原因**：宿主机 8000 端口被其他进程占用，或上一次容器未清理干净。

**排查**：

```bash
# 找占用进程
lsof -i :8000                              # macOS / Linux

# 或强制清理残留容器
docker compose down --remove-orphans
make up
```

### Q3：`python -m app.data.sync prices` 同步失败 / 卡住

**原因**：akshare 依赖外部网络（东方财富等数据源）；偶发限频或网络抖动。

**排查**：

```bash
# 1. 检查容器能否访问外网
docker compose exec backend curl -I https://www.baidu.com

# 2. 单只标的逐步测试（不要一次拉全市场）
docker compose exec backend uv run python -m app.data.sync prices --codes 510300 --full

# 3. 指定较短时间窗口，避免触发限频
docker compose exec backend uv run python -m app.data.sync prices \
    --codes 510300 --start 2024-01-01 --end 2024-12-31

# 4. 若 akshare 整体不可用，可等待或换数据源（baostock 备选，见 v2.0 计划）
```

### Q4：测试运行失败 / 端口冲突

**原因**：pytest 与 vitest 默认不需要端口，但 e2e/集成测试可能占用。

**排查**：单跑测试用 `cd backend && uv run pytest -k <pattern>` 或 `cd frontend && pnpm test --run <file>`。

## 文档导航

| 想了解 | 看哪里 |
|--------|--------|
| 项目整体需求 / 架构 | `spec/requirements.md`、`spec/design.md` |
| 后端模块结构 / API / CLI / 测试 | [`backend/README.md`](backend/README.md) |
| 前端页面 / 组件 / store / 测试 | [`frontend/README.md`](frontend/README.md) |
| 历史变更与决策记录 | `openspec/changes/archive/` |
| AI 代理配置 | `AGENTS.md` |
| 里程碑任务进度 | [`spec/tasks.md`](spec/tasks.md) |

## 里程碑

当前进度：**v1.0 阶段 4（质量与交付）**。

| 版本 | 状态 | 关键里程碑 |
|------|------|------------|
| v1.0 MVP | 全部已完成 | 基础设施（FastAPI / Vite / SQLite / Docker）→ 核心能力（动量 / 回测 / 6 指标 / 信号）→ API + 前端（Dashboard / Backtest / Pools）→ 质量（267 后端测试 / 190 前端测试 / README） |
| v2.0 | 占位 | 多策略对比、美股扩展、用户账户、实时告警 |

详见 [`spec/tasks.md`](spec/tasks.md)。