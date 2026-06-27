# Checkpoint

**写入时间**: 2026-06-27T13:36:03Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: readme-startup-docs
**分支**: feature/readme-startup-docs
**父分支**: main
**Plan 进度**: 0/0

## 未完成的 Plan 项

```
3:- [ ] 1.1 跑 `pytest backend/ --collect-only -q | wc -l` 获取后端测试数（截至 commit 时）
4:- [ ] 1.2 跑 `cd frontend && pnpm test --run 2>&1 | grep -E "Test Files|Tests"` 获取前端测试数
5:- [ ] 1.3 确认 12 个 API 端点的现状（`grep -E "@router\.(get|post)" backend/app/api/v1/*.py`）
6:- [ ] 1.4 确认前端 4 个页面 + Layout + Zustand store 名称
7:- [ ] 1.5 确认 akshare CLI 与 signal CLI 的 argparse 参数
8:- [ ] 1.6 确认 `Makefile` 所有 target 与命令实际可用
12:- [ ] 2.1 顶部：项目简介（一段话，含核心目标 + 链接到 `spec/requirements.md`）
13:- [ ] 2.2 「功能特性」章节：5 项业务能力（动量 / 回测 / 指标 / 信号 / 前端）每项含代码定位
14:- [ ] 2.3 「快速开始」章节：端到端首跑清单（up → migrate → sync etfs → sync prices → 浏览）
15:- [ ] 2.4 「Docker 常用命令」章节：从 Makefile 派生，与 `make help` 一致
16:- [ ] 2.5 「本地开发（无 Docker）」章节：backend + frontend 独立启动命令
17:- [ ] 2.6 「故障排查」章节：≥3 类问题（数据空 / 端口占用 / akshare 同步失败）
18:- [ ] 2.7 「项目结构」章节：顶层 ASCII 树（含 `AGENTS.md`）
19:- [ ] 2.8 「文档导航」章节：指向 backend/README + frontend/README + spec/ + openspec/changes/archive/
20:- [ ] 2.9 「里程碑」章节：链接到 `spec/tasks.md`，标注 v1.0 已完成项
24:- [ ] 3.1 「项目简介」章节：列出 v1.0 已交付能力（动量 + 回测 + 6 指标 + 实时信号 + 12 端点）
25:- [ ] 3.2 「API 端点速查表」：12 个端点（方法 + 路径 + 一行说明 + 指向 Swagger）
26:- [ ] 3.3 「CLI 命令」章节：`sync etfs` / `sync prices` / `signal run` / `signal show` 完整 argparse
27:- [ ] 3.4 「项目结构」章节：补齐到 v1.0 状态（`app/signals/`、`app/api/v1/pools.py`、`tests/` 子目录细分）
28:- [ ] 3.5 「测试覆盖」章节：标注当前测试数 + 自检命令
```

## 最近修改的文件

```
f17e22a chore(state): mark frontend-component-tests merge phase
1814923 Merge feature/frontend-component-tests: 25 component tests for Button/HealthPage/Layout
821283d chore(spec): mark frontend-component-tests done + devlog
546f25b chore(archive): complete frontend-component-tests change
7adde6c chore(spec): sync component-coverage spec to main
```
