# 开发日志

## 初始化
- 日期：2026-06-26 初始化 SpecCoding 结构
- OpenSpec CLI v1.3.1 初始化完成（schema: spec-driven）
- 项目架构：全栈（后端 + 前端 Web），目录 backend/ + frontend/
- 市场范围：A 股 ETF
- 技术栈：Python + FastAPI（后端）+ React + TypeScript（前端）
- v1.0 范围：回测 + 实时信号监控
- git 仓库已初始化（main 分支，初始提交 34ba10e）

## change: backend-fastapi-scaffold
- 日期：2026-06-26
- 分支：feature/backend-fastapi-scaffold
- 阶段：proposal → spec → executing（全部完成）
- 实现：FastAPI 最小骨架（main.py + health.py + v1 router.py + test_health.py）
- 测试：pytest 4/4 通过（/health, /docs, /redoc, /openapi.json）
- 验证：uvicorn 启动后所有端点 HTTP 200，curl /health 返回 {"status":"ok"}
- 提交：2ccb33a
- 备注：
  - TDD 脚本 `speccoding-tdd.sh` 在 macOS 上存在两个限制：stat -c 返回 0（GNU vs BSD），导致 mtime 检查失效；内部多余 shift 导致传 N 个文件实际只检查 N-1 个
  - 当前无远程仓库（git remote 为空），未执行 git push；后续如需推送可配置 origin 后再走 merge 阶段

## change: frontend-vite-react-scaffold
- 日期：2026-06-26
- 分支：feature/frontend-vite-react-scaffold
- 阶段：proposal → spec → executing → archive（全部完成）
- 实现：Vite 5 + React 18 + TypeScript（strict）+ React Router v6 + Zustand + Tailwind + shadcn/ui Button
- 测试：vitest 9/9 通过（cn 4 + health-store 5）
- 验证：`pnpm build` 产出 194KB JS + 10KB CSS；dev server 启动后 `/` 与 `/health` 均返回 200；与后端 /health 联通
- 备注：
  - `pnpm` 默认不批准 postinstall 脚本（esbuild），需在 package.json 加 `pnpm.onlyBuiltDependencies: ["esbuild"]`
  - `tsc -b` 在 composite 模式下会为 `vite.config.ts` 生成 `.d.ts` 与 `.js`，需加入 `.gitignore`

