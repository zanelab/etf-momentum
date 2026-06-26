# Implementation Plan: 前端 Vite + React 脚手架

## Prerequisites
- [x] 确认 Node.js 18+ 可用（`node --version` → v24.14.0）
- [x] 确认 pnpm 已安装（`pnpm --version` → 10.33.0）

## Project Skeleton
- [x] 创建 `frontend/` 子目录：`src/`、`src/pages/`、`src/components/`、`src/api/`、`src/stores/`、`src/layouts/`、`src/lib/`
- [x] 创建测试目录 `src/__tests__/` 与 `vitest` 配置

## Dependency Management (pnpm)
- [x] 在 `frontend/` 下创建 `package.json`，声明项目元数据与依赖
- [x] 添加依赖：react、react-dom、react-router-dom、zustand、clsx、tailwind-merge、class-variance-authority、lucide-react
- [x] 添加开发依赖：vite、@vitejs/plugin-react、typescript、@types/react、@types/react-dom、tailwindcss、postcss、autoprefixer、vitest、@testing-library/react、@testing-library/jest-dom、jsdom、@types/node
- [x] 执行 `pnpm install` 生成 `node_modules/` 与 `pnpm-lock.yaml`（含 esbuild postinstall 批准）

## Build & Tooling Config
- [x] 创建 `vite.config.ts`（含 React 插件、Vitest 配置）
- [x] 创建 `tsconfig.json`（strict 模式 + path alias `@/*` → `src/*`）
- [x] 创建 `tsconfig.node.json`（Node 端类型）
- [x] 创建 `tailwind.config.js`（content 指向 src + shadcn 预设）
- [x] 创建 `postcss.config.js`（tailwindcss + autoprefixer）
- [x] 创建 `index.html`（Vite 入口，含 `<div id="root">`）
- [x] 创建 `.env.development` 与 `.env.production` 模板（`VITE_API_BASE_URL`）

## Tailwind & shadcn/ui Setup
- [x] 创建 `src/index.css` 引入 Tailwind 指令 + shadcn CSS 变量
- [x] 创建 `src/lib/utils.ts`（`cn()` 合并 className 工具）
- [x] 手动添加 shadcn Button 组件至 `src/components/ui/button.tsx`（避免 CLI 交互）

## Source Code — Tests First (TDD)
- [x] 创建 `src/__tests__/cn.test.ts`：测试 `cn()` 合并与条件 class（4 通过）
- [x] 创建 `src/__tests__/health-store.test.ts`：测试 `useHealthStore` 状态转换（idle → loading → ok/error）
- [x] 运行 `pnpm test` 确认失败（红 phase：health-store.test.ts import 失败）

## Source Code — Implementation
- [x] 实现 `src/lib/utils.ts`（cn 函数）使 cn 测试通过
- [x] 实现 `src/stores/health-store.ts`（Zustand store，含 status/setStatus/setError）使 store 测试通过
- [x] 创建 `src/api/client.ts`：fetch 封装，读取 `VITE_API_BASE_URL`，提供 `apiGet<T>`、`apiPost<T>` 工具函数
- [x] 创建 `src/components/ui/button.tsx`（shadcn Button 副本，含 cva 变体）
- [x] 创建 `src/layouts/Layout.tsx`：左侧导航 + 顶部标题 + `<Outlet />` 内容区
- [x] 创建 `src/pages/HealthPage.tsx`：使用 `useHealthStore` + `apiGet` 调用 `/health`，展示状态
- [x] 创建 `src/App.tsx`：`<BrowserRouter>` + `<Routes>` 配置（`/` → Navigate to `/health`，`/health` → HealthPage）
- [x] 创建 `src/main.tsx`：渲染 `<App />` 到 `#root`

## TDD Verification
- [x] 运行 `pnpm test`，所有测试通过（9/9：cn 4 + health-store 5）
- [x] 运行 `speccoding-tdd.sh verify frontend/src/stores/health-store.ts`（PASS）

## Build & Runtime Verification
- [x] `pnpm build` 产出生产构建无错误（1591 modules, 194KB JS, 10KB CSS）
- [x] 启动后端（`uv run uvicorn app.main:app --port 8000`，后台）
- [x] 启动前端（`pnpm dev`，后台）
- [x] `curl http://localhost:5173/` 返回 Vite HTML，含 `<div id="root">`
- [x] `curl http://localhost:5173/health` 返回 Vite HTML（SPA 路由 fallback 200）
- [x] 浏览器或 curl 验证 dev server 代理或直连：响应中包含 `<div id="root">`

## Documentation
- [x] 创建 `frontend/README.md`，包含：
  - 项目简介
  - 安装步骤（`pnpm install`）
  - 启动命令（`pnpm dev`）
  - 构建命令（`pnpm build`）
  - 测试命令（`pnpm test`）
  - 环境变量（`VITE_API_BASE_URL`）
  - 目录结构图
