# 项目需求

## 项目概述

将原聚宽（JoinQuant）ETF 动量轮动策略重构为前后端分离的全栈应用。

策略核心保持不变（静态+动态池融合、双均线过滤、动量评分、行业分散、止损、防御 ETF），但参数和池子从硬编码改为前端可配置；筛选/回测逻辑从单文件脚本迁移到后端服务；前端提供可视化与交互入口。

## 核心功能

### 前端（React）

| 功能 | 说明 |
|------|------|
| 静态核心池配置 | 增删改查核心 ETF 列表（替代原 `STATIC_ETF_POOL`） |
| 主题分类词典配置 | 增删改查主题关键词映射（替代原 `THEME_KEYWORDS`） |
| 策略参数配置 | 可视化编辑动量周期、均线周期、止损比例、防御 ETF 等（替代原 `STRATEGY_CONFIG`） |
| 回测执行与展示 | 选择时间区间、执行回测、展示净值曲线与统计指标 |
| ETF 历史数据查询 | 单只 ETF 的历史 K 线、成交额、动量评分查询 |
| 当日买入/卖出信号 | 展示当日 `filter_etfs()` 选中的标的与调仓建议 |
| 当前持仓展示 | 持仓清单、成本价、浮动盈亏、止损线 |

### 后端（Python）

| 功能 | 说明 |
|------|------|
| 配置持久化 API | 静态池、主题词典、策略参数的 CRUD |
| ETF 筛选 API | 接收前端配置，调用核心 `filter_etfs()` 逻辑，返回当日目标列表 |
| 历史数据 API | 行情数据查询（K 线、成交额等） |
| 回测 API | 在选定时间区间上重放筛选逻辑，计算净值与统计 |
| 当日买入/卖出信号 API | 与筛选 API 类似，但额外返回调仓建议（卖出列表 + 买入列表 + 数量） |
| 持仓 API | 当前持仓、成本价、市值、盈亏 |
| 收盘数据同步 | 每日收盘后拉取真实/模拟行情，写入数据库 |

## 非功能需求

- **API 风格**：RESTful，JSON over HTTP
- **数据存储**：配置数据可用关系型 DB（SQLite 起步，便于后续迁移 Postgres）；行情/回测结果历史可入库
- **数据源**：抽象数据源接口（`MarketDataSource`），至少实现一个 mock/本地数据源 + 一个真实源（akshare）；通过 `make_source(name)` 工厂按 `ETF_DATA_SOURCE` 环境变量或 per-request 参数切换；akshare 路径自动缓存
- **回测**：后端串行执行，避免阻塞 API（可用异步任务或同步短任务）
- **测试**：核心筛选逻辑必须有单测覆盖（TDD 强制，参见 AGENTS.md）
- **动态池管理**：用户可拉取 akshare 全市场 ETF 列表入本地表，勾选启用哪些进入筛选；同步失败必须返回明确错误（不可静默回退）

## 数据源切换与缓存（real-data-source 2026-06-29）

- **数据源**：`ETF_DATA_SOURCE` 环境变量决定默认源（`fixture` / `akshare`）；也支持 `?source=akshare` per-request 覆盖（行情、筛选、信号、回测接口均接受）
- **akshare 缓存**：`CachedSource(AkShareSource)` 自动写入 SQLite `market_bar_cache` 表；hits / misses 由 `/api/health?stats=1` 暴露
- **动态池同步**：`POST /api/configs/pool/dynamic/sync` 必须走 akshare（不受 `ETF_DATA_SOURCE` 影响）；返回 200 `{synced, total, enabled}` / 503 akshare 缺失 / 502 akshare 拉取失败
- **前端面板**：`/datasource` 页面展示健康状态、缓存命中统计、动态池列表与同步按钮

## ETF 代码归一化（akshare-code-normalization 2026-06-29）

- **规范格式**：系统内 ETF 代码统一使用 `XXXXXX.XSHG`（上海）或 `XXXXXX.XSHE`（深圳）带后缀形式；akshare 返回的 6 位裸码由 `app/data_sources/codes.normalize_etf_code` 在 4 个接入点统一归一（akshare 返回、动态池 upsert key、`filter_etfs` 池合并、`load_display_names` 查表）
- **交易所推断**：6 位裸码首字符规则 — 5/6 → XSHG、1/0/3 → XSHE
- **向后兼容**：所有归一化点同时接受裸码与带后缀输入；存量裸码 row 在下次 `POST /api/configs/pool/dynamic/sync` 时自动迁移到 canonical form

## 待用户确认

- 数据源：是否已有可用数据源（如 akshare、tushare、聚宽自带）？还是先 mock？
- 回测粒度：分钟级 / 日级？
- 部署形态：本地启动 / Docker / 远端？

## 已确认（M0 决议 2026-06-28）

- **数据源**：起步使用 mock（`backend/app/data_sources/fixture.py` 提供 GBM 生成的 10 只代表性 ETF × 500 个交易日的 OHLCV），生产接入通过替换 `MarketDataSource` 实现完成
- **回测粒度**：日级（API 强约束：单次回测 ≤ 366 天）
- **部署形态**：本地启动 — 后端 `uvicorn app.main:app --port 8000`，前端 `npm run dev`（Vite 代理 `/api` → `localhost:8000`）