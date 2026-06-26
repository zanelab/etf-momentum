# 项目目录结构说明

## 架构选择
全栈（后端 + 前端 Web）— 2026-06-26 初始化时确认

## 后端实现状态（2026-06-26）
FastAPI 脚手架已就位（change: backend-fastapi-scaffold，已归档）。

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   └── api/
│       ├── __init__.py
│       ├── health.py           # GET /health
│       └── v1/
│           ├── __init__.py
│           └── router.py       # /api/v1 业务前缀占位
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── pyproject.toml              # uv 依赖管理
├── uv.lock
└── README.md
```

## 前端实现状态（2026-06-26）
Vite + React + TypeScript 脚手架已就位（change: frontend-vite-react-scaffold，已归档）。

```
frontend/
├── public/
├── src/
│   ├── __tests__/              # Vitest 测试
│   │   ├── cn.test.ts
│   │   ├── health-store.test.ts
│   │   └── setup.ts
│   ├── api/client.ts           # fetch 封装 + ApiError
│   ├── components/ui/button.tsx # shadcn Button
│   ├── layouts/Layout.tsx      # 左侧导航 + 顶部标题 + Outlet
│   ├── lib/utils.ts            # cn() 工具
│   ├── pages/HealthPage.tsx    # /health 页面
│   ├── stores/health-store.ts  # Zustand 健康检查状态
│   ├── App.tsx                 # 路由配置
│   ├── main.tsx                # React 入口
│   ├── index.css               # Tailwind + shadcn CSS 变量
│   └── vite-env.d.ts
├── index.html
├── vite.config.ts              # Vite + Vitest
├── tsconfig.json               # TS strict
├── tsconfig.node.json
├── tailwind.config.js
├── postcss.config.js
├── package.json
├── pnpm-lock.yaml
└── README.md
```

## 目录布局

```
etf-momentum/
├── spec/                     # 项目级 Spec
│   ├── requirements.md       # 整体需求
│   ├── design.md             # 架构设计
│   ├── tasks.md              # 里程碑任务
│   ├── devlog.md             # 开发日志
│   └── structure.md          # 本文档
├── openspec/                 # OpenSpec 配置
│   ├── config.yaml           # OpenSpec 配置（schema: spec-driven）
│   ├── specs/                # 长期规格
│   └── changes/
│       └── archive/          # 已归档变更
├── backend/                  # 后端代码（FastAPI，已脚手架）
├── frontend/                 # 前端代码（Vite + React，已脚手架）
└── AGENTS.md                 # 开发规则
```
