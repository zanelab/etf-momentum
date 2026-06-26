# etf-momentum Frontend

A 股 ETF 动量策略系统的前端。基于 Vite + React + TypeScript，使用 pnpm 管理依赖，shadcn/ui + Tailwind 提供 UI 组件，Zustand 管理状态。

## Docker

详见根目录 `README.md` 的「Docker Compose」章节。本目录下：

- `Dockerfile`：基于 `node:24-alpine` + pnpm（corepack 激活），`pnpm dev --host 0.0.0.0` 启动
- `.dockerignore`：排除 `node_modules`、`dist`、`.vite`、`*.tsbuildinfo`
- `.npmrc`：放宽 pnpm 11 的 `minimum-release-age` 与 build 策略（dev 镜像专用）

容器内 HMR：`./frontend` bind mount 到容器 `/app`，编辑源码即热更新。

## 当前阶段
最小可运行脚手架：
- Vite dev server（5173）
- React Router v6：首页重定向到 `/health`
- `/health` 页面：调用后端 `GET /health`
- shadcn/ui Button + Tailwind
- Zustand `useHealthStore`
- Vitest 单元测试覆盖

后续将添加 Dashboard、Backtest UI、ETF 池管理等业务页面。

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

注意：访问 `/health` 页面需先启动后端（参见 `backend/README.md`）。默认后端地址 `http://localhost:8000`，可通过 `.env.development` 中的 `VITE_API_BASE_URL` 修改。

## 生产构建

```bash
pnpm build
```

产物输出至 `dist/`，可用 `pnpm preview` 预览。

## 运行测试

```bash
pnpm test           # 单次运行
pnpm test:watch     # 监听模式
```

## 类型检查

```bash
pnpm lint           # tsc --noEmit
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API base URL | 空（相对路径）或 `http://localhost:8000`（开发） |

修改 `.env.development` 或 `.env.production` 即可配置。

## 目录结构

```
frontend/
├── public/                          # 静态资源
├── src/
│   ├── __tests__/                   # Vitest 测试
│   │   ├── cn.test.ts
│   │   ├── health-store.test.ts
│   │   └── setup.ts
│   ├── api/                         # API 客户端
│   │   └── client.ts                # fetch 封装 + ApiError
│   ├── components/
│   │   └── ui/
│   │       └── button.tsx           # shadcn Button
│   ├── layouts/
│   │   └── Layout.tsx               # 左侧导航 + 顶部标题 + Outlet
│   ├── lib/
│   │   └── utils.ts                 # cn() 工具
│   ├── pages/
│   │   └── HealthPage.tsx           # /health 页面
│   ├── stores/
│   │   └── health-store.ts          # Zustand 健康检查状态
│   ├── App.tsx                      # 路由配置
│   ├── main.tsx                     # React 入口
│   ├── index.css                    # Tailwind + shadcn CSS 变量
│   └── vite-env.d.ts                # import.meta.env 类型
├── index.html                       # Vite HTML 入口
├── vite.config.ts                   # Vite + Vitest 配置
├── tsconfig.json                    # TS strict
├── tailwind.config.js
├── postcss.config.js
├── package.json
├── pnpm-lock.yaml
└── README.md
```

## 后续计划

- `/dashboard` 页面：动量排名 + 调仓建议
- `/backtest` 页面：参数选择 + 业绩图表
- `/etfs` 页面：ETF 池管理
- TanStack Query 替换直 fetch（数据缓存与失效）
- 鉴权（用户登录、token 管理）
