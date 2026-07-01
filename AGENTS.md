# 项目开发强制规则：必须使用 SpecCoding 全栈开发工作流

> ⚠️ 本项目的所有开发工作必须严格遵循 **SpecCoding 全栈开发工作流**（https://github.com/zanelab/speccoding-skill）。
> 该技能通过两级 Spec 体系（`spec/` + `openspec/changes/`）和八阶段开发循环（git branch → proposal → brainstorming → spec → amend → executing → archive → merge），规范 AI 的工作方式。

## 1. 技能检查

在开始任何项目开发之前，首先检查当前 AI 是否已加载技能 `speccoding`。

- **如果已激活**：直接跳转到第 3 节开始工作。
- **如果未激活**：请执行下面的“安装选择流程”。

## 2. 安装选择流程

检测到本项目的必需技能 `speccoding` 尚未安装。请选择安装方式：

- **A. 智能体自动安装** – 我将自动执行安装步骤。
- **B. 我手动安装** – 我会提供手动安装说明，由您自行完成。完成后请回复“已安装”。

请输入 **A** 或 **B**。

### 2.1 选项 A：智能体自动安装

我将执行以下步骤完成安装：

1. **确定目标路径**：根据项目环境，将技能安装到合适目录。
   - **通用路径**（推荐，跨工具共享技能）：`.agent/skills/`
   - **CodeBuddy 专用路径**：`.codebuddy/skills/`
   - **Cursor 专用路径**：`.cursor/skills/`

2. **执行安装命令**（任选其一，根据当前 AI 工具适配）：
   - **使用 `npx` 快速安装（推荐）**：
     ```bash
     npx add-skill zanelab/speccoding-skill
     ```
     这个命令会自动识别环境，将技能安装到正确的路径下。
   - **使用 Git 克隆（通用后备方案）**：
     ```bash
     git clone https://github.com/zanelab/speccoding-skill.git [目标路径]/speccoding-skill
     ```

3. **验证安装**：检查目标路径下是否存在包含 `SKILL.md` 的 `speccoding-skill` 文件夹。

4. **激活技能**：如果上述安装成功，请调用技能加载功能（如 `use_skill("speccoding")`）来激活它。

5. 技能激活后，告知用户并继续开发工作。

### 2.2 选项 B：用户手动安装

如果你选择手动安装，请参照以下任一方式进行操作：

- **方式一（全局通用，推荐）**：在终端中运行以下命令之一
   ```bash
   # 推荐：使用 add-skill 工具，它会自动处理
   npx add-skill zanelab/speccoding-skill
   
   # 或使用 CLI 工具
   npx skillab add zanelab/speccoding-skill
   ```

- **方式二（手动克隆）**：将技能克隆到你的 AI 工具对应的技能目录下。例如，对于通用路径：
   ```bash
   mkdir -p .agent/skills/
   git clone https://github.com/zanelab/speccoding-skill.git .agent/skills/speccoding-skill
   ```

安装完成后，请回到对话中回复 **“已安装”**，我将重新检测并激活技能。

## 3. 技能使用要求

- **所有**项目开发、代码修改、重构、调试等任务，都必须严格遵循 `speccoding` 技能中定义的 **八阶段工作流**。
- 务必遵守 **阶段写入边界** 规则，在设计阶段（proposal/brainstorming/spec/amend）禁止修改任何代码。
- 在任何情况下，都不得在未激活 `speccoding` 技能时执行项目相关的开发操作。

## 4. 异常处理

- 如果自动安装失败，请告知用户失败原因，并建议切换到手动安装。
- 如果用户拒绝安装，则停止所有开发工作，并说明开发必须依赖 `speccoding` 技能。

---

## 5. UI 设计维度强制规则

> 本项目涉及前端界面（React + Vite + Tailwind）。所有涉及 UI 的变更必须在 **spec 阶段** 落地设计维度，写入 `openspec/changes/<name>/design.md`（与 `spec.md` 并列）。

### 5.1 设计维度集成层位置

- **集成层**：`~/.hermes/skills/speccoding/ui-design/`（位于 speccoding skill 目录下）
- **来源**：吸收自 [frontend-ui-foundry](https://github.com/jiushiwon/wg-skills/tree/main/frontend-ui-foundry) 的设计法则
- **触发**：对话中出现"做 UI / 调色板 / 字体 / 圆角 / 动效 / AI slop / spec/design.md"等关键词，agent 自动加载该集成层
- **模板**：`~/.hermes/skills/speccoding/ui-design/templates/01-spec-design-template.md`

### 5.2 5 个硬约束（违反必须修正）

| # | 约束 | 详见 |
|---|------|------|
| 1 | **场景识别**：8 场景（mobile-responsive/pc-corporate/admin-dashboard/landing-marketing/docs-site/fintech-app/mobile-native/threejs-3d）必走"4 问"定位 | `references/01-ui-scenarios.md` |
| 2 | **调色承诺度**：Restrained / Committed / Full / Drenched 四档必填一档 | `references/02-color-typography-tokens.md` |
| 3 | **反 AI Slop 三阶反思维**：提案阶段必跑（品类→调色板、品类+反参考→美学，猜得出=反射） | `references/03-anti-ai-slop.md` § 三 |
| 4 | **尺寸系统**：间距必落 4pt 网格；圆角必落 8 档阶梯；动效仅 transform/opacity | `references/04-motion-spacing-radius.md` |
| 5 | **17 项自检清单**：executing 入口必跑，未过则阻止进入代码实现 | `references/03-anti-ai-slop.md` § 四 |

### 5.3 阶段边界

- **proposal 阶段**：必加 "UI 场景" 节（含场景名、调色板名、承诺度、技术栈）
- **brainstorming 阶段**：必跑"三阶反思维"，未通过回到 proposal
- **spec 阶段**：必写 `openspec/changes/<name>/design.md`（用 5.1 的模板）
- **amend 阶段**：UI 变更必须改 spec/design.md，重新跑 17 项自检
- **executing 入口**：必跑 17 项自检清单（截图存档到 commit message）；未过 = 阻止开始
- **executing 出场（commit 前）**：再跑一遍 17 项自检，防止新增 slop

### 5.4 触发关键词

```
UI 设计 / 页面设计 / 前端 / 设计稿
调色板 / 颜色 / 字体 / 圆角 / 动效 / Token
AI slop / 渐变文字 / 玻璃拟态 / Inter 字体 / 侧边色条 / hero-metric
管理端设计 / 落地页设计 / 移动端界面
Stripe 风格 / Linear 风格 / Vercel 风格 / Tailwind
```

只要对话包含上述任何一个词，agent 必须先 `skill_view(name='speccoding-ui-design')`（或读 `~/.hermes/skills/speccoding/ui-design/SKILL.md`）再行动。

### 5.5 当前项目 UI 状况基线

- **技术栈**：React 18 + Vite + Tailwind 3.4（HSL 主题，shadcn-style 默认）
- **组件库**：lucide-react + 自主组件（无 shadcn / MUI / AntD）
- **场景**：admin-dashboard（默认场景；移动端有响应式，但主战场是 PC 后台）
- **最近体检**：见 `spec/ui-design-audit.md`（C 任务产出）
- **Token 计划**：见 D 任务（4pt 网格 + OKLCH 调色板迁移）
