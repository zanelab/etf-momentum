# Plan: akshare-real-data

---

## 任务清单

### Task 1: Docker 骨架（不涉及业务代码）

- [ ] 新增 `Dockerfile`（后端 Python 3.12）
- [ ] 新增 `Dockerfile.frontend`（前端 Node 20 + nginx）
- [ ] 新增 `frontend/nginx.conf`
- [ ] 新增 `docker-compose.yml`
- [ ] 新增 `.dockerignore`
- [ ] 验证 `docker-compose build` 成功

### Task 2: Portfolio 数据库系统

- [ ] 新增 `backend/app/models/portfolio.py`（SQLAlchemy model）
- [ ] 新增 `backend/app/services/portfolio.py`（CRUD service）
- [ ] 新增 `backend/app/api/portfolio.py`（REST API 端点）
- [ ] 注册路由到 `main.py`
- [ ] 新增 `backend/tests/test_portfolio_db.py`
- [ ] 验证 `uv run pytest -q` 通过

### Task 3: 删除 mock/fixture 数据

- [ ] 删除 `backend/data/fixtures/` 目录
- [ ] 删除 `backend/app/data_sources/fixture.py`
- [ ] 删除 `backend/app/services/portfolio_mock.py`
- [ ] 删除 `backend/scripts/generate_fixtures.py`
- [ ] 删除 `backend/tests/test_fixture_source.py`
- [ ] 删除 `backend/tests/test_portfolio_cash.py`
- [ ] 更新 `backend/app/data_sources/__init__.py`（移除 fixture 分支）
- [ ] 更新 `backend/app/data_sources/akshare_source.py`（移除 fallback 逻辑）
- [ ] 改造 `signals.py`、`screening.py`、`today.py`（替换 portfolio 调用）
- [ ] 更新 `conftest.py`（移除 FIXTURES_DIR fixture）

### Task 4: 前端持仓配置页面

- [ ] 新增 `frontend/src/pages/PortfolioSettingsPage.tsx`
- [ ] 新增 `usePortfolio`、`useUpsertHolding`、`useDeleteHolding` hooks
- [ ] 注册路由到 AppShell
- [ ] 验证 `npm test` 通过

### Task 5: 全栈 CI 验证

- [ ] `docker-compose build` 成功
- [ ] `docker-compose up -d` + health check 通过
- [ ] 后端 `uv run pytest -q` 全部通过
- [ ] 前端 `npm test` 全部通过
- [ ] `npm run build` 通过
- [ ] push 到远程分支

---

## 执行顺序

```
Task 1 (Docker) → Task 2 (Portfolio DB) → Task 3 (删除 mock) → Task 4 (前端) → Task 5 (CI)
```

Task 1 先跑通 Docker 骨架，后续任务在容器内验证。