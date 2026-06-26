# Spec: akshare 数据同步脚本

## ADDED Requirements

### Requirement: AkshareClient Protocol 抽象
`AkshareClient` 是 sync 模块与具体数据源之间的契约。所有 sync 函数只依赖此 Protocol，便于测试时注入假数据。

#### Scenario: 定义 Protocol 接口
- Given Python 类型注解 `class AkshareClient(Protocol)`
- When 检查 `list_etfs()` 与 `fetch_etf_hist(code, start, end)` 两个方法签名
- Then 两者均为 Protocol 方法，无具体实现

### Requirement: AkshareHttpClient 真实实现
`AkshareHttpClient` 通过 `import akshare as ak` 调用真实 akshare API。

#### Scenario: list_etfs 返回 ETF 列表
- Given `ak.fund_etf_spot_em()` 返回全市场 ETF 实时数据 DataFrame
- When 调用 `AkshareHttpClient().list_etfs()`
- Then 返回 `list[EtfMasterRow]`，每行含 code / name / market / category

#### Scenario: fetch_etf_hist 返回日线 OHLCV
- Given `ak.fund_etf_hist_em(symbol=code, period='daily', start_date=..., end_date=...)` 返回 DataFrame
- When 调用 `client.fetch_etf_hist("510300", date(2024,1,1), date(2024,1,31))`
- Then 返回 `list[DailyPriceRow]`，每行含 date / open / high / low / close / volume

### Requirement: FakeAkshareClient 测试替身
`FakeAkshareClient` 在测试时预设返回值，无需网络。

#### Scenario: 预设数据返回
- Given `FakeAkshareClient(etfs=[...], prices={"510300": [...]})`
- When 调用 `list_etfs()` 与 `fetch_etf_hist("510300", ...)`
- Then 返回预设的 ETF 与日线数据

### Requirement: ETF 主数据同步函数
`sync_etf_master(session, client)` 拉取 ETF 列表并 upsert 到 `etfs` 表。

#### Scenario: 首次同步插入新 ETF
- Given `etfs` 表为空，`client.list_etfs()` 返回 3 条 ETF
- When 调用 `sync_etf_master(session, client)`
- Then `etfs` 表新增 3 条记录

#### Scenario: 重复同步不抛错（upsert）
- Given `etfs` 表已有 `code='510300'` 的记录（name='旧名称'）
- When `client.list_etfs()` 返回 `code='510300', name='新名称'`
- And 调用 `sync_etf_master(session, client)`
- Then 不抛 IntegrityError；记录被更新为 '新名称'

### Requirement: 日线行情同步函数
`sync_daily_prices(session, client, codes, start=None, end=None, full=False)` 按 code 拉取并 upsert 到 `daily_prices` 表。

#### Scenario: 首次同步插入新行情
- Given `daily_prices` 表为空
- When 调用 `sync_daily_prices(session, client, codes=['510300'], start=date(2024,1,1), end=date(2024,1,3))`
- Then `daily_prices` 表新增对应 (510300, 2024-01-01) ~ (510300, 2024-01-03) 记录

#### Scenario: 重复同步 upsert
- Given `daily_prices` 表已有 (510300, 2024-01-02) 记录
- When 再次 sync 同一区间
- Then 不抛 IntegrityError；记录被更新

#### Scenario: full 模式拉全量
- Given `daily_prices` 表已有 510300 至 2024-01-10 的数据
- When 调用 `sync_daily_prices(..., codes=['510300'], full=True)`
- Then 从 akshare 起点拉取全量，覆盖已有区间

### Requirement: 单只 ETF 失败不中断
`sync_daily_prices` 中单只 ETF 拉取失败时记录日志并继续。

#### Scenario: 单只失败继续下一只
- Given `client.fetch_etf_hist('510300', ...)` 抛 `ValueError`
- And `client.fetch_etf_hist('510500', ...)` 正常返回
- When 调用 `sync_daily_prices(session, client, codes=['510300','510500'], ...)`
- Then 510500 数据写入；510300 跳过并记录 warning 日志

### Requirement: CLI 入口
`python -m app.data.sync etfs` 与 `python -m app.data.sync prices` 两个子命令。

#### Scenario: etfs 子命令
- Given CLI 调用 `python -m app.data.sync etfs`
- When 执行
- Then 同步全市场 ETF 主数据，stdout 输出成功/失败计数

#### Scenario: prices 子命令指定 codes
- Given CLI 调用 `python -m app.data.sync prices --codes 510300,510500`
- When 执行
- Then 同步这两只 ETF 的历史行情

#### Scenario: prices 子命令 full 模式
- Given CLI 调用 `python -m app.data.sync prices --codes 510300 --full`
- When 执行
- Then 从 akshare 起点拉取 510300 全量历史

### Requirement: upsert_etf 工具函数
`upsert_etf(session, EtfMasterRow)` 提供单条 upsert，使用 SQLite `on_conflict_do_update`。

#### Scenario: upsert 单条 ETF
- Given `upsert_etf(session, EtfMasterRow(code='510300', name='沪深300ETF', market='SH', category='指数'))`
- When session commit
- Then `etfs` 表新增/更新该记录

### Requirement: upsert_daily_price 工具函数
`upsert_daily_price(session, code, DailyPriceRow)` 提供单条 upsert，按 (code, date) 唯一索引。

#### Scenario: upsert 单条日线
- Given `upsert_daily_price(session, '510300', DailyPriceRow(date=..., open=..., ...))`
- When session commit
- Then `daily_prices` 表新增/更新该 (code, date) 记录

### Requirement: 测试覆盖同步逻辑
pytest 套件覆盖 FakeAkshareClient + 真实 sync 函数 + CLI 冒烟。

#### Scenario: pytest 全部通过
- Given pytest 在 backend 目录运行
- When 收集所有 `tests/test_*.py`
- Then 全部通过；退出码 0

### Requirement: README 增补数据同步章节
`backend/README.md` 新增「数据同步」小节，说明 CLI 用法。

#### Scenario: README 包含同步命令
- Given 阅读 `backend/README.md`
- When 查找「数据同步」章节
- Then 包含 `python -m app.data.sync etfs` 与 `python -m app.data.sync prices` 用法示例
