# Proposal: 前端 Vite + React 脚手架

## What
在 `frontend/` 目录下建立 Vite + React + TypeScript 的最小可运行骨架，作为后续业务页面（Dashboard、Backtest UI、ETF 池管理）的基础设施。

具体包含：
- Vite 构建 + React 18 + TypeScript（strict）
- React Router v6 提供路由（首页重定向到 `/health`）
- `/health` 页面：调用后端 `GET /health`，展示后端存活状态
- Tailwind CSS + shadcn/ui（基础 Button、Card 组件）
- Zustand 提供轻量全局状态
- 基础布局壳：左侧导航 + 顶部标题栏
- API 客户端：轻量 fetch 封装（base URL 通过环境变量配置）
- 依赖管理使用 `pnpm`，锁文件 `pnpm-lock.yaml`
- `README.md` 说明启动 / 构建 / 测试命令

## Why
当前 `frontend/` 为空目录。后续每个业务页面（Dashboard 看板、回测 UI、ETF 池管理）都将依赖这个骨架。提早建立脚手架可以让后续 change 专注于业务逻辑与 UI 细节，避免每个 change 都重复搭建环境。

## Scope
- [ ] backend
- [x] frontend

## Acceptance Criteria
- [ ] `frontend/package.json` 存在，使用 pnpm 管理依赖
- [ ] `pnpm install` 安装无报错，生成 `pnpm-lock.yaml`
- [ ] `pnpm dev` 启动 Vite dev server（默认 5173 端口），无报错
- [ ] `pnpm build` 产出生产构建无错误
- [ ] `pnpm test` 运行至少一个组件 / 工具函数的测试，全绿
- [ ] 首页（`/`）重定向到 `/health`
- [ ] `/health` 页面调用 `GET /health` 并展示后端响应状态
- [ ] Tailwind CSS 与 shadcn/ui Button 至少一处可见使用
- [ ] 路由使用 `react-router-dom`，至少 `/` 与 `/health` 两条
- [ ] API 客户端封装于 `frontend/src/api/client.ts`，可通过环境变量配置 base URL
- [ ] Zustand store 至少一个示例（用于健康检查状态）
- [ ] `frontend/README.md` 包含启动、构建、测试命令
- [ ] 目录结构与 `spec/design.md` 中的「目录布局」一致

## Status
- [x] 提案已确认
