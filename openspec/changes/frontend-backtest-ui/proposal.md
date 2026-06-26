## Why

后端回测 API（`POST /api/v1/backtest`、`GET /api/v1/backtest/{id}`、`GET /api/v1/backtest/{id}/nav`）已经交付并合并到 main，但用户仍需用 curl/Postman/Swagger 手工提交回测 → 再拉 NAV。用户场景"想看一组 ETF 池 + 参数下历史 1 年的策略表现"被强迫走两次 HTTP，效率低、易错。提供 Web UI 让用户在浏览器表单里点选 ETF、调窗口/调仓参数、看回测指标和净值曲线，是把后端能力落到日常调仓决策的最后一公里。

## What Changes

- 新增路由 `/backtest`，侧边栏加入"回测"导航项
- 新增表单：ETF 池（多选 /etfs）、start / end 日期、initial_cash、lookback、skip、top_n、rebalance_freq
- 提交后调用 `POST /api/v1/backtest`，loading 状态期间禁用表单 + 显示 spinner
- 422 错误（参数无效 / 池中无价格）以字段级错误展示
- 成功后渲染：6 项业绩指标卡片（年化收益、最大回撤、夏普、Sortino、Calmar、总收益）+ NAV 时间序列折线图
- 折线图新增依赖 `recharts`（声明式 React 图表库）
- 表单错误：空池、未来日期、start>end、lookback<1 等基础校验
- 不做：历史回测列表（v1.1 再加）、参数 preset 保存、并发回测

## Capabilities

### New Capabilities
- `backtest-ui`: 回测 Web UI 页面（参数表单 + 提交 + 指标卡 + NAV 折线图）

### Modified Capabilities
无

## Impact

- 受影响代码：
  - 新增：`frontend/src/api/backtest.ts`（typed 客户端：`runBacktest` / `getBacktestRun` / `getBacktestNav`）
  - 新增：`frontend/src/stores/backtest-store.ts`（zustand store：状态机 + 当前 run + 当前 NAV）
  - 新增：`frontend/src/components/backtest/BacktestForm.tsx`（表单：ETF 池多选 + 7 个参数）
  - 新增：`frontend/src/components/backtest/MetricsCards.tsx`（6 张指标卡）
  - 新增：`frontend/src/components/backtest/NavChart.tsx`（recharts 折线图）
  - 新增：`frontend/src/components/backtest/FormError.tsx`（422 错误展示）
  - 新增：`frontend/src/pages/BacktestPage.tsx`（页面装配：表单在上、结果在下）
  - 修改：`frontend/src/App.tsx`（新增 `<Route path="backtest" />`）
  - 修改：`frontend/src/layouts/Layout.tsx`（navItems 插入"回测"）
  - 修改：`frontend/package.json`（新增 `recharts` 依赖）
- 新增依赖：`recharts`（~85KB gzipped，声明式 React 图表，主页唯一图表组件）
- 不影响后端、不影响其它前端页面
- 数据契约完全复用 `rest-api` 已交付的三个端点
