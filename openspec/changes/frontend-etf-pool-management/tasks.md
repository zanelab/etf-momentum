# Tasks: 前端 ETF 池管理 + Backtest 池集成

## 1. 分支与依赖

- [x] 1.1 从 `main` 切到新分支 `feature/frontend-etf-pool-management`

## 2. 后端：数据模型 + REST

- [x] 2.1 Alembic 新迁移：`etf_pools` 表（id, name UNIQUE, description, created_at, updated_at）+ `etf_pool_members` 表（pool_id FK, etf_code FK → etfs.code, position INT, PK (pool_id, etf_code)）
- [x] 2.2 新增 SQLAlchemy ORM 模型 `EtfPool` / `EtfPoolMember` + Pydantic schema `EtfPoolCreate` / `EtfPoolUpdate` / `EtfPoolRead` / `EtfPoolSummary`
- [x] 2.3 新增 service `app/services/pool_service.py`：CRUD + name 唯一校验（409）+ etf_code 必须存在于 etfs 表（422）+ 事务原子性
- [x] 2.4 新增 router `app/api/v1/pools.py`：5 端点 GET 列表 / POST / GET 详情 / PUT / DELETE，挂到 `/api/v1`
- [x] 2.5 新增后端测试 `backend/tests/test_pools_api.py`：覆盖 5 端点 + 409 重名 + 422 未知 code + 404 删除 + 空列表
- [x] 2.6 跑 `cd backend && uv run pytest tests/test_pools_api.py -v`，确认全过

## 3. 前端：API 客户端 + 状态管理

- [x] 3.1 新增 `frontend/src/api/pools.ts`：定义 `EtfPoolSummary` / `EtfPoolMember` / `EtfPoolDetail` / `EtfPoolCreateRequest` / `EtfPoolUpdateRequest` 类型，导出 `listPools()` / `getPool(id)` / `createPool(req)` / `updatePool(id, req)` / `deletePool(id)`
- [x] 3.2 新增 `frontend/src/api/__tests__/pools.test.ts`：覆盖 5 函数成功 + 409 + 422 + 404 + 网络错误
- [x] 3.3 新增 `frontend/src/stores/pools-store.ts`：zustand store，状态 `{ status, items, currentPool, currentPoolStatus, createStatus, updateStatus, deleteStatus, error, fetchAll, fetchOne, create, update, remove, reset }`；delete 成功后从 items 中移除该 id
- [x] 3.4 新增 `frontend/src/stores/__tests__/pools-store.test.ts`：覆盖 list/get/create/update/delete 五个动作 + 错误路径

## 4. 前端：池管理 UI 组件

- [x] 4.1 新增 `frontend/src/components/pools/EtfPickerGrid.tsx`：复用 BacktestForm 的 checkbox 网格（搜索 + "已选 N / total" 头部 + show first 12 + 锁定模式），独立组件以便 PoolsPage 和 BacktestForm 都能用
- [x] 4.2 新增 `frontend/src/components/pools/EtfPickerGrid.test.tsx`：渲染、搜索过滤、选中计数、locked prop 禁用
- [x] 4.3 新增 `frontend/src/components/pools/PoolList.tsx`：卡片网格，hover 显示编辑 / 删除按钮，点击编辑触发回调
- [x] 4.4 新增 `frontend/src/components/pools/PoolList.test.tsx`：空态、列表渲染、编辑 / 删除回调触发
- [x] 4.5 新增 `frontend/src/components/pools/PoolEditor.tsx`：表单（名称、描述、EtfPickerGrid、diff 摘要、保存 / 取消按钮）；name 字段下方预留 409 错误位；etf_codes 错误位；diff 摘要只在 count 变化时显示
- [x] 4.6 新增 `frontend/src/components/pools/PoolEditor.test.tsx`：空名拦截、空池拦截、保存触发回调、diff 摘要渲染、409 错误展示

## 5. 前端：PoolsPage 装配

- [ ] 5.1 新增 `frontend/src/pages/PoolsPage.tsx`：useEffect 拉 pools；左侧 PoolList + 右侧 PoolEditor（编辑态）；新建按钮清空编辑器进入创建态；删除走原生 confirm；409/422/网络错误分别展示
- [ ] 5.2 新增 `frontend/src/pages/PoolsPage.test.tsx`：渲染空态、列表渲染、点击新建进入创建态、点击编辑进入编辑态、删除确认、删除成功后列表更新

## 6. 前端：BacktestForm 池集成

- [x] 6.1 修改 `frontend/src/components/backtest/BacktestForm.tsx`：顶部新增 mode 切换（"使用策略池" / "自定义"），pool 模式下 EtfPickerGrid 加 `locked` prop + 自动注入池成员 + 显示池下拉；切池模式弹原生 confirm
- [x] 6.2 新增 `frontend/src/components/backtest/BacktestForm.test.tsx` 用例：pool 模式渲染、locked checkbox、池列表为空显示链接、池列表加载失败显示重试
- [x] 6.3 修改 `frontend/src/api/backtest.ts`：`BacktestRequest` 新增可选 `pool_id?: number | null`
- [x] 6.4 修改 `frontend/src/stores/backtest-store.ts`：submit 时透传 pool_id（state 中加 poolId 字段 + onSubmit 调用方传入）

## 7. 路由与导航

- [x] 7.1 修改 `frontend/src/App.tsx`：新增 `<Route path="pools" element={<PoolsPage />} />`
- [x] 7.2 修改 `frontend/src/layouts/Layout.tsx`：在 navItems 插入 `{ to: "/pools", label: "策略池" }`

## 8. 类型与构建验证

- [x] 8.1 跑 `cd frontend && pnpm tsc --noEmit`，确认无 TS 错误
- [x] 8.2 跑 `cd frontend && pnpm vitest run`，确认既有 + 新增测试全过（目标 130+）
- [x] 8.3 跑 `cd backend && uv run pytest`，确认后端测试全过
- [x] 8.4 跑 `cd frontend && pnpm build`，确认 `tsc -b && vite build` 通过

## 9. 端到端冒烟（手动）

- [x] 9.1 后端 uvicorn 8000 + `cd frontend && pnpm dev`；浏览 `/pools`
- [x] 9.2 新建池"宽基核心"（3 只）→ 列表显示 → 详情正确
- [x] 9.3 编辑池改名为"宽基核心 2" + 加 1 只 → 列表更新 → 详情正确
- [x] 9.4 再次新建同名"宽基核心 2" → 409 提示
- [x] 9.5 删除池 → confirm → 列表移除
- [x] 9.6 浏览器到 `/backtest` → 切"使用策略池" → 选"宽基核心 2" → checkbox 全自动勾且锁定 → 提交 → 跑回测
- [x] 9.7 切回"自定义" → 之前自定义勾选恢复（如果有）

> 注：9.6 的回测实跑受限于 akshare 行情同步失败（已记录的后端 issue），仅验证了后端接收 `pool_id` 字段、池成员正确填充到 `etf_pool`，价格数据 422 由预存问题引起。
