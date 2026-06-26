## Context

- `rest-api` 已合并到 main：4 个 backtest 端点
  - `POST /api/v1/backtest` — 提交参数 + ETF 池 → 同步执行 → 返回 BacktestRun JSON
  - `GET /api/v1/backtest/{id}` — 详情（含 metrics）
  - `GET /api/v1/backtest/{id}/nav` — NAV 序列
  - `GET /api/v1/backtest` — 列表（v1.1 用，本期不接）
- 既有 `frontend-vite-react-scaffold` 与 `frontend-dashboard` 已就位：vite/react/ts/zustand/tailwind/lucide 齐全
- 既有模式：typed apiGet/apiPost + zustand store（`idle|loading|ok|error`）+ Tailwind + 颜色徽章
- 后端 `run_backtest` 是同步阻塞 + 读 DB，对 1 年数据单次回测 < 1s；用户感知 loading < 3s 可接受

## Goals / Non-Goals

**Goals:**
- 用户在浏览器表单选 ETF 池 + 参数 → 一键跑回测
- 看到 6 个业绩指标（年化、最大回撤、夏普、Sortino、Calmar、总收益）
- 看到 NAV 折线图（X 轴日期、Y 轴 NAV，自动适应容器宽度）
- 422 错误以字段级提示（不影响其它字段）
- 后端错误以页面级红色卡提示

**Non-Goals:**
- 历史回测列表（v1.1）
- 参数 preset 保存
- 并发回测 / 后台任务
- 调仓明细表（rebalance_log）
- 修改后端任何代码

## Decisions

### 1. 图表库：Recharts
- 选用 Recharts（声明式 React，TypeScript 友好，~85KB gzipped）
- 替代方案：(a) 纯 SVG：100+ 行手写坐标轴/刻度/响应式，不值；(b) chart.js + react-chartjs-2：体积相近但非 React 范式
- Recharts 的 `LineChart` + `XAxis` + `YAxis` + `Tooltip` + `ResponsiveContainer` 正好覆盖需求；接受 ~85KB 增量换开发速度

### 2. 表单状态：本地 React state，不用 react-hook-form
- 8 个字段 + 错误展示，state 结构简单；`useState` 即可
- 替代方案 react-hook-form：性能好但 API 重，本期 8 字段不必要
- 校验在 submit 时跑：empty pool / start>end / lookback<1 / skip<0 / top_n<1

### 3. ETF 池选择器：checkbox 网格（限速 12 个）
- 后端 `/etfs?limit=500` 拉全市场（实际 100-200 只）
- 用原生 `<input type="checkbox">` 网格（4 列）展示前 12 个 + 搜索框过滤
- 替代方案：(a) native `<select multiple>`：UX 差；(b) headless listbox 库：增加复杂度
- 已选数量实时显示在标题旁（"已选 3 / 12"）

### 4. 提交流程：单次 fetch + 同步返回 metrics
- 后端 POST /backtest 已同步返回完整 BacktestRun JSON（含 metrics）
- 但 **不含 nav_series**（避免大 payload），nav_series 需 `GET /backtest/{id}/nav` 二次拉
- store 状态机：`idle → submitting → (ok | error)`，ok 后自动 `fetchNav(id)`：`loading-nav → nav-ok | nav-error`
- 不并行发起两请求（metrics 必含 id 才知道拉哪个 nav）

### 5. NAV 渲染：日期为 string，X 轴用 ISO date
- 后端 `nav_series: [{date, nav}, ...]`，`date` 是 ISO string，`nav` 是 string（Decimal）
- 图表用 `<LineChart data={points}>`，每点 `{ date, nav, displayDate: 'YYYY-MM-DD' }`
- Y 轴用 `Number(nav).toLocaleString()` 保留千分位
- 数据点超 1000 时 Recharts 自动采样（不开 isAnimationActive 避免长动画）

### 6. 业绩指标渲染：6 张 MetricCard
- 与 DashboardPage 的 SummaryCards 风格一致（grid + 卡片）
- 总收益 / 年化 / 最大回撤：百分比格式 `Number(decimal).toFixed(2) + '%'`
- 夏普 / Sortino / Calmar：保留 3 位小数；null 显示 `—`

## Risks / Trade-offs

- [Risk] 后端同步回测在长区间（5 年）下可能 > 3s，前端 loading 期间用户可能重复点击 → [Mitigation] 提交时禁用 submit 按钮 + 表单字段；store 提交期 status='submitting'，UI 渲染 spinner
- [Risk] `GET /etfs` 返回 500 时整个页面无法填池 → [Mitigation] 池加载失败时表单显示"ETF 字典加载失败"并禁用 submit
- [Risk] 422 错误中 `detail` 可能是 FastAPI list-of-violations（路径/messages 嵌套），字段级提取需容错 → [Mitigation] 写一个 `extractFieldErrors(detail)` 工具函数，能取到 `loc[1]`（字段名）+ `msg`；取不到时全部归到 "form" 通用错误
- [Risk] Recharts 在 jsdom 下的 ResponsiveContainer 默认 width=0 height=0，测试渲染时 SVG 不出 → [Mitigation] 测试用 `width={500} height={300}` 硬编码 prop + 断言 `<path>` 存在而不是用 `toMatchSnapshot` 像素比对
- [Risk] Decimal string → Number 转换有精度损失（金融场景）→ [Mitigation] 仅用于显示/绘图，不参与计算；后端是 source of truth
- [Risk] 池中含退市 ETF（无 close）时后端 422 → [Mitigation] 后端已返回 missing codes 在 detail 中；前端用通用错误卡 + 显示 detail 全文

## Open Questions

- 折线图 Y 轴是否加"基准对比线"（等权持有基准）？**决定**：v1.0 不做
- 跑完回测后是否自动清空表单？**决定**：不清空，方便用户微调参数再跑（diff 体验）
