## 1. 调研与素材收集

- [x] 1.1 跑 `pytest backend/ --collect-only -q | wc -l` 获取后端测试数（截至 commit 时）→ **267**
- [x] 1.2 跑 `cd frontend && pnpm test --run 2>&1 | grep -E "Test Files|Tests"` 获取前端测试数 → **190 tests / 26 files**
- [x] 1.3 确认 18 个 API 端点的现状（`grep -E "@router\.(get|post)" backend/app/api/v1/*.py`）
- [x] 1.4 确认前端 4 个页面 + Layout + Zustand store 名称
- [x] 1.5 确认 akshare CLI 与 signal CLI 的 argparse 参数
- [x] 1.6 确认 `Makefile` 所有 target 与命令实际可用

## 2. 根 README 重写

- [x] 2.1 顶部：项目简介（一段话，含核心目标 + 链接到 `spec/requirements.md`）
- [x] 2.2 「功能特性」章节：5 项业务能力（动量 / 回测 / 指标 / 信号 / 前端）每项含代码定位
- [x] 2.3 「快速开始」章节：端到端首跑清单（up → migrate → sync etfs → sync prices → 浏览）
- [x] 2.4 「Docker 常用命令」章节：从 Makefile 派生，与 `make help` 一致
- [x] 2.5 「本地开发（无 Docker）」章节：backend + frontend 独立启动命令
- [x] 2.6 「故障排查」章节：≥3 类问题（数据空 / 端口占用 / akshare 同步失败）
- [x] 2.7 「项目结构」章节：顶层 ASCII 树（含 `AGENTS.md`）
- [x] 2.8 「文档导航」章节：指向 backend/README + frontend/README + spec/ + openspec/changes/archive/
- [x] 2.9 「里程碑」章节：链接到 `spec/tasks.md`，标注 v1.0 已完成项（**注意：`spec/tasks.md` 中"12 个 REST 端点"表述已过期，实际为 18 个**）

## 3. backend/README 更新

- [x] 3.1 「项目简介」章节：列出 v1.0 已交付能力（动量 + 回测 + 6 指标 + 实时信号 + 18 端点）
- [x] 3.2 「API 端点速查表」：18 个端点（方法 + 路径 + 一行说明 + 指向 Swagger）
- [x] 3.3 「CLI 命令」章节：`sync etfs` / `sync prices` / `signal run` / `signal show` 完整 argparse
- [x] 3.4 「项目结构」章节：补齐到 v1.0 状态（`app/signals/`、`app/api/v1/pools.py`、`tests/` 子目录细分）
- [x] 3.5 「测试覆盖」章节：标注当前测试数 + 自检命令（**267**）
- [x] 3.6 「后续计划」章节：清空 v1.0 已完成项，仅留 v2.0 占位（多策略对比 / 美股扩展 / 实时告警）

## 4. frontend/README 更新

- [x] 4.1 「当前阶段」章节：列出 4 个页面（HealthPage / DashboardPage / BacktestPage / PoolsPage）+ Layout
- [x] 4.2 「页面说明」章节：每个页面 1-2 句（路由 + 作用 + 关键交互）
- [x] 4.3 「Zustand store」章节：列出 5 个 store 名称 + 各自管理的状态
- [x] 4.4 「项目结构」章节：补齐到 v1.0（`pages/` 4 个文件 + `stores/` 5 个文件 + `layouts/`）
- [x] 4.5 「测试覆盖」章节：当前测试数 + 自检命令（**190**）
- [x] 4.6 「环境变量」章节：补充 `VITE_API_BASE_URL`（已有）+ 任何新增变量（如有）→ 仅保留 `VITE_API_BASE_URL`
- [x] 4.7 「后续计划」章节：清空 v1.0 已完成项，仅留 v2.0 占位

## 5. 验证与归档

- [ ] 5.1 `git diff main -- '*.py' '*.tsx' '*.ts' '*.json' '*.toml' 'Dockerfile' 'docker-compose.yml' Makefile` 输出为空
- [ ] 5.2 三个 README 中的命令逐条在本机或容器中确认可执行（至少 spot-check 3 条）
- [ ] 5.3 三个 README 中的数字（测试数 / 端点数 / 页面数）已对照源码
- [ ] 5.4 `git add` 三个 README 文件并 commit
- [ ] 5.5 sync delta spec 到 `openspec/specs/`
- [ ] 5.6 更新 `spec/tasks.md` 标记「README + 启动文档」为已完成
- [ ] 5.7 更新 `spec/devlog.md` 添加变更记录
- [ ] 5.8 archive 变更 → merge → push