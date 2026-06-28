# Close Issues / 归档说明

## 变更摘要

`bootstrap-fullstack` 变更完成全栈重构：将原 JoinQuant 单文件策略 `main.py` 迁移到 FastAPI + SQLModel + SQLite 后端 + React + Vite + TypeScript 前端的完整应用，覆盖 M0–M8 全部里程碑。

## 关闭的 M0–M8 里程碑

| 里程碑 | 范围 | Commit |
|---|---|---|
| M0 | 项目初始化 | `8a5648d` |
| M1 | 后端骨架 + 配置 CRUD | `73e64e2` |
| M2 | 数据源 + fixture | `ec96381` |
| M3 | 筛选核心迁移（关键：与 main.py 行为对照） | `e294683` |
| M4 | 当日信号 + 持仓 API | `b8c4640` |
| M5 | 回测引擎 | `c3d0a6a` |
| M6 | 市场数据 API | `0ac9001` |
| M7 | 前端 7 个页面 | `eccd81a` |
| M8 | 收盘同步（mock） | `e7f8078` |
| 集成验证 + CI | 文档 + 迁移提示 + lint 清理 | `b39a192` |

## 关键风险点（已闭环）

- **JoinQuant 行为对齐**：通过 `tests/_jq_shim.py` + `tests/test_screening_parity.py` 三个对照测试验证迁移后 `filter_etfs` 与原 `main.py` 在 default / industry-diverse / ma-filter-off 三种配置下输出完全一致
- **TDD 纪律**：74 个 pytest 用例 + 1-1 文件映射（每个服务文件均有对应测试）+ 关键回归测试（动量评分窗口语义、成交量均值排除当日）
- **CI 基线**：`pytest` 74 passed / `ruff check` 0 errors / `tsc --noEmit` exit 0 / `npm run build` 通过

## 已知遗留（不在本次范围）

- 真实行情数据源接入（替换 `FixtureCSVSource`）
- 真实券商持仓对接（替换 `portfolio_mock`）
- 同步任务的定时器触发（当前为手动调用）
- 认证 / 权限（仅本地使用）
- 多用户隔离（SQLite 单库）

这些项已记录在 `README.md` 已知限制和 `spec/design.md` 实施调整中。

## 状态

- 归档目录：`openspec/changes/archive/bootstrap-fullstack-20260628/`
- 项目级 spec：`spec/requirements.md` / `design.md` / `tasks.md` / `devlog.md` / `structure.md` 已同步
- 分支：仍在 `feature/bootstrap-fullstack`（待 merge 阶段合入 main）
