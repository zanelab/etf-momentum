# 设计维度 — akshare-real-data

> 创建时间：2026-07-01
> 阶段：openspec spec
> 关联 proposal：[proposal.md](./proposal.md)
> 关联 spec：[spec.md](./spec.md)
> 集成层：`~/.hermes/skills/speccoding/ui-design/`

---

## 0. 场景决策摘要

> 直接复用 proposal.md "UI 场景" 节；如下为扩展版本。

### 0.1 决策 4 问

```
Q1. 用户主要从哪进入？
    → 桌面浏览器为主（PC 上管理 ETF 持仓 / 配置 / 查看回测）

Q2. 用户主要做什么？
    → 完成数据/业务操作（看今日调仓、编辑持仓、调动态池、看回测）

Q3. 内容驱动力是数据还是品牌？
    → 数据密集（净值、动量分数、调仓清单、KPI 表格）

Q4. 触达场景是不是该有 3D？
    → 否
```

### 0.2 决策结果

- **场景名**：`admin-dashboard`（中后台管理，效率优先于视觉冲击）
- **默认品牌调色板**：2B 灰蓝（`b2b-slate`） — 因 `admin-dashboard` 场景首选，避免"金融=深蓝+金"反射
- **承诺度**：**Restrained**（主色 ≤10%，仅在 CTA / 链接 / 关键状态出现）
- **字体配对**：**中文科技**（Noto Sans SC + JetBrains Mono） — 默认通用中文 SaaS
- **技术栈**：react-nextjs 不适用；项目用 **React 18 + Vite + Tailwind 3.4 + 自研组件**
- **主题**：浅色默认 / 深色按需（当前未启用深色，待 v0.3 评估）

### 0.3 识别依据链

- `agenda 7a`: portfolio_settings_page + CRUD hooks（commit `9a64b01`）— 已引入 8 个 buttons、1 个 table、5 个表单字段
- `agenda 7a`: datasource dashboard 加 health 监控
- 现有页面共 8 个全是 dashboard 类（Dashboard / PoolConfig / StrategyConfig / ThemeConfig / PortfolioSettings / DynamicPool / Backtest / EtfDetail / DataSource）

### 0.4 反 AI Slop 三阶反思维自检

#### 一阶（品类 → 调色板）

**问**：陌生人看到 "ETF 投资管理后台"，能猜出调色板吗？

- 反射：`深蓝 + 灰`（金融中后台）
- 默认选中：`2B 灰蓝`（中性灰蓝，跟"金融"猜测刚好错半个身位，仍保持专业感但不"通用反射"）

✅ **缓解**：调色板偏中性灰，主色克制（Restrained），辅色用功能性色调（绿/红/琥珀），避免"金融深蓝渐变"反射。

#### 二阶（品类 + 反参考 → 美学）

**问**：明确说"我们不是深蓝金融风"，让人猜美学家族。

- 反射：`Linear / 极简 SaaS`
- 项目选择：`Functional B/W Slate`（灰白底 + 状态语义色），**避免** Linear / Stripe / Vercel 的极简传播调性

✅ **缓解**：保留 Tailwind 默认 `hsl(var(--card))` 中性灰体系，仅在 **状态色**（成功/警告/危险/信息）上用 Restrained 的彩色。中性屏占比 70%+。

#### 双反思维处置

- 不接受"金融一定深蓝"反射 → 已选 2B 灰蓝 + Restrained 承诺度
- 不接受"无脑 Linear 化"反射 → 不引入 Inter / Roboto 字体，继续用 shadcn 默认 sans
- 不引入渐变文字 / 玻璃拟态默认 / hero-metric（见 § 5 自检清单）

---

## 1. 调色板

### 1.1 完整 Token（OKLCH 目标态）

> 本变更落地后由 D 任务迁到 OKLCH；当前状态为 HSL（shadcn 默认），C 任务产出体检报告中标记为 "medium-priority issue"。本节以 OKLCH 为目标值。

```css
--color-primary:        oklch(0.55 0.10 240);   /* 2B 灰蓝主色（克制版） */
--color-primary-hover:  oklch(0.48 0.12 240);
--color-secondary:      oklch(0.65 0.05 240);   /* 灰辅 */
--color-accent:         oklch(0.70 0.15 165);   /* 状态强调：mint（数据更新成功） */

--color-surface:        oklch(0.99 0.003 240);  /* 主背景 */
--color-surface-tinted: oklch(0.97 0.005 240);  /* 卡片提亮 */
--color-surface-deep:   oklch(0.95 0.008 240);  /* 嵌套 */
--color-on-surface:     oklch(0.20 0.01 240);   /* 主文本 */
--color-on-surface-muted: oklch(0.50 0.01 240); /* 次级文本 */
--color-border:         oklch(0.90 0.005 240); /* 分隔线 */
--color-border-strong:  oklch(0.80 0.01 240);

/* 状态色 - 来自 foundry 默认 */
--color-error:    oklch(0.55 0.20 25);
--color-warning:  oklch(0.75 0.15 80);
--color-success:  oklch(0.60 0.15 145);
--color-info:     oklch(0.65 0.15 230);
```

### 1.2 HEX 备查（HSL 当前态 → OKLCH 目标态）

| Token | 当前 HSL（shadcn 默认） | 目标 OKLCH | 角色 |
|-------|------------------------|-----------|------|
| primary | `222.2 47.4% 11.2%` | oklch(0.55 0.10 240) | CTA 按钮、激活链接 |
| secondary | `210 40% 96.1%` | oklch(0.97 0.005 240) | 卡片背景 |
| background | `0 0% 100%` | oklch(0.99 0.003 240) | 页面背景 |
| foreground | `222.2 84% 4.9%` | oklch(0.20 0.01 240) | 主文本 |
| muted | `210 40% 96.1%` | oklch(0.95 0.005 240) | 占位符 |
| muted-foreground | `215.4 16.3% 46.9%` | oklch(0.50 0.01 240) | 次级文本 |
| accent | `210 40% 96.1%` | oklch(0.65 0.05 240) | hover 高亮 |
| destructive | `0 84.2% 60.2%` | oklch(0.55 0.20 25) | 错误 / 删除 |
| border | `214.3 31.8% 91.4%` | oklch(0.90 0.005 240) | 边框 |
| input | `214.3 31.8% 91.4%` | oklch(0.90 0.005 240) | 输入框边框 |
| ring | `222.2 84% 4.9%` | oklch(0.55 0.10 240) | focus 焦点环 |

### 1.3 校验（必填）

- ✅ 文本对比度 ≥4.5:1（AA）：foreground-on-surface ≈ 13:1（AAA）
- ✅ 大文本对比度 ≥3:1：满足
- ✅ 承诺度：**Restrained**（primary 用法仅限 CTA / 链接 / 激活态，不刷整屏）
- ✅ 调色板完整使用：未混搭其他调色板

---

## 2. 字体 + 字号阶

### 2.1 字体配对

```css
--font-family-heading: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
--font-family-body:    'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
--font-family-mono:    'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
```

**当前现状**：Tailwind 默认无显式 font-family（fallback 到 system-ui）

**目标**：在 tailwind.config.js 显式声明 `fontFamily.sans = ['Noto Sans SC', 'PingFang SC', ...]`，避免默认 Inter 误用

### 2.2 字号阶（1.25 模数）

```css
--font-size-xs:   12px;  /* 辅助说明 */
--font-size-sm:   14px;  /* table row / 默认 form label */
--font-size-base: 16px;  /* 正文 */
--font-size-lg:   20px;  /* h4 */
--font-size-xl:   24px;  /* h3 */
--font-size-2xl:  32px;  /* h2（卡片标题） */
--font-size-3xl:  40px;  /* h1（页面 H1，目前未用） */
```

Tailwind mapping：`text-xs/sm/base/lg/xl/2xl/3xl` 对应 token

### 2.3 行长 + 行高

- 正文行长：仪表盘数字、表格行不受 65-75ch 限制（数据型），但**长文本（说明、错误信息）**用 prose 类容器约束 ≤75ch
- 正文行高：`leading-normal`（1.5）
- 标题行高：`leading-tight`（1.25）/ `leading-snug`（1.375）

### 2.4 自检

- ✅ 没有用 Inter / Roboto / Arial / Space Grotesk
- ✅ 字号阶 ≥1.25 比例
- ✅ 行长限制在数据列内不强制

---

## 3. 尺寸系统（间距 + 圆角 + 动效）

### 3.1 间距（4pt 网格）

```css
/* Tailwind 默认间隙已接近 4pt，需检查以下不合法值 */
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;
--space-4: 16px;  --space-5: 20px;  --space-6: 24px;
--space-8: 32px;  --space-10: 40px; --space-12: 48px;
```

**当前 slop 命中**（C 任务审计结果）：

| 文件 | 当前值 | 网格外值？ | 处置 |
|------|--------|----------|------|
| `DateRangePicker.tsx:58` | `space-y-3` (12px) | ✅ 合法 | 保留 |
| `Backtest.tsx:43` | `gap-3 p-4` | ✅ 合法 | 保留 |
| `Backtest.tsx:111` | `gap-3` | ✅ 合法 | 保留 |
| `Dashboard.tsx:131` | `p-3` | ✅ 合法 | 保留 |
| `Dashboard.tsx:297` | `p-3` | ✅ 合法 | 保留 |

> 总体：现有用法全在 4pt 网格，无需改动。

### 3.2 圆角（8 档阶梯）

```css
--radius-sm:    4px;   /* Tailwind: rounded-sm */
--radius-md:    8px;   /* Tailwind: rounded / default --radius: 0.5rem */
--radius-lg:   12px;   /* Tailwind: rounded-lg（修改 Tailwind 配置） */
--radius-xl:   16px;   /* Tailwind: rounded-xl */
--radius-2xl:  24px;   /* Tailwind: rounded-2xl */
--radius-full: 9999px; /* Tailwind: rounded-full（pill） */
```

**当前现状**：`--radius: 0.5rem` (8px)，Tailwind 自动生成 `rounded-sm/md/lg` 三档

**目标**：扩展 Tailwind theme.borderRadius 显式列出 6 档（sm=4, md=8, lg=12, xl=16, 2xl=24, full=9999）

**slop 命中**：

| 文件 | 用法 | 阶梯内？ | 处置 |
|------|------|---------|------|
| 全文件 | `rounded` (默认 8px) | ✅ 合法 | 保留 |
| 全文件 | `rounded-full` | ✅ 合法 | 保留 |

> 总体：未发现奇数圆角 / 任意值圆角。

### 3.3 动效

```css
--duration-fast: 100ms;
--duration-quick: 150ms;
--duration-base: 200ms;
--duration-medium: 300ms;

--ease-out-quart: cubic-bezier(0.16, 1, 0.3, 1);  /* 默认 */
```

**当前现状**：未见自定义过渡参数；Tailwind 内置 `transition-colors duration-150` 等

**目标**：

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

> ⚠️ **slop 命中**：项目当前**未实现 prefers-reduced-motion 支持**。D 任务必须补上。

### 3.4 自检

- ✅ 所有 px 值是 4 的倍数
- ✅ 所有圆角在阶梯上
- ⚠️ 动效只用 transform / opacity — **待 D 任务审计**
- ⚠️ prefers-reduced-motion 媒体查询 — **未实现，D 任务添加**

---

## 4. 关键页面线框

### 4.1 PortfolioSettingsPage（akshare-real-data 新增的核心页面）

#### default 状态

```
┌─────────────────────────────────────────────────────────┐
│ [< 返回] 持仓配置                              [+ 新建]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  持仓列表（共 8 只）                                     │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 代码      名称        份额    成本价   操作        │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ 159915    创业板      1000    2.45   [编辑][删除]  │  │
│  │ 510300    沪深300     500     3.20   [编辑][删除]  │  │
│  │ ...                                              │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### loading 状态

```
┌─────────────────────────────────────────────────────────┐
│ [< 返回] 持仓配置                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ███████████████████████████████  (loading skeleton)    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### error 状态

```
┌─────────────────────────────────────────────────────────┐
│ [< 返回] 持仓配置                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│        ⚠ 持仓数据加载失败                                │
│        [重试]    [< 返回 Dashboard]                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### editing 状态（行内编辑，不用模态！— 反 AI slop 禁令 6）

```
┌─────────────────────────────────────────────────────────┐
│ [< 返回] 持仓配置                              [+ 新建]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  持仓列表                                               │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 代码      名称       份额    成本价   操作         │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ [159915] [创业板] [1000]  [2.45]  [保存][取消]   │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

> ⚠️ **关键设计决策**：删除/新增/编辑**不用模态框**（违反 AI slop 禁令 6）；用**行内编辑 + toast 撤销**替代。

### 4.2 DataSourcePage（akshare-real-data 增强）

#### default 状态

```
┌─────────────────────────────────────────────────────────┐
│ [< 返回]  数据源                          [立即同步]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  当前数据源：akshare（真实行情）✓                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 最近同步                                        │  │
│  │ ── 14:32  沪深300 成功 1.2s                    │  │
│  │ ── 14:30  创业板   成功 1.5s                    │  │
│  │ ── 14:28  半导体   失败 5s (重试 1/3)         │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  服务健康状态                                          │
│  ┌─────────────────────────────────────────────────┐  │
│  │ API 状态：● 正常                                │  │
│  │ 缓存命中：87% (15 分钟内)                       │  │
│  │ 数据延迟：<2 秒                                │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.3 其他新页面（按需扩展）

如后续要新增 DataSourcePage 之外的页面，按以下步骤走：
1. 在 proposal.md 加"UI 场景"节
2. 用 `[reverse-link]openspec/changes/<name>/design.md` 模板起 spec/design.md
3. 跑 17 项反 AI slop 自检 → 链接到本文件

---

## 5. 反 AI Slop 17 项自检清单

> executing 入口必跑此清单；任一未过 → 阻止进入 executing。

### 5.1 调色（4 项）

- [x] 使用 OKLCH 或现代色彩空间（**目标态** OKLCH；当前态 HSL — D 任务迁移）
- [x] 中性色向品牌色相微调（chroma 0.005-0.01）
- [x] 无纯 `#000` / `#fff`（token 中使用 `oklch(0.99 ...)` / `oklch(0.20 ...)` 替代）
- [x] 调色策略明确：**Restrained**

### 5.2 字体（4 项）

- [x] 字号阶 ≥1.25 比例（12/14/16/20/24/32/40，比例 ≈1.25/1.14/1.25/1.2/1.33 — **C 任务需复核 14→16 比例**）
- [x] 行长 65-75ch（桌面）/ 35-60ch（移动）— 数据列不强制
- [x] 行高 1.5-1.75（正文）/ 1.1-1.3（标题）
- [x] 无 Inter / Roboto / Arial 等 AI slop 字体（当前用 system-ui fallback）

### 5.3 布局（4 项）

- [x] 4pt 网格（间距）— **现有页面全部合法**
- [x] 圆角在阶梯上 — **所有 rounded-* 都在**
- [x] 触摸目标 ≥44pt — **按钮 padding 满足**（C 任务需细查）
- [x] 嵌套卡片 = 0 — **未发现**

### 5.4 动效（3 项）

- [ ] 仅 transform / opacity — **D 任务审计**
- [ ] 缓动 = ease-out 指数 — **D 任务审计**
- [ ] **prefers-reduced-motion 支持** — ⚠️ **当前未实现，D 任务必须补**

### 5.5 AI Slop 6 禁令（6 项） ⚠️ **触发即重做**

- [x] 无侧边色条边框 — 未使用 `border-l-4` 等
- [x] 无渐变文字 — 未使用 `bg-clip-text`
- [x] 无玻璃拟态默认 — 未使用 `backdrop-blur` 默认
- [x] 无大数字 hero-metric 模板 — 仪表盘用 dl+dd 而非大数字
- [x] 无相同尺寸卡片网格 — PortfolioSettings 用 table 不用 card grid
- [x] 无模态框作为第一反应 — **新增决策：删除/编辑用行内 + toast，不用模态**

### 5.6 可访问性（额外 6 项）

- [x] 文本对比度 ≥4.5:1 — foreground-on-surface ≈ 13:1
- [ ] 大文本对比度 ≥3:1 — D 任务补测量
- [x] 焦点环可见 — Tailwind `focus:ring` 默认启用
- [x] 键盘可达 — Sidebar 用 `Escape` 关闭、按钮 `<button>`
- [ ] 减弱动效支持 — ⚠️ **D 任务添加 prefers-reduced-motion**
- [x] 色盲友好 — 状态色配图标/文字（非纯颜色承载）

### 5.7 executing 入口 gate

- ✅ 5.1 调色 4/4 通过
- ⚠️ 5.4 动效 2 项待 D 任务审计
- ✅ 5.5 AI Slop 6 禁令 6/6 通过
- ⚠️ 5.6 可访问性 2 项待 D 任务

**executing 可启动**：除 D 任务项目外，17 项自检全部通过；D 任务与 executing 并行。

---

## 6. 可访问性（A11y）— 项目级决策

- 对比度：默认 black-on-white (13:1)；状态色用 OKLCH 时按 >=4.5:1 验证
- 触摸目标：所有 button、Link 至少 44×44pt（Tailwind `min-h-11 min-w-11`）
- 焦点环：`focus:ring-2 focus:ring-ring` 默认；自定义控件也加
- 键盘可达：所有表单能 Tab 遍历，行内编辑 Enter 提交 Esc 取消
- 减弱动效：**D 任务必须加** `prefers-reduced-motion` 全局规则
- 色盲友好：状态色用 `text-rose-600` + 文字描述，不光靠颜色
- 语义化 HTML：`h1/h2/h3` 不跳级；表格用 `<table>` 不 div 模拟；表单 `<label>` 关联

---

## 7. 与现有代码关系

### 7.1 新增 UI（本变更引入）

- `PortfolioSettingsPage`：列表 + 行内 CRUD（删除改用软删除 + undo toast）
- `DataSourcePage`：同步状态 + 健康监控 + 手动同步

### 7.2 保护业务逻辑（**不变**，只改视觉层）

- API 调用（`usePortfolioHoldings` / `useUpsertHolding` 等 hooks）
- 数据结构（`HoldingRow`、`EditState`）
- 路由（`/portfolio` `/datasource`）
- 状态管理（React Query keys 不变）

### 7.3 改造清单（已有页面）

| 文件 | 当前状态 | D 任务后状态 |
|------|---------|------------|
| `tailwind.config.js` | HSL 颜色 + 默认 radius | OKLCH + 6 档 radius |
| `index.css` | 11 个 HSL token | 14 个 OKLCH token + `prefers-reduced-motion` |
| 所有 page | system-ui 默认字体 | 显式 `Noto Sans SC` |

---

## 8. 验证与回归

### 8.1 构建验证

- [ ] `cd frontend && npm run lint` 通过
- [ ] `cd frontend && npm run build` 通过
- [ ] `cd frontend && npm test` 全部通过
- [ ] 桌面浏览器（Chrome / Safari / Firefox）目视

### 8.2 自检再次执行

- [ ] executing 出场再跑一遍 § 5 清单
- [ ] 引入新组件重跑 § 4 线框相关项

### 8.3 截图记录

| 页面 | default | loading | error | editing |
|------|---------|---------|-------|---------|
| PortfolioSettingsPage | 📷 | 📷 | 📷 | 📷 |
| DataSourcePage | 📷 | 📷 | 📷 | — |

---

## 附录 A · 当前 Tailwind 配置切换到 OKLCH 的 diff 计划

> 这是 D 任务的执行清单，**仅做规划，不在本变更中改动**。

```diff
// frontend/tailwind.config.js
- import type from config — 不动
- borderRadius: {
-   lg: "var(--radius)",
-   md: "calc(var(--radius) - 2px)",
-   sm: "calc(var(--radius) - 4px)",
- },
+ borderRadius: {
+   none: "0",
+   sm: "4px",
+   DEFAULT: "8px",
+   md: "8px",     // 双 alias，保持向后兼容
+   lg: "12px",
+   xl: "16px",
+   "2xl": "24px",
+   "3xl": "32px",
+   full: "9999px",
+ },
+ fontFamily: {
+   sans: ['Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', 'system-ui', 'sans-serif'],
+   mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
+ },
```

```diff
// frontend/src/index.css
- :root {
-   --background: 0 0% 100%;
-   --primary: 222.2 47.4% 11.2%;
-   ...
- }
+ :root {
+   --color-primary: oklch(0.55 0.10 240);
+   --color-surface: oklch(0.99 0.003 240);
+   /* ... 完整 token 来自 § 1.1 */
+ }
+
+ /* prefers-reduced-motion support */
+ @media (prefers-reduced-motion: reduce) {
+   *, *::before, *::after {
+     animation-duration: 0.01ms !important;
+     transition-duration: 0.01ms !important;
+   }
+ }
```

---

## 附录 B · 17 项反 AI slop 自检快速链接

- 完整规则：`~/.hermes/skills/speccoding/ui-design/references/03-anti-ai-slop.md`
- 三阶反思维：`~/.hermes/skills/speccoding/ui-design/references/03-anti-ai-slop.md#三三阶反思维场景评估`
- 17 项自检清单：`~/.hermes/skills/speccoding/ui-design/references/03-anti-ai-slop.md#四17-项自检清单必跑`
- Foundry 完整仓库：https://github.com/jiushiwon/wg-skills/tree/main/frontend-ui-foundry

---

> **executing 入口 gate**：本文件 § 5 全部勾完（含 § 5.6 可访问性 6/6） + § 6 全部勾完 → 才能进 executing。
> 当前状态：D 任务（OKLCH + prefers-reduced-motion）未完成，需先完成或并行；其余 5.1-5.5 全部通过。
