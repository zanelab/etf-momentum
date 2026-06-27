## Why

当前 `/backtest` 页面的 ETF 池选择器每次都让用户从 1522 只 ETF 里手动勾选 — 即使是常用的"宽基"或"红利"组合也要重新挑一遍。用户已经在多次回测中固化出几个常用组合（沪深300+中证500+红利 等），但目前没有任何方式保存这些组合。

需要让用户能**创建命名池**（如"宽基核心"、"红利高息"），保存后下次跑回测直接选池，避免每次重复勾选。

## What Changes

- 新增 `/pools` 路由 + 导航入口，提供池的 CRUD UI
- 用户可以新建池：填写名称 + 描述 + 从 1522 只 ETF 里勾选子集
- 用户可以编辑现有池：改名、调整成员
- 用户可以删除池（带确认弹窗）
- 池数据持久化到后端（需要新的 REST 端点）
- `BacktestForm` 顶部加"使用策略池"切换：选池 → 自动勾选池内 ETF；切回"自定义"→ 恢复用户原有勾选
- 池列表显示：名称 / 成员数 / 描述 / 创建时间 / 操作按钮

## Capabilities

### New Capabilities
- `etf-pool-management`: 用户自建策略池的 CRUD（前端 UI + 后端持久化）
- `backtest-pool-integration`: BacktestForm 与策略池联动（选池自动灌入 etf_pool）

### Modified Capabilities
<!-- 无现有 spec 受影响 — backtest-ui 的现有需求不要求 pool 集成，那是新增能力 -->

## Impact

**后端**
- 新表 `etf_pools`（id, name, description, created_at, updated_at）+ `etf_pool_members`（pool_id, etf_code, position）
- 新 REST 端点：
  - `GET /api/v1/pools` — 列表（含成员数）
  - `POST /api/v1/pools` — 创建（含成员 codes）
  - `GET /api/v1/pools/{id}` — 详情（含成员 codes）
  - `PUT /api/v1/pools/{id}` — 更新（替换名称/描述/成员）
  - `DELETE /api/v1/pools/{id}` — 删除
- Alembic 新迁移

**前端**
- 新增 `frontend/src/api/pools.ts` + 测试
- 新增 `frontend/src/stores/pools-store.ts` + 测试
- 新增 `frontend/src/pages/PoolsPage.tsx` + 测试
- 新增 `frontend/src/components/pools/{PoolList,PoolEditor,PoolPicker,ConfirmDialog}.tsx` + 测试
- 修改 `frontend/src/components/backtest/BacktestForm.tsx`：顶部加 "使用策略池" 切换器
- 修改 `frontend/src/App.tsx`：新增 `/pools` 路由
- 修改 `frontend/src/layouts/Layout.tsx`：navItems 加 "策略池"

**范围之外（v1.0 不做）**
- 池的导入/导出（CSV / JSON）
- 池的分享 / 多用户
- 池的回测历史绑定（哪个 pool 跑的哪个 run）
- 池的智能推荐（按动量排名自动建池）
