# ETF Momentum — 全栈应用

ETF 动量轮动策略的全栈实现：React 前端 + Python (FastAPI) 后端。

策略核心（双均线过滤、动量评分、行业分散、止损、防御 ETF）从原聚宽（JoinQuant）单文件策略 `main.py` 迁移而来，行为保持一致。

## 目录

- `backend/` — Python FastAPI 后端
- `frontend/` — React + Vite + TypeScript 前端
- `spec/` — 项目级规格（需求、设计、任务、日志）
- `openspec/` — 变更管理（当前在执行的变更 `bootstrap-fullstack`）
- `main.py` — **已迁移**，仅作参考
- `scripts/` — SpecCoding 工作流脚本（state/gate/checkpoint/tdd）

## 启动

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端 API: <http://localhost:8000/api>
自动文档: <http://localhost:8000/docs>

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端: <http://localhost:5173>

### 开发工作流

```bash
# 查看当前阶段
./scripts/speccoding-state.sh report

# 标记任务完成（手动，因为脚本无法自动判断）
# 编辑 openspec/changes/bootstrap-fullstack/plan.md 将 `- [ ]` 改为 `- [x]`

# 每次提交前跑 TDD 验证
./scripts/speccoding-tdd.sh check-commit
```

## 已知限制

- 行情数据源当前为 fixture CSV（10 只代表性 ETF × 2 年日级），无真实市场接入
- 持仓数据为 mock
- 认证未启用（仅本地使用）
- 回测限制单次 ≤ 365 天

## 下一步

详见 `spec/tasks.md` 里程碑 M1–M8。