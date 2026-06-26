# Spec: 前端 Vite + React 脚手架

## ADDED Requirements

### Requirement: 前端开发服务器可启动
`pnpm dev` 必须能在本地启动 Vite dev server 并监听 5173 端口。

#### Scenario: 启动 dev server
- Given 已运行 `pnpm install`
- When 用户执行 `pnpm dev`
- Then Vite 在 5173 端口监听，且终端输出本地访问 URL

#### Scenario: 浏览器访问首页返回 React 应用
- Given dev server 已启动
- When 用户访问 `http://localhost:5173/`
- Then 返回 HTML 页面，渲染 React 根组件

### Requirement: 首页重定向到 /health
访问根路径必须自动跳转到 `/health`。

#### Scenario: 根路径重定向
- Given 用户访问 `http://localhost:5173/`
- When 页面加载完成
- Then 浏览器地址栏变为 `/health` 且展示健康检查页面

### Requirement: /health 页面调用后端健康检查
`/health` 页面必须调用后端 `GET /health` 并展示响应状态。

#### Scenario: 后端存活时显示 OK
- Given 后端服务在 `http://localhost:8000` 已启动且 `/health` 返回 200
- When `/health` 页面加载
- Then 显示「后端存活」状态与响应内容 `{"status":"ok"}`

#### Scenario: 后端不可达时显示错误
- Given 后端服务未启动或不可达
- When `/health` 页面加载
- Then 显示错误提示（连接失败 / 网络错误），不崩溃

### Requirement: API 客户端支持环境变量配置 base URL
API 客户端必须能通过环境变量配置后端 base URL，便于开发 / 生产环境切换。

#### Scenario: 通过 VITE_API_BASE_URL 配置
- Given `.env.development` 中设置 `VITE_API_BASE_URL=http://localhost:8000`
- When 应用调用 `apiClient.get('/health')`
- Then 实际请求 URL 为 `http://localhost:8000/health`

#### Scenario: 默认值生效
- Given 未设置 `VITE_API_BASE_URL`
- When 应用调用 `apiClient.get('/health')`
- Then 实际请求 URL 默认为 `/api/v1/...` 相对路径或 `http://localhost:8000`

### Requirement: UI 组件库基于 shadcn/ui + Tailwind
项目必须集成 Tailwind CSS 与至少一个 shadcn/ui 组件（Button 或 Card），且在页面中可见使用。

#### Scenario: Tailwind 工具类生效
- Given 已配置 Tailwind
- When 组件 className 包含 `bg-blue-500`
- Then 浏览器渲染该元素为蓝色背景

#### Scenario: shadcn Button 组件可见
- Given 已通过 shadcn CLI 添加 Button
- When `/health` 页面渲染
- Then 至少一个 shadcn Button 出现在页面上

### Requirement: 全局状态管理使用 Zustand
至少一个 Zustand store 用于管理健康检查状态。

#### Scenario: 读取健康检查状态
- Given 已创建 `useHealthStore`
- When 组件调用 `useHealthStore.getState().status`
- Then 返回 `'idle' | 'loading' | 'ok' | 'error'` 之一

#### Scenario: 更新健康检查状态
- Given 已创建 `useHealthStore`
- When 调用 `useHealthStore.getState().setStatus('ok')`
- Then 订阅该 store 的组件重新渲染

### Requirement: 路由使用 react-router-dom
应用路由必须通过 react-router-dom 管理，至少包含 `/` 与 `/health` 两条。

#### Scenario: 路由配置正确
- Given 已配置 `<Routes>` 含 `<Route path="/" element={<Navigate to="/health" />} />`
- When 用户访问 `/`
- Then 重定向至 `/health`

### Requirement: 基础布局壳（左侧导航 + 顶部标题）
应用必须提供带左侧导航栏与顶部标题栏的布局壳，业务页面渲染在内容区。

#### Scenario: 布局壳渲染
- Given 应用已挂载 `Layout` 组件
- When 任意业务页面渲染
- Then 可见左侧导航与顶部标题栏，业务页面渲染在内容区

### Requirement: 依赖通过 pnpm 管理
项目使用 pnpm 作为依赖管理工具，不引入 npm 或 yarn。

#### Scenario: package.json 存在
- Given 项目初始化完成
- When 检查 `frontend/` 根目录
- Then 存在 `package.json` 与 `pnpm-lock.yaml`

#### Scenario: 安装命令为 pnpm install
- Given 用户克隆项目后
- When 用户执行 `cd frontend && pnpm install`
- Then 创建 `node_modules/` 与 `pnpm-lock.yaml`

### Requirement: 前端具备测试覆盖
至少一个组件 / 工具函数必须有自动化测试。

#### Scenario: 运行测试全绿
- Given 在 `frontend/` 下执行 `pnpm test`
- When 收集所有测试
- Then 全部通过且退出码为 0

### Requirement: TypeScript 严格模式
tsconfig.json 必须启用严格模式。

#### Scenario: 严格模式启用
- Given 项目初始化完成
- When 检查 `frontend/tsconfig.json`
- Then 包含 `"strict": true`

### Requirement: 项目结构遵循 spec/design.md
前端目录结构必须与 `spec/design.md` 中描述的布局保持一致。

#### Scenario: 关键目录存在
- Given 项目初始化完成
- When 检查 `frontend/` 子目录
- Then 必须存在 `src/` 与 `src/pages/`、`src/components/`、`src/api/` 子目录
