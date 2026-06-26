# Design: akshare 数据同步脚本

> 2026-06-26 brainstorming 阶段产出。基于用户确认的 4 项关键决策。

## 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| Akshare 客户端抽象 | Protocol + DI（依赖注入） | sync 函数接 `AkshareClient` Protocol；运行时注入 `AkshareHttpClient`，测试注入 `FakeAkshareClient`。无网络依赖测试，akshare 升级不破坏 sync 逻辑 |
| Upsert 实现 | `sqlalchemy.dialects.sqlite.insert(...).on_conflict_do_update(...)` | SQLite 原生 upsert，与 `UNIQUE(code, date)` 配合；后续切 PG 时改 `pg.insert` 即可 |
| 默认同步粒度 | 增量 + 显式 `--full` | `sync prices` 默认从 DB 中该 code 的最后日期+1 开始；`--full` 拉全量历史。避免重复抓取历史 |
| 错误处理 | log + 跳过 + 续 | 单只 ETF 抓取失败时 `logger.warning`，继续下一只；最终返回汇总（成功/失败/跳过计数） |
| 数据来源 | akshare 单源 | A 股事实标准；MVP 不引入 baostock |
| CLI 框架 | argparse（标准库） | 无额外依赖；参数稳定后切换 click/typer 无影响 |
| 日志格式 | `logging.basicConfig` + 标准库 | 简单可控；后续可换 loguru/structlog |
| akshare 限流 | 调用间 `time.sleep(0.5)` | 简单有效；未来可加 token bucket |
| ETF 元数据 | akshare `fund_etf_spot_em()` → 全市场 ETF 实时列表（含 code/name） | 一站式拉取；category 字段 akshare 不直接给，从 name 启发式解析（指数/行业/主题），首版简单处理 |
| 历史行情 | akshare `fund_etf_hist_em(symbol=..., period='daily', start_date, end_date)` | 返回标准 OHLCV DataFrame |

## 模块结构

```
backend/app/
├── data/
│   ├── __init__.py
│   ├── client.py              # AkshareClient Protocol + AkshareHttpClient + FakeAkshareClient
│   ├── etf_master.py          # sync_etf_master(session, client) 函数
│   ├── daily_prices.py        # sync_daily_prices(session, client, codes, start, end, full) 函数
│   ├── upsert.py              # upsert_etf(), upsert_daily_price() 工具
│   └── sync.py                # CLI 入口（argparse + 子命令 etfs / prices）
└── (其他既有目录)
```

## 协议设计

```python
class AkshareClient(Protocol):
    def list_etfs(self) -> list[EtfMasterRow]: ...
    def fetch_etf_hist(self, code: str, start: date, end: date) -> list[DailyPriceRow]: ...

@dataclass(frozen=True)
class EtfMasterRow:
    code: str
    name: str
    market: str  # 'SH' / 'SZ'
    category: str | None

@dataclass(frozen=True)
class DailyPriceRow:
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
```

`AkshareHttpClient` 用 `ak.fund_etf_spot_em()` + `ak.fund_etf_hist_em()` 真实调用。
`FakeAkshareClient` 提供 fixture 化的 fixture-friendly 假数据，单测用。

## Upsert 实现

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

def upsert_etf(session: Session, row: EtfMasterRow) -> None:
    stmt = sqlite_insert(ETF).values(
        code=row.code, name=row.name, market=row.market, category=row.category,
    ).on_conflict_do_update(
        index_elements=[ETF.code],
        set_={"name": row.name, "market": row.market, "category": row.category},
    )
    session.execute(stmt)
```

`upsert_daily_price` 同理，index_elements=`[DailyPrice.code, DailyPrice.date]`，更新 OHLCV 与 volume。

## 增量同步逻辑

```python
def sync_daily_prices(session, client, codes, start=None, end=None, full=False):
    for code in codes:
        try:
            if full or start is None:
                row_start = date(2000, 1, 1)  # akshare 起点
            else:
                row_start = start
            rows = client.fetch_etf_hist(code, row_start, end or date.today())
            for row in rows:
                upsert_daily_price(session, DailyPriceRow(code=code, ...))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning("sync %s failed: %s", code, e)
            continue
```

后续可加入「若未指定 start 则查 DB 最后日期」逻辑（首版简化处理）。

## CLI

```
python -m app.data.sync etfs            # 同步全市场 ETF 主数据
python -m app.data.sync prices --codes 510300,510500
python -m app.data.sync prices --codes 510300 --full
python -m app.data.sync prices --codes 510300 --start 2024-01-01 --end 2024-12-31
```

退出码：0 全部成功 / 1 部分失败 / 2 全部失败。

## 测试策略

- **FakeAkshareClient**：单测用，预设几行 ETF + 几行 daily price
- **sync_etf_master**：测试 upsert 行为（重复 sync 不抛错，name 更新）
- **sync_daily_prices**：测试增量（start/end）、full 模式、错误跳过
- **CLI 烟测**：`subprocess.run([sys.executable, "-m", "app.data.sync", "etfs", "--dry-run"])`
- **不使用真实 akshare**：CI / 测试环境无外网，依赖 fake

## 关键风险与缓解

| 风险 | 缓解 |
|------|------|
| akshare 升级破坏 API | Protocol 抽象 + adapter 隔离，单点修复 |
| akshare 反爬限流 | 调用间 `time.sleep(0.5)`；后续可加重试 |
| ETF 退市 / 新上市 | 增量 upsert 自然处理（已存在则更新，不存在则插入） |
| 数据精度 | DailyPriceRow 字段用 Decimal，与 ORM Numeric(10,4) 对齐 |
| `category` 字段 akshare 不提供 | 首版从 name 启发式解析；为空也允许（schema 允许 NULL） |
| ETF 全市场列表过大 | akshare 返回 ~500 只；全量 sync 一次性执行 < 10s |

## 不在本 change 范围

- 任务调度（cron / APScheduler）
- baostock 接入
- 分钟级实时数据
- 数据校验、告警、去重异常值
- Docker compose
