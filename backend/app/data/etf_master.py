"""ETF 主数据同步。"""

from sqlalchemy.orm import Session

from app.data.client import AkshareClient
from app.data.upsert import upsert_etf


def sync_etf_master(
    session: Session, client: AkshareClient
) -> dict[str, int]:
    """同步全市场 ETF 主数据到 etfs 表。

    Returns:
        汇总 dict：{"fetched": 总数, "upserted": 写入/更新数}
    """
    rows = client.list_etfs()
    upserted = 0
    for row in rows:
        upsert_etf(session, row)
        upserted += 1
    session.commit()
    return {"fetched": len(rows), "upserted": upserted}
