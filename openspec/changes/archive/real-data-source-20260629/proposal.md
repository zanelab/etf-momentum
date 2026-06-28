# Proposal: real-data-source

## What

将 `MarketDataSource` 抽象从单一 `FixtureCSVSource` 扩展为多实现：
1. **新增 AkShareSource**：基于 akshare 库获取 A 股 ETF 日级 OHLCV（`fund_etf_hist_em`）+ 全市场 ETF 列表（`fund_etf_name_em`）
2. **本地缓存层**：SQLite 表 `market_bar_cache(code, date, fields...)`，按 (code, date) 命中，避免重复网络请求
3. **动态池**：新增 `/api/configs/pool/dynamic` 端点，从 akshare 拉全市场 ETF 列表（可启用/停用），与现有静态池融合（与原 `main.py` 设计对齐）
4. **前端"数据源"页**：显示当前源（fixture/akshare）、末次同步时间、缓存命中数、手动刷新按钮
5. **运行时切换**：`ETF_DATA_SOURCE=akshare|fixture` 环境变量控制默认源；单次请求可通过 `?source=` 参数覆盖

## Why

`bootstrap-fullstack` 已交付完整业务逻辑（筛选 / 回测 / 信号），但所有端到端测试都基于 GBM mock fixture。生产前必须接入真实数据，否则无法：
- 验证筛选核心在真实行情上的行为
- 跑多日实盘回测
- 给用户提供可见的"数据来源 + 时效性"信息

akshare 是国内最常用的免费 ETF 数据源，无 token；缓存层既解决 akshare 限速（每分钟调用次数），又支持离线开发。

## Scope

- [x] backend
- [x] frontend

## Acceptance Criteria

- [ ] 新增 `backend/app/data_sources/akshare_source.py`，实现 `MarketDataSource`（snapshot / history / all_etfs / health）
- [ ] 新增缓存层 `backend/app/data_sources/cache.py`（SQLite 表 `market_bar_cache`，按 (code, date) 查询；`hit/miss` 计数可读）
- [ ] 环境变量 `ETF_DATA_SOURCE`（默认 `fixture`）；请求参数 `?source=akshare` 可覆盖
- [ ] 新增 `/api/configs/pool/dynamic` 端点（GET 拉取全市场 ETF 列表并写库；PATCH 启用/停用）
- [ ] `filter_etfs` 接受 `dynamic_pool` 参数与静态池融合（已存在，复用现有 M2 实现）
- [ ] 前端新增 `DataSource.tsx` 页：源类型、末次同步、缓存命中率、刷新按钮
- [ ] 现有 74 个 pytest 用例继续通过（fixture 仍为默认）
- [ ] 新增 `tests/test_akshare_source.py`：mock akshare 响应测试适配器逻辑（不依赖网络）
- [ ] 新增 `tests/test_data_source_cache.py`：缓存命中/失效/序列化
- [ ] 新增 `tests/test_dynamic_pool.py`：动态池拉取 + 启用/停用
- [ ] ruff check 通过 / tsc --noEmit 通过 / npm run build 通过
- [ ] README.md 更新"已知限制"段（标注 akshare 接入情况）

## Out of Scope

- 真实券商持仓对接（仍为 `portfolio_mock`）
- 同步定时器（手动触发 / 缓存层完成即视为"同步"）
- 鉴权 / 多用户
- 替换 akshare 为 tushare / JoinQuant（可后续新变更）

## Status

- [x] 提案已确认
