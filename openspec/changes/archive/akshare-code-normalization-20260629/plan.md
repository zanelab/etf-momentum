# Implementation Plan: akshare-code-normalization

## Prerequisites

- [x] 1.1 [后端] 确认 git 已切到 `feature/akshare-code-normalization` 分支（off main）
- [x] 1.2 [后端] 确认 `pytest` 116 个旧用例基线全部通过

## Backend — 归一化工具（TDD 强制）

- [x] 2.1 [后端] 新建 `backend/app/data_sources/codes.py`，导出 `normalize_etf_code(code)` 与 `same_etf(a, b)`
- [x] 2.2 [后端] 写 `backend/tests/test_codes.py`：6 位裸码 / 已带后缀 / 前后空白小写 / 非法输入抛错 / `same_etf` 正反例 / SZ 首字符规则（1/0/3 → XSHE）

## Backend — akshare 返回归一化

- [x] 3.1 [后端] 修改 `AkShareSource.all_etf_entries`，对每个 code 应用 `normalize_etf_code` 后再返回
- [x] 3.2 [后端] 扩展 `backend/tests/test_akshare_source.py`：`all_etf_entries` 测试断言返回的 code 全部为带后缀规范格式

## Backend — filter_etfs 合并去重

- [x] 4.1 [后端] 修改 `backend/app/services/screening.py` 的 `filter_etfs`：合并池前用 `{normalize_etf_code(c) for c in static_pool + dynamic_pool}` 去重；defensive 排除用 `normalize_etf_code(params.defensive_etf)`
- [x] 4.2 [后端] 扩展 `backend/tests/test_screening.py`（如不存在新建）：断言 `[510300.XSHG]` + `[510300]` 合并后池大小为 1；断言 bare defensive 也能剔除
- [x] 4.3 [后端] 扩展 `backend/tests/test_screening_parity.py`（如必要）：保证与 `main.py` 原版行为一致

## Backend — load_display_names 双查兜底

- [x] 5.1 [后端] 修改 `backend/app/services/today.py` 的 `load_display_names`：先按原 code 查，再按 `normalize_etf_code(code)` 查；输出 `{input_code: matched_display_name}`
- [x] 5.2 [后端] 写测试：bare 码输入返回 display_name、canonical 输入返回 display_name、混合输入全返回、未匹配返回 `code` 自身

## Backend — 动态池同步归一化 upsert key

- [x] 6.1 [后端] 修改 `backend/app/api/configs.py` 的 `sync_dynamic_pool`：在 upsert 时用 `normalize_etf_code(code)` 做 key（同时更新 `existing = session.get(DynamicPoolEntry, normalize_etf_code(code))` 与新建行 `code=normalize_etf_code(raw_code)`）
- [x] 6.2 [后端] 扩展 `backend/tests/test_dynamic_pool_api.py`：新增用例 — 存量 `code="510300"` row 触发 sync 后 row 仍存在且 `code="510300.XSHG"`、新增裸码 row 在 sync 后转 canonical、`is_enabled` 在迁移过程中保留

## Testing — 集成与回归

- [x] 7.1 [后端] `pytest` 全部通过（116 旧 + 新增用例）
- [x] 7.2 [后端] `ruff check backend/app/ backend/tests/` 通过
- [x] 7.3 [前端] `tsc --noEmit` 通过（如有前端改动）
- [x] 7.4 [前端] `npm run build` 通过

## Docs

- [x] 8.1 [后端] 更新 `README.md`：在 API 端点表说明「动态池同步后 code 字段为规范格式」
- [x] 8.2 [后端] 更新 `spec/devlog.md`：归档时记录 akshare 归一化变更要点与剩余限制
- [x] 8.3 [后端] 更新 `spec/requirements.md`：在数据源非功能需求章节加一条「ETF 代码系统内统一为 `XXXXXX.XSHG/XSHE` 规范格式」

## Submission

- [x] 9.1 [共享] 提交所有变更到 `feature/akshare-code-normalization`（每个 section 一个或多个 commit，按 `feat:` / `fix:` 前缀）
- [x] 9.2 [共享] 在 commit message 中标注 spec 章节引用（如 `Closes #` 或正文提及）