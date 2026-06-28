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

- **行情数据**：mock — `backend/data/fixtures/` 下 10 只代表性 ETF × 500 个交易日（GBM 模拟）。生产接入需要替换 `MarketDataSource` 实现（JoinQuant / Tushare / AkShare）。
- **持仓数据**：mock — `backend/app/services/portfolio_mock.py` 返回固定的 3 只 ETF（510300、518880、513100）。生产需要对接券商接口。
- **认证**：未启用（仅本地使用）。
- **回测窗口**：单次 ≤ 366 天（API 强约束）。
- **当日数据**：mock 用 fixture 的最后一日作为 "today"；生产应使用真实交易日历。

## API 端点速查

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | 健康检查 |
| `/api/configs/pool` | GET / POST / PUT / DELETE | 静态池 CRUD |
| `/api/configs/themes` | GET / PUT | 主题词典 |
| `/api/configs/strategy` | GET / PUT | 策略参数 |
| `/api/screening/today` | GET | 当日筛选目标 |
| `/api/portfolio` | GET | 当前持仓 + 市值 + 盈亏 |
| `/api/signals/today` | GET | 当日调仓建议 |
| `/api/backtest` | POST | 启动回测任务（BackgroundTask） |
| `/api/backtest/{task_id}` | GET | 查询任务状态/结果 |
| `/api/market/list` | GET | 所有可用 ETF |
| `/api/market/history` | GET | 单只 ETF OHLCV（支持字段过滤） |

## 环境变量

见 `backend/.env.example`。