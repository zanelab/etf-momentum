## 1. Environment & dependencies

- [ ] 1.1 Backend requirements.txt (fastapi, uvicorn, sqlmodel, pandas, numpy, pytest, httpx, pydantic, python-multipart)
- [ ] 1.2 Backend pyproject.toml with ruff + pytest config
- [ ] 1.3 Backend app/ skeleton with __init__.py
- [ ] 1.4 Frontend Vite + React + TS init in frontend/
- [ ] 1.5 Frontend deps: react-router-dom, @tanstack/react-query, zustand
- [ ] 1.6 Frontend shadcn/ui init + base components
- [ ] 1.7 Shared README with startup commands

## 2. Backend skeleton (M1)

- [ ] 2.1 backend/app/main.py: FastAPI + CORS + /api/health
- [ ] 2.2 SQLModel models: StaticPool, ThemeKeyword, StrategyParam
- [ ] 2.3 backend/app/db.py: engine + session + init
- [ ] 2.4 backend/app/seed.py: seed default data on first run
- [ ] 2.5 GET/POST/PUT/DELETE /api/configs/pool
- [ ] 2.6 GET/PUT /api/configs/themes
- [ ] 2.7 GET/PUT /api/configs/strategy
- [ ] 2.8 Config API tests: backend/tests/test_configs.py

## 3. Data source + fixtures

- [ ] 3.1 MarketDataSource Protocol
- [ ] 3.2 FixtureCSVSource implementation
- [ ] 3.3 Fixture generator script: 10 ETFs × 2 years daily CSV
- [ ] 3.4 Generated fixtures committed to git
- [ ] 3.5 Data source tests: test_fixture_source.py

## 4. Screening core migration (M2, TDD mandatory)

- [ ] 4.1 StrategyParams and ScreeningContext Pydantic models
- [ ] 4.2 filter_etfs() pure-function signature
- [ ] 4.3 Dual-MA filter logic
- [ ] 4.4 Momentum scoring (weighted log regression + R²)
- [ ] 4.5 Industry diversification selection
- [ ] 4.6 Unit tests for all branches
- [ ] 4.7 Parity test: original main.py vs new implementation

## 5. Daily signals & portfolio API (M3)

- [ ] 5.1 GET /api/screening/today
- [ ] 5.2 Mock portfolio data
- [ ] 5.3 GET /api/portfolio with market value & P&L
- [ ] 5.4 GET /api/signals/today with rebalance suggestions
- [ ] 5.5 Signals tests

## 6. Backtest engine (M4)

- [ ] 6.1 run_backtest() service
- [ ] 6.2 Task state file persistence
- [ ] 6.3 POST /api/backtest with BackgroundTask
- [ ] 6.4 GET /api/backtest/{task_id}
- [ ] 6.5 Backtest tests
- [ ] 6.6 Reject interval > 365 days with 400

## 7. Market data API

- [ ] 7.1 GET /api/market/history
- [ ] 7.2 GET /api/market/list
- [ ] 7.3 Market API tests

## 8. Frontend skeleton

- [ ] 8.1 Vite proxy /api to localhost:8000
- [ ] 8.2 src/api/client.ts fetch wrapper
- [ ] 8.3 src/api/hooks.ts TanStack Query hooks
- [ ] 8.4 React Router structure
- [ ] 8.5 AppShell with navigation

## 9. Frontend config pages (M5)

- [ ] 9.1 PoolConfig.tsx with Table + dialog
- [ ] 9.2 ThemeConfig.tsx with grouped editor
- [ ] 9.3 StrategyConfig.tsx with Form
- [ ] 9.4 Hook all three to API

## 10. Frontend signals & portfolio (M6)

- [ ] 10.1 Signals.tsx with sell/buy cards + 5s polling
- [ ] 10.2 Portfolio.tsx with Table + Statistic + 5s polling

## 11. Frontend backtest (M7)

- [ ] 11.1 Install chart library (recharts)
- [ ] 11.2 Backtest.tsx with DatePicker + submit + 2s polling
- [ ] 11.3 NAV curve component
- [ ] 11.4 Stats cards

## 12. Frontend market history

- [ ] 12.1 History.tsx with K-line chart
- [ ] 12.2 Code selector input

## 13. Daily sync (mock)

- [ ] 13.1 daily_sync.py with mock close prices
- [ ] 13.2 Invoke once on startup
- [ ] 13.3 Tests

## 14. Integration verification

- [ ] 14.1 Backend boots, /api/health returns 200
- [ ] 14.2 Frontend boots, all routes accessible
- [ ] 14.3 End-to-end: configure pool, trigger backtest, see result
- [ ] 14.4 README with startup steps + ports + mock data caveats
- [ ] 14.5 .env.example with FIXTURES_DIR, BACKTEST_TASK_DIR
- [ ] 14.6 main.py header has migration notice

## 15. CI / pre-commit checks

- [ ] 15.1 pytest backend/tests/ passes
- [ ] 15.2 ruff check backend/ passes
- [ ] 15.3 tsc --noEmit passes
- [ ] 15.4 npm run build passes
- [ ] 15.5 ./scripts/speccoding-tdd.sh check-commit passes