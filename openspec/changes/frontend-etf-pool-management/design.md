## Context

- 后端已有：FastAPI + SQLAlchemy 2.0 + SQLite + Alembic；`etfs` / `daily_prices` / `backtest_runs` / `signal_snapshots` 4 张业务表
- 前端已有：vite + react + zustand + tailwind + react-router v6；既有 backtest-store 和 etfs-store 模式可复用
- 既有 rest-api 端点：`GET /api/v1/etfs?limit=500`（1522 只）已用于 BacktestForm 选择器
- 用户已经在跑回测，每次都从 1522 只里重复勾选同样的几个组合
- v1.0 单用户、无登录；池表不需要 user_id 列

## Goals / Non-Goals

**Goals:**
- 用户能在 `/pools` 页面 CRUD 自己的策略池（命名 + 描述 + ETF 子集）
- BacktestForm 顶部能用"选池"自动灌入 etf_pool，避免重复勾选
- 池数据持久化（不丢）
- 与既有风格一致：typed API + zustand store + Tailwind + 中文 UI

**Non-Goals:**
- 池导入/导出
- 多用户/分享
- 池与回测历史绑定
- 池的智能推荐
- 修改既有的 backtest / etfs / signals 表结构

## Decisions

### 1. 数据模型：两表（pool + members），不用 JSON 列
- `etf_pools` (id, name UNIQUE, description, created_at, updated_at)
- `etf_pool_members` (pool_id FK, etf_code FK → etfs.code, position INT, PRIMARY KEY (pool_id, etf_code))
- 替代方案：把 members 存成 JSON 列。否决 — 查询"哪些池包含这只 ETF"和约束 UNIQUE(name) 都需要关系表
- position 字段让池成员有顺序（用户拖拽排序用，但 v1.0 UI 不暴露拖拽，先存下来）

### 2. REST 设计：5 端点，与既有 rest-api 风格一致
- `GET /api/v1/pools` → `{items: [{id, name, description, member_count, created_at, updated_at}], total}`
- `POST /api/v1/pools` → body `{name, description?, etf_codes: [...]}` → 201 + 完整对象
- `GET /api/v1/pools/{id}` → `{id, name, description, members: [{code, name, market, category, position}], created_at, updated_at}`
- `PUT /api/v1/pools/{id}` → body `{name, description?, etf_codes: [...]}` → 完整对象（**整体替换**成员列表，不是 patch）
- `DELETE /api/v1/pools/{id}` → 204
- name 唯一约束 → 重复时返回 409，错误 detail `"Pool <name> already exists"`
- etf_codes 校验：每只必须在 etfs 表里，否则 422 `"Unknown ETF code: 510999"`

### 3. 前端 store：`pools-store` 与 `backtest-store` 解耦
- `usePoolsStore` 管理 `{ status, items, currentPool, error, fetchAll, fetchOne, create, update, remove, reset }`
- BacktestForm 在挂载时**不**主动调 pools API；改为"点开策略池下拉时"按需加载（lazy） — 1522 只 ETF 已经够重，pool 列表不应该加重首屏
- 替代方案：BacktestPage 挂载时并行 fetch。否决 — 用户进 /backtest 不一定用 pool

### 4. BacktestForm 集成：select 切池 + 锁定 vs 自定义
- BacktestForm 顶部新增 select："使用策略池 ▼ / 自定义"
- 选池模式：从下拉选池 → 自动勾选池内成员 → 用户**可以取消勾**但不能加入新 ETF（lock 加锁）
- 选"自定义"模式：恢复原有交互（无 lock，自由勾）
- 模式切换不清空 formErrors / currentRun 等其它状态
- 替代方案：池成员与自由勾完全独立两张 view。否决 — 增加复杂度，diff 体验差

### 5. 池编辑 UI：单页内嵌编辑，不弹模态
- `/pools` 页面左侧是 PoolList（卡片网格，hover 显示操作按钮）
- 点击"编辑" → 行内展开 PoolEditor（同一页右侧或行下方）
- 替代方案：弹模态。否决 — 模态里塞 1522 只 checkbox 网格体验差

### 6. 删除确认：原生 confirm() 即可
- 一行 `window.confirm("确定删除池「宽基核心」？此操作不可撤销。")`
- 替代方案：自建 ConfirmDialog 组件。v1.0 不值 — 单用户场景、原生 confirm 够用

## Risks / Trade-offs

- [Risk] 池 name 重复 → 409，前端需要在表单上区分 409 vs 422 vs 网络错误 → [Mitigation] store 在 409 时把后端 detail 直接展示在表单 name 字段下；其它错误走通用 error 卡
- [Risk] PUT 整体替换成员，如果用户编辑时漏勾某些 ETF 会误删 → [Mitigation] 编辑器加载时显示当前 members 全集；保存前显示"将保存 N 只 ETF（原 M 只）"摘要；删除的 ETF 单独高亮
- [Risk] 池内含退市 ETF（已从 etfs 表删除）时 PUT/GET 行为不明 → [Mitigation] 后端在 PUT 时校验所有 codes 必须在 etfs 表；GET 时保留 orphan 成员但前端显示"⚠️ 该 ETF 已下线"
- [Risk] BacktestForm 切池模式 lock checkbox，但用户已经手动勾了非池成员怎么办 → [Mitigation] 切池时弹确认"将丢弃当前 X 个自定义勾选，确定？"；切回自定义保留上次自由勾选（local state）
- [Risk] 1522 只 ETF 的 checkbox 网格在 PoolEditor 中性能 / 滚动差 → [Mitigation] 复用 BacktestForm 的搜索过滤 + 限速 12 + "已选 N" 头部；分页不必要（单页全可见的更直观）
- [Risk] 删除最后一个池时 BacktestForm 顶部 select 怎么处理 → [Mitigation] 列表为空时 select 显示"（暂无策略池）+ 创建新池"链接跳转 `/pools`

## Open Questions

- 池是否需要"内置"几个（如"宽基全市场"、"红利全市场"）让新用户上手？**决定**：v1.0 不做，避免污染用户空间
- 编辑时是否支持拖拽排序 position？**决定**：存 position 字段但 v1.0 UI 不暴露排序 UI（按 code 字典序展示）
