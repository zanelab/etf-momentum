"""日线行情同步。"""

import logging
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.client import AkshareClient
from app.data.upsert import upsert_daily_price
from app.models.daily_price import DailyPrice

logger = logging.getLogger(__name__)

AKSHARE_EARLIEST = date(2000, 1, 1)


def sync_daily_prices(
    session: Session,
    client: AkshareClient,
    codes: Iterable[str],
    *,
    start: date | None = None,
    end: date | None = None,
    full: bool = False,
) -> dict[str, int]:
    """按 code 列表同步日线行情到 daily_prices 表。

    Args:
        codes: 要同步的 ETF code 列表。
        start: 显式开始日期；full=True 时被忽略。
        end: 结束日期；None 则用今天。
        full: True 时从 akshare 起点拉全量；否则按以下优先级：
              1) 显式 start 2) DB 中该 code 的最后日期+1

    Returns:
        汇总 dict：{"fetched": 尝试只数, "succeeded": 成功数,
                    "failed": 失败数, "rows_written": 总写入行数}
    """
    codes = list(codes)
    succeeded = 0
    failed = 0
    rows_written = 0
    row_end = end or date.today()

    for code in codes:
        try:
            if full:
                row_start = AKSHARE_EARLIEST
            elif start is not None:
                row_start = start
            else:
                row_start = _next_unsynced_date(session, code)

            rows = client.fetch_etf_hist(code, row_start, row_end)
            for r in rows:
                upsert_daily_price(session, code, r)
                rows_written += 1
            session.commit()
            succeeded += 1
        except Exception as e:
            session.rollback()
            failed += 1
            logger.warning("sync daily prices for %s failed: %s", code, e)
            continue

    return {
        "fetched": len(codes),
        "succeeded": succeeded,
        "failed": failed,
        "rows_written": rows_written,
    }


def _next_unsynced_date(session: Session, code: str) -> date:
    """查 DB 中该 code 的最后日期，返回其下一天；若不存在则返回 akshare 起点。"""
    last = session.execute(
        select(DailyPrice.date)
        .where(DailyPrice.code == code)
        .order_by(DailyPrice.date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if last is None:
        return AKSHARE_EARLIEST
    return last + timedelta(days=1)
