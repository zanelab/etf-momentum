# etf-momentum Frontend

A 股 ETF 动量策略系统的前端。基于 Vite + React + TypeScript，使用 pnpm 管理依赖，shadcn/ui + Tailwind 提供 UI 组件，Zustand 管理状态，vitest + @testing-library/react 做单元测试。

## 目录

- [项目简介](#项目简介)
- [Docker](#docker)
- [环境要求](#环境要求)
- [安装](#安装)
- [启动开发服务器](#启动开发服务器)
- [生产构建](#生产构建)
- [运行测试](#运行测试)
- [类型检查](#类型检查)
- [页面说明](#页面说明)
- [Zustand store 清单](#zustand-store-清单)
- [API 客户端](#api-客户端)
- [环境变量](#环境变量)
- [项目结构](#项目结构)
- [后续计划](#后续计划)

## 项目简介

v1.0 已交付的全部前端能力：

- **4 个业务页面**：`/dashboard` 动量看板、`/backtest` 回测工作台、`/pools` ETF 池管理、`/health` 健康检查
- **共享 Layout**：左侧 NavLink 导航 + 顶部标题 + `<Outlet />` 子路由出口（基于 React Router v6）
- **shadcn/ui + Tailwind**：基础 Button / Card / Badge 等组件；CSS 变量驱动主题
- **5 个 Zustand store**：每个业务域独立的状态机（idle / loading / ok / error）
- **API 客户端封装**：`apiGet` / `apiPost` / `apiPut` / `apiDelete`，统一 `ApiError` 处理
- **190 个 vitest 测试**（26 个测试文件）：store 单测 + 组件渲染 + 交互行为

## Docker

详见根目录 `README.md` 的「Docker Compose」章节。本目录下：

- `Dockerfile`：基于 `node:24-alpine` + pnpm（corepack 激活），`pnpm dev --host 0.0.0.0` 启动
- `.dockerignore`：排除 `node_modules`、`dist`、`.vite`、`*.tsbuildinfo`
- `.npmrc`：放宽 pnpm 11 的 `minimum-release-age` 与 build 策略（dev 镜像专用）

容器内 HMR：`./frontend` bind mount 到容器 `/app`，编辑源码即热更新。

## 环境要求

- Node.js 18+（推荐 20+）
- [pnpm](https://pnpm.io/) 10+

## 安装

```bash
cd frontend
pnpm install
```

## 启动开发服务器

```bash
pnpm dev
```

默认监听 `http://localhost:5173`。访问根路径会自动跳转到 `/health`。

注意：访问页面需先启动后端（参见 [`../backend/README.md`](../backend/README.md)）。默认后端地址 `http://localhost:8000`，可通过 `.env.development` 中的 `VITE_API_BASE_URL` 修改。

## 生产构建

```bash
pnpm build
```

产物输出至 `dist/`，可用 `pnpm preview` 预览。`build` 命令先跑 `tsc -b` 类型检查，再跑 `vite build` 打包；任一阶段失败整个命令 exit 非 0。

## 运行测试

```bash
pnpm test           # 单次运行（CI 模式）
pnpm test:watch     # 监听模式（开发）

# 收集测试数（用于文档自检）
pnpm test 2>&1 | grep -E "Test Files|Tests"
```

**截至 v1.0 共 190 个测试 / 26 个文件**（以 `pnpm test` 当前输出为准）。

## 类型检查

```bash
pnpm lint           # tsc --noEmit
```

## 页面说明

| 路由 | 页面组件 | 作用 | 关键交互 |
|------|----------|------|----------|
| `/dashboard` | `DashboardPage.tsx` | 当日动量排名 + BUY/HOLD/WATCH 三态标签 | 选择日期、点击 ETF 行看历史价格 |
| `/backtest` | `BacktestPage.tsx` | 参数化回测工作台 + 业绩图表（recharts） | 选 ETF 池、设窗口/调仓频率、跑回测、看 NAV 曲线 + 6 指标卡片 |
| `/pools` | `PoolsPage.tsx` | ETF 策略池 CRUD（创建 / 查看 / 编辑 / 删除） | 输入池名 + codes 列表、提交后即时刷新 |
| `/health` | `HealthPage.tsx` | 后端健康检查 + 重新检测按钮 | 调用 `GET /health`、展示 ok/loading/error 三态 |

根路径 `/` 自动重定向到 `/health`（在 `App.tsx` 中配置）。

## Zustand store 清单

每个业务域独立 store，统一状态机：`"idle" | "loading" | "ok" | "error"`。

| Store 文件 | Store 名 | 管理状态 |
|------------|----------|----------|
| `src/stores/health-store.ts` | `useHealthStore` | `status` + `data: { status }` + `error` + `check()` action |
| `src/stores/etfs-store.ts` | `useEtfsStore` | ETF 列表 + 加载状态 + 错误 + `fetchAll()` action |
| `src/stores/signals-store.ts` | `useSignalsStore` | 当日/指定日信号快照 + 加载状态 + `fetchLatest()` / `fetchByDate()` |
| `src/stores/backtest-store.ts` | `useBacktestStore` | 回测运行列表 + 当前运行 + NAV 序列 + `run()` / `fetchById()` |
| `src/stores/pools-store.ts` | `usePoolsStore` | 策略池列表 + CRUD 操作 + 当前选中池 |

## API 客户端

`src/api/client.ts` 提供薄封装：

```typescript
import { apiGet, apiPost, apiPut, apiDelete, ApiError } from "@/api/client";

// GET
const etfs = await apiGet<EtfsApiResponse>("/api/v1/etfs?limit=10");

// POST
const run = await apiPost<BacktestRunResponse>("/api/v1/backtest", {
    etf_pool: ["510300", "510500"],
    start: "2024-01-01",
    end: "2024-12-31",
    initial_cash: "100000",
    top_n: 2,
    rebalance_freq: "monthly",
});

// 错误处理
try {
    await apiGet("/api/v1/etfs/999999");
} catch (e) {
    if (e instanceof ApiError) {
        // e.status: HTTP code; e.message: 错误描述
    }
}
```

各业务域的 `fetchXxx` 函数（如 `fetchAllEtfs` / `fetchLatestSignals`）由 `src/api/<domain>.ts` 进一步封装，处理 URL 拼接与 query string。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API base URL | 空字符串（相对路径，使用 Vite proxy）或 `http://localhost:8000`（开发） |

修改 `.env.development` 或 `.env.production` 即可配置。

## 项目结构

```
frontend/
├── public/                          # 静态资源
├── src/
│   ├── __tests__/                   # 工具函数测试（cn 等）
│   ├── api/                         # API 客户端
│   │   ├── client.ts                # fetch 封装 + ApiError + apiGet/apiPost/apiPut/apiDelete
│   │   ├── etfs.ts                  # ETF 域 fetch 封装
│   │   ├── signals.ts               # Signal 域 fetch 封装
│   │   ├── backtest.ts              # Backtest 域 fetch 封装
│   │   ├── pools.ts                 # Pools 域 fetch 封装
│   │   └── *.test.ts                # API 客户端测试
│   ├── components/
│   │   └── ui/
│   │       ├── button.tsx           # shadcn Button
│   │       ├── card.tsx             # shadcn Card
│   │       ├── badge.tsx            # shadcn Badge
│   │       └── *.test.tsx           # 组件测试
│   ├── layouts/
│   │   ├── Layout.tsx               # 左侧 NavLink + 顶部标题 + Outlet
│   │   └── Layout.test.tsx
│   ├── lib/
│   │   └── utils.ts                 # cn() 工具（clsx + tailwind-merge）
│   ├── pages/
│   │   ├── DashboardPage.tsx        # /dashboard
│   │   ├── BacktestPage.tsx         # /backtest
│   │   ├── PoolsPage.tsx            # /pools
│   │   ├── HealthPage.tsx           # /health
│   │   └── *.test.tsx               # 每个页面 1 个测试文件
│   ├── stores/                      # Zustand store
│   │   ├── health-store.ts
│   │   ├── etfs-store.ts
│   │   ├── signals-store.ts
│   │   ├── backtest-store.ts
│   │   ├── pools-store.ts
│   │   ├── __tests__/               # store 单测
│   │   │   └── *.test.ts
│   ├── App.tsx                      # React Router v6 路由配置
│   ├── main.tsx                     # React 入口
│   ├── index.css                    # Tailwind + shadcn CSS 变量
│   └── vite-env.d.ts                # import.meta.env 类型
├── index.html                       # Vite HTML 入口
├── vite.config.ts                   # Vite + Vitest 配置（含 @ alias）
├── tsconfig.json                    # TS strict + path alias
├── tailwind.config.js
├── postcss.config.js
├── package.json
├── pnpm-lock.yaml
└── README.md
```

## 后续计划

> v1.0 范围已全部交付（4 个页面 + Layout + 5 个 store + 190 测试）。本节仅列 v2.0+ 占位项。

- **v2.0**：
  - TanStack Query 替换直 fetch（数据缓存、自动失效、乐观更新）
  - 全局错误边界 + Toast 提示
  - ECharts / Lightweight Charts 替换 recharts（更丰富的 K 线 / 因子曲线）
  - 深色模式 / 主题切换
  - 鉴权（用户登录、token 管理）
  - 实时推送（WebSocket 推送今日信号变更）