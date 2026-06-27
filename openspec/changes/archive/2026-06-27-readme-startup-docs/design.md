## Context

- v1.0 阶段 4 最后一项「README + 启动文档」尚未完成
- 当前根 `README.md` 95 行只覆盖 Docker Compose 启动，未提业务能力
- `backend/README.md` 写于 scaffold 阶段，「后续计划」把已交付功能列成 TODO，测试数 200 与实际 267 不一致
- `frontend/README.md` 只覆盖 HealthPage，遗漏 DashboardPage / BacktestPage / PoolsPage
- 用户角色：个人投资者（首次跑通看动量看板）+ 策略研究员（理解可调参数）

约束：
- 不引入新代码、不改 API、不改测试、不改依赖
- 所有变更必须可由 `git diff` 在文档目录直接观察到
- 与现有 `Makefile` / `docker-compose.yml` 命令保持一致（不发明新命令）
- 中英文混排风格与现有 README 一致（中文小标题 + 英文代码）

## Goals / Non-Goals

**Goals:**
- 让新用户从 README 第一页就能回答 5 个问题：(1) 这是什么 (2) 怎么跑起来 (3) 跑起来后能干什么 (4) 跑不起来怎么排查 (5) 想去哪里深入
- 让现有 README 中「后续计划」一节全部清空（v1.0 已完成的能力移到「功能特性」章节）
- 测试数 / 端点数 / 页面数等数字必须与代码现状一致
- 提供 5 分钟「首跑清单」（容器起来 → migrate → 同步 ETF 主数据 → 同步价格 → 浏览 Dashboard → 跑一次回测）

**Non-Goals:**
- 不重写 `AGENTS.md` / `spec/` 下的项目级 spec（这些属于 spec-driven 流程的产物，不是用户文档）
- 不做英文翻译（仅维护中文版本）
- 不新增 `CONTRIBUTING.md` / `CHANGELOG.md`（v1.0 单用户本地部署场景不需要）
- 不文档化 akshare 内部 API（黑盒使用即可）
- 不修改 Docker / Make / CI 配置

## Decisions

### 决策 1：根 README 作为唯一入口，后端/前端 README 作深入参考

**选择**：根 README 覆盖「是什么 / 怎么跑 / 能干什么 / 出问题怎么办」四个面；`backend/README.md` 聚焦模块结构 + API 端点速查 + CLI；`frontend/README.md` 聚焦页面 + store + 组件。

**理由**：根 README 是 GitHub 仓库默认渲染页，新用户 80% 概率只看它。子目录 README 是开发者深入时的二级入口。

**取舍**：根 README 会变长（估计 200+ 行）。如果用户偏好短根 README + 长 QUICKSTART，可调整。

### 决策 2：不新增 `docs/QUICKSTART.md`，根 README 内嵌「快速开始」章节

**选择**：把 5 分钟首跑流程作为根 README 的一个顶级章节，而不是独立文件。

**理由**：
- 减少文件数（用户少跳一次）
- 「快速开始」是根 README 的天然章节，符合 GitHub README 通用约定
- `docs/` 目录目前不存在，新建一个目录只放一个文件性价比低

**取舍**：如果未来需要 i18n 或独立分发 QUICKSTART，再拆出独立文件。

### 决策 3：API 文档策略——「速查表 + Swagger 链接」，不在 README 中逐端点详述

**选择**：在 `backend/README.md` 用一张表格列出 12 个端点（method + path + 一行说明），然后指向 `http://localhost:8000/docs`（FastAPI 自动生成的 Swagger UI）。

**理由**：
- FastAPI 已自动生成完整 OpenAPI schema + Swagger UI + ReDoc，逐端点抄到 README 是重复劳动且会漂移
- 表格给速查，Swagger 给完整 schema，二者互补

**取舍**：表格需要在每次新增端点时手动更新，可能漂移。接受此漂移风险（README 末尾的「文档」章节会提醒以 Swagger 为准）。

### 决策 4：测试数 / 端点数等数字以现状为准，写明「最后更新」

**选择**：在 `backend/README.md` 与 `frontend/README.md` 中各加一行「测试覆盖：N 个（截至 v1.0）」，并指向 CI 或 `pytest -v` / `pnpm test` 输出。

**理由**：手动维护数字必然漂移，但显式标注「截至 v1.0」+ 提供可执行命令自查，比静默落后强。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 测试数 / 端点数随后续 commit 漂移 | 在 README 中显式标注「v1.0」，并附上自检命令（`pytest backend/ --collect-only -q \| wc -l`） |
| 重写 README 后丢失原有有价值内容 | 执行前用 `git show main:README.md` 备份现有内容到 proposal 评审材料中，执行后逐节对照 |
| 根 README 过长（200+ 行）用户不愿读 | 顶部用 TOC（`## 目录`）+ 每章节不超过 50 行；首屏只放「快速开始」+「功能特性」 |
| 与 `spec/devlog.md` 重复叙述 | README 是面向最终用户的语言；devlog 是面向开发者的内部记录。分工清晰 |

## Migration Plan

无（纯文档变更，部署即生效）。

**回滚**：单 PR 回退三个 README 文件 + 删除新建文件即可。

## Open Questions

无（已通过 scope 决策 1+2 确定文件分布）。