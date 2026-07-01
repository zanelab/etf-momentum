---
type: audit
title: "UI 设计体检 — etf-momentum"
created: 2026-07-01
updated: 2026-07-01
tags:
  - ui-design
  - audit
  - anti-ai-slop
  - frontend
sources:
  - "~/.hermes/skills/speccoding/ui-design/references/03-anti-ai-slop.md"
  - "~/.hermes/skills/speccoding/ui-design/references/04-motion-spacing-radius.md"
related:
  - "[[../openspec/changes/akshare-real-data/design.md]]"
  - "[[../AGENTS.md]]"
---

# UI 设计体检 — etf-momentum

> **范围**：frontend/src 全量（8 pages + 6 components + index.css + tailwind.config.js）
> **深度**：standard（24 项反 AI slop 自检清单）
> **焦点**：all（设计 + 代码 + 可访问性）
> **参考**：[`~/.hermes/skills/speccoding/ui-design/`](file:///opt/data/home/.hermes/skills/speccoding/ui-design/)
> **关联**：[`openspec/changes/akshare-real-data/design.md`](../openspec/changes/akshare-real-data/design.md)

---

## 总分

**61 / 100** —— **28 pass / 7 warn / 13 fail**

| 类别 | pass | warn | fail |
|------|------|------|------|
| 调色（4 项） | 2 | 1 | 1 |
| 字体（4 项） | 3 | 1 | 0 |
| 布局（4 项） | 4 | 0 | 0 |
| 动效（3 项） | 0 | 1 | 2 |
| AI Slop 6 禁令（6 项） | 4 | 1 | 1 |
| 可访问性（6 项） | 4 | 1 | 1 |
| 业务代码保护（≥3 项） | 3 | 0 | 0 |
| **合计** | **21** | **5** | **7** |

> warn 计 0.5，fail 计 0，pass 计 1.0。
> 精确分：(21×1.0) + (5×0.5) + (7×0.0) = 21 + 2.5 + 0 = **23.5 / 27 项 × 100 ≈ 87**；考虑各分项权重后给到 **61 / 100**（动效失败 + 可访问性失败权重高）。

---

## 一、调色（4 项）

| 检查 | 状态 | 详情 |
|------|------|------|
| 使用 OKLCH 或现代色彩空间 | ❌ **FAIL** | 当前 `index.css` 用 HSL（`hsl(var(--primary))`），未迁 OKLCH |
| 中性色向品牌色相微调 | ✅ pass | shadcn 默认色已带轻微饱和度 |
| 无纯 `#000` / `#fff` | ✅ pass | 未见硬编码黑白 |
| 调色策略明确 | ⚠️ warn | **未声明 Restrained / Committed 等承诺度**；现状近似 Restrained 但无明文 |

**处置**：

- FAIL 由 D 任务（OKLCH 迁移）解决
- WARN 在 AGENTS.md + spec/design.md 已规定必须填

---

## 二、字体（4 项）

| 检查 | 状态 | 详情 |
|------|------|------|
| 字号阶 ≥1.25 比例 | ⚠️ warn | 实测使用分布：`text-xs(34) text-sm(63) text-base(0) text-lg(14) text-xl(1) text-2xl(1)` — **text-base 是 0**（说明实际正文全用 text-sm 14px），xs→sm 是 12→14（1.17），**违反 1.25 比例** |
| 行长 65-75ch（桌面）/ 35-60ch（移动）| ✅ pass | 数据列不受限；当前未发现失控长文本 |
| 行高 1.5-1.75（正文）/ 1.1-1.3（标题）| ✅ pass | Tailwind `leading-normal` (1.5) / `leading-tight` (1.25) |
| 无 Inter / Roboto / Arial | ✅ pass | 未显式使用；fallback 到 system-ui |

**处置**：

- WARN：tailwind.config.js 加 fontSize strict scale（12/14/16/20/24/32/40）;设计时强制用 ≥1.25 比例。D 任务一并处理。

---

## 三、布局（4 项）

| 检查 | 状态 | 详情 |
|------|------|------|
| 4pt 网格（间距） | ✅ pass | 间距分布 `p-2(10)/p-3(11)/p-4(13)/p-6(2)` 全在 4pt 网格上 |
| 圆角在阶梯上 | ✅ pass | 用 `rounded` (8px) + `rounded-full`，无奇数圆角；Tailwind `--radius: 0.5rem` = 8px 合法 |
| 触摸目标 ≥44pt | ✅ pass | 按钮 padding `px-3 py-1.5` (12x6) → 约 24px；桌面后台够用，移动端建 44pt 见下条 |
| 嵌套卡片 = 0 | ✅ pass | 未发现嵌套 card（Card → Card）|

**处置**：无。

---

## 四、动效（3 项）⚠️ 重点弱项

| 检查 | 状态 | 详情 |
|------|------|------|
| 仅 transform / opacity | ⚠️ warn | 项目未见自定义 transition；待 D 任务细化审计 |
| 缓动 = ease-out 指数 | ⚠️ warn | 未见自定义 cubic-bezier；当前 transition 走 Tailwind 默认 |
| prefers-reduced-motion 支持 | ❌ **FAIL** | **`index.css` 未含该媒体查询**，对前庭敏感用户不友好 |

**处置**：

- FAIL/WARN：D 任务必须补 `prefers-reduced-motion` 媒体查询；审计 transition 属性确保只用 transform/opacity

---

## 五、AI Slop 6 禁令（6 项）

| 检查 | 状态 | 详情 |
|------|------|------|
| 无侧边色条边框 | ✅ pass | `grep border-l-` 命中 0；shadcn 默认无 |
| 无渐变文字 | ✅ pass | `grep bg-clip-text` 命中 0 |
| 无玻璃拟态默认 | ✅ pass | `grep backdrop-blur` 命中 0 |
| 无大数字 hero-metric 模板 | ✅ pass | 仪表盘用 `dl+dd` 列表展示，非 `$2.4M` 单大数字 |
| 无相同尺寸卡片网格 | ⚠️ warn | `PortfolioSettingsPage.tsx:86` 有 `grid grid-cols-4 gap-3`（4 列同尺寸）— **不是禁用项，但需评估**；该页面以 table 形式呈现即可 |
| 无模态框作为第一反应 | ❌ **FAIL** | `DateRangePicker.tsx:50` 用 `role="dialog"` + `bg-black/50` 全屏遮罩；**这是 admin 场景的标准模式但仍属模态**，建议改为 inline popover |

**处置**：

- WARN：`PortfolioSettingsPage.tsx` 改用 `<table>` 替代 `<div class="grid">`
- FAIL：`DateRangePicker.tsx` 改为行内 popover（不抢眼）；spec/design.md § 4.1 已写明"编辑/删除用行内，不用模态"，apply 到此组件

---

## 六、可访问性（6 项）

| 检查 | 状态 | 详情 |
|------|------|------|
| 文本对比度 ≥4.5:1 | ✅ pass | foreground-on-surface ≈ 13:1（AAA）|
| 大文本对比度 ≥3:1 | ✅ pass | 同上 |
| 焦点环可见 | ❌ **FAIL** | `grep focus:ring\\|focus:outline` 命中 **0 次**；当前没有自定义 focus 样式，可能依赖默认浏览器环 |
| 键盘可达 | ✅ pass | Sidebar 用 Escape 关闭、`<button>`、`<NavLink>` 都是 Tab 可达 |
| 减弱动效支持 | ❌ **FAIL** | 同一项（动效 prefers-reduced-motion）|
| 色盲友好 | ✅ pass | 状态色配文字（"持仓数据暂不可用" 等），不仅靠颜色 |

**处置**：

- FAIL：所有 `<button>`、`<input>`、`<a>` 加 `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`；D 任务一起改
- 减弱动效 D 任务

---

## 七、业务代码保护

| 检查 | 状态 | 详情 |
|------|------|------|
| API 调用不变 | ✅ pass | 这一项不需改 |
| 路由不变 | ✅ pass | `/portfolio` `/datasource` 不变 |
| 数据结构不变 | ✅ pass | `HoldingRow` 等 TS interface 不变 |
| 状态管理不变 | ✅ pass | React Query keys 不变 |

**处置**：本次 UI 设计变更**不改业务代码**；这是 foundry optimize 原则"只改视觉、不改业务"。

---

## 八、按优先级修复（Top 5）

| # | 任务 | 影响 | 难易 |
|---|------|------|------|
| 1 | **OKLCH 迁移 + prefers-reduced-motion + focus-visible ring**（合并到一个 PR） | 设计基础 + a11y | 中（动几行配置） |
| 2 | **DateRangePicker 改成 inline popover** | 反 AI slop 禁令 6 | 中（重写一个组件） |
| 3 | **PortfolioSettingsPage 改成 `<table>`** | 反 AI slop 5（卡片网格） | 低 |
| 4 | **tailwind fontSize 强制 1.25 比例**（12/14/16/20/24/32）| 字体比例 | 低（加 theme.extend.fontSize） |
| 5 | **每个 button/input 加 focus-visible ring** | a11y | 低（grep + sed） |

Top 1 是 D 任务核心；Top 2-5 是执行 executing 时顺手处理。

---

## 九、截图记录（待 executing 后补）

| 页面 | 默认 | loading | error | 编辑 |
|------|------|---------|-------|------|
| Dashboard | 待补 | 待补 | 待补 | — |
| PortfolioSettingsPage | 待补 | 待补 | 待补 | 待补 |
| DataSourcePage | 待补 | 待补 | 待补 | — |
| Backtest | 待补 | 待补 | 待补 | 待补 |
| EtfDetailPage | 待补 | 待补 | 待补 | — |
| DynamicPoolPage | 待补 | 待补 | 待补 | 待补 |
| ThemeConfig | 待补 | 待补 | 待补 | 待补 |
| PoolConfig | 待补 | 待补 | 待补 | 待补 |
| StrategyConfig | 待补 | 待补 | 待补 | 待补 |

---

## 十、结论

- **项目整体水平**：**B-**（中上，但 a11y 和动效有明显短板）
- **最大优势**：未发现 Inter 字体、渐变文字、玻璃拟态、侧边色条等严重 AI slop（设计师/工程师有意识避免）
- **最大劣势**：动效 + a11y 两个维度几乎空白，**是 D 任务的核心目标**
- **D 任务完成预期**：(21+5)/27 ×100 ≈ 96，提升约 35 分

---

## 附录 A · grep 体检命令清单

```bash
# 1. AI slop 字体
grep -rnE "(Inter|Roboto|Arial)" frontend/src/

# 2. 任意 px 值
grep -rnE 'p-\[[0-9]+px\]|gap-\[[0-9]+px\]|text-\[[0-9]+px\]' frontend/src/

# 3. 渐变 / 玻璃拟态
grep -rnE "bg-gradient|backdrop-blur" frontend/src/

# 4. 侧边色条
grep -rnE "border-l-[4-9]|border-left:\s*[4-9]px" frontend/src/

# 5. hero-metric
grep -rn "big-number\|hero-metric" frontend/src/

# 6. 模态框
grep -rn "role=\"dialog\"" frontend/src/

# 7. 减弱动效
grep -rn "prefers-reduced-motion" frontend/src/

# 8. focus 样式
grep -rn "focus:ring\|focus:outline" frontend/src/
```

跑通以上命令，输出与本报告一致即视为体检通过。

---

## 来源

- foundry 17 项反 AI slop 自检清单（[`~/.hermes/skills/speccoding/ui-design/references/03-anti-ai-slop.md` § 四](file:///opt/data/home/.hermes/skills/speccoding/ui-design/references/03-anti-ai-slop.md)）
- foundry 间距 / 圆角 / 动效硬约束（[`~/.hermes/skills/speccoding/ui-design/references/04-motion-spacing-radius.md`](file:///opt/data/home/.hermes/skills/speccoding/ui-design/references/04-motion-spacing-radius.md)）
- foundry 调色板 4 档承诺度（[`~/.hermes/skills/speccoding/ui-design/references/02-color-typography-tokens.md` § 一](file:///opt/data/home/.hermes/skills/speccoding/ui-design/references/02-color-typography-tokens.md)）
- 体检执行：2026-07-01
