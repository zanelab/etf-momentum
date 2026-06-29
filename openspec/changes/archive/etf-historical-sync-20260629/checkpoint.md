# Checkpoint

**写入时间**: 2026-06-29T08:29:16Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: spec
**活跃变更**: etf-historical-sync
**分支**: feature/etf-historical-sync
**父分支**: main
**Plan 进度**: 0/23

## 未完成的 Plan 项

```
3:> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
44:- [ ] **Step 1: Write failing tests** — Add to `backend/tests/test_daily_sync.py`:
97:- [ ] **Step 2: Run tests, see them fail**
105:- [ ] **Step 3: Implement the refactor** — In `backend/app/services/daily_sync.py`, rewrite so the per-ETF pull becomes a single function `_read_latest_bar(code: str) -> dict | None` that returns the bar dict or `None` when missing, raising on real errors. The main loop catches `Exception` per code, writes the row with `status`/`error` accordingly. Final structure:
178:- [ ] **Step 4: Run tests, see them pass**
186:- [ ] **Step 5: Commit**
245:- [ ] **Step 1: Write failing tests** — Create `backend/tests/test_sync_api.py`:
273:- [ ] **Step 2: Run tests, see them fail**
281:- [ ] **Step 3: Implement endpoints + lifespan hardening**
407:- [ ] **Step 4: Run tests, see them pass**
415:- [ ] **Step 5: Commit**
473:- [ ] **Step 1: Verify tsc still passes after type additions**
481:- [ ] **Step 2: Implement**
485:- [ ] **Step 3: Run tsc + lint**
493:- [ ] **Step 4: Commit**
575:- [ ] **Step 1: Write failing tests** — Create `frontend/src/pages/__tests__/SyncStatus.test.tsx`:
619:- [ ] **Step 2: Run tests, see them fail**
627:- [ ] **Step 3: Implement the page + register the route + add the sidebar entry**
660:- [ ] **Step 4: Run tests, see them pass**
668:- [ ] **Step 5: Run full frontend suite to confirm no regressions**
```

## 最近修改的文件

```
d21e79d chore(hooks): drop stale Signals.tsx reference in DEFENSIVE_REASON comment
27f6a25 chore(dashboard-flatten): sync project-level spec
98dd65b chore(dashboard): strip stale /signals and /portfolio refs from inlined-section comments
ff1ad5f feat(shell): drop /signals, /portfolio, /screening routes and 2 top-nav entries
e5477fd feat(dashboard): inline full holdings table from /portfolio
```
