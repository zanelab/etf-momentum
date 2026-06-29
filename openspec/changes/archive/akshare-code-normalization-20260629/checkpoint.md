# Checkpoint

**写入时间**: 2026-06-29T01:47:31Z
**项目根目录**: /Users/zane/Workspace/etf-momentum
**阶段**: executing
**活跃变更**: akshare-code-normalization
**分支**: feature/akshare-code-normalization
**父分支**: main
**Plan 进度**: 0/22

## 未完成的 Plan 项

```
5:- [ ] 1.1 [后端] 确认 git 已切到 `feature/akshare-code-normalization` 分支（off main）
6:- [ ] 1.2 [后端] 确认 `pytest` 116 个旧用例基线全部通过
10:- [ ] 2.1 [后端] 新建 `backend/app/data_sources/codes.py`，导出 `normalize_etf_code(code)` 与 `same_etf(a, b)`
11:- [ ] 2.2 [后端] 写 `backend/tests/test_codes.py`：6 位裸码 / 已带后缀 / 前后空白小写 / 非法输入抛错 / `same_etf` 正反例 / SZ 首字符规则（1/0/3 → XSHE）
15:- [ ] 3.1 [后端] 修改 `AkShareSource.all_etf_entries`，对每个 code 应用 `normalize_etf_code` 后再返回
16:- [ ] 3.2 [后端] 扩展 `backend/tests/test_akshare_source.py`：`all_etf_entries` 测试断言返回的 code 全部为带后缀规范格式
20:- [ ] 4.1 [后端] 修改 `backend/app/services/screening.py` 的 `filter_etfs`：合并池前用 `{normalize_etf_code(c) for c in static_pool + dynamic_pool}` 去重；defensive 排除用 `normalize_etf_code(params.defensive_etf)`
21:- [ ] 4.2 [后端] 扩展 `backend/tests/test_screening.py`（如不存在新建）：断言 `[510300.XSHG]` + `[510300]` 合并后池大小为 1；断言 bare defensive 也能剔除
22:- [ ] 4.3 [后端] 扩展 `backend/tests/test_screening_parity.py`（如必要）：保证与 `main.py` 原版行为一致
26:- [ ] 5.1 [后端] 修改 `backend/app/services/today.py` 的 `load_display_names`：先按原 code 查，再按 `normalize_etf_code(code)` 查；输出 `{input_code: matched_display_name}`
27:- [ ] 5.2 [后端] 写测试：bare 码输入返回 display_name、canonical 输入返回 display_name、混合输入全返回、未匹配返回 `code` 自身
31:- [ ] 6.1 [后端] 修改 `backend/app/api/configs.py` 的 `sync_dynamic_pool`：在 upsert 时用 `normalize_etf_code(code)` 做 key（同时更新 `existing = session.get(DynamicPoolEntry, normalize_etf_code(code))` 与新建行 `code=normalize_etf_code(raw_code)`）
32:- [ ] 6.2 [后端] 扩展 `backend/tests/test_dynamic_pool_api.py`：新增用例 — 存量 `code="510300"` row 触发 sync 后 row 仍存在且 `code="510300.XSHG"`、新增裸码 row 在 sync 后转 canonical、`is_enabled` 在迁移过程中保留
36:- [ ] 7.1 [后端] `pytest` 全部通过（116 旧 + 新增用例）
37:- [ ] 7.2 [后端] `ruff check backend/app/ backend/tests/` 通过
38:- [ ] 7.3 [前端] `tsc --noEmit` 通过（如有前端改动）
39:- [ ] 7.4 [前端] `npm run build` 通过
43:- [ ] 8.1 [后端] 更新 `README.md`：在 API 端点表说明「动态池同步后 code 字段为规范格式」
44:- [ ] 8.2 [后端] 更新 `spec/devlog.md`：归档时记录 akshare 归一化变更要点与剩余限制
45:- [ ] 8.3 [后端] 更新 `spec/requirements.md`：在数据源非功能需求章节加一条「ETF 代码系统内统一为 `XXXXXX.XSHG/XSHE` 规范格式」
```

## 最近修改的文件

```
45dce6c Merge: real-data-source (M9 — 真实数据源接入)
e3518f6 chore(real-data-source): archive + sync spec/ to project-level
d583535 fix(real-data-source): use fund_etf_spot_em (real akshare API)
f14b7a4 fix(real-data-source): clean up sync error message (remove duplication + prefix)
ca39dd5 fix(real-data-source): sync returns 503/502 with actionable errors
```
