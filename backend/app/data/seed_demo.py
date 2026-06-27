"""演示数据 Loader CLI：把 demo_data.json fixture 灌入当前 SQLite。

Usage:
    cd backend && uv run python -m app.data.seed_demo
    # 或容器内：
    docker compose exec backend uv run python -m app.data.seed_demo

行为：
- 读取 backend/app/data/fixtures/demo_data.json
- upsert ETF 主数据（基于 code 唯一索引）
- upsert 日线行情（基于 (code, date) 唯一索引）
- 写入 signal snapshot（overwrite=True，二次执行覆盖）
- 创建示例 pool（PoolService.create；name 重复时跳过，保证幂等）
- 全部 upsert 完成后打印摘要

幂等：重复执行 exit 0，行数无变化。

⚠️ 演示数据仅用于系统功能演示，不构成投资建议。
"""

import argparse
import json
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.data.client import EtfMasterRow, DailyPriceRow
from app.data.upsert import upsert_daily_price, upsert_etf
from app.db.session import SessionLocal
from app.services.pool_service import PoolNameConflictError, PoolService
from app.signals.compute import SignalRow
from app.signals.persistence import save_signal_snapshot
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


SUPPORTED_VERSION = 1
DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "demo_data.json"
BATCH_SIZE = 1000  # 每日线 batch commit，避免长事务


def _parse_signal_row(d: dict) -> SignalRow:
    """把 JSON dict 还原为 SignalRow。"""
    score = d.get("momentum_score")
    return SignalRow(
        etf_code=d["etf_code"],
        momentum_score=Decimal(score) if score is not None else None,
        rank=d.get("rank"),
        action=d["action"],
    )


def load_demo_data(session: Session, fixture_path: Path) -> dict:
    """读取 fixture JSON 并 upsert 到 session 绑定的 DB。

    Raises:
        FileNotFoundError: fixture 文件不存在
        ValueError: version 字段不兼容
        Exception: 任意 DB 写入失败时整批 rollback
    """
    if not fixture_path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture_path}")

    raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    version = raw.get("version")
    if version != SUPPORTED_VERSION:
        raise ValueError(
            f"Unsupported demo data version: {version} (expected {SUPPORTED_VERSION})"
        )

    etfs = raw.get("etfs", [])
    daily_prices = raw.get("daily_prices", {})
    snapshot = raw.get("signal_snapshot", {})
    pool_meta = raw.get("pool", {})

    # 1. ETF 主数据
    for d in etfs:
        upsert_etf(
            session,
            EtfMasterRow(
                code=d["code"],
                name=d["name"],
                market=d["market"],
                category=d.get("category"),
            ),
        )
    session.flush()

    # 2. 日线（分批 commit）
    total_price_rows = 0
    pending = 0
    for code, rows in daily_prices.items():
        for r in rows:
            upsert_daily_price(
                session,
                code,
                DailyPriceRow(
                    date=date.fromisoformat(r["date"]),
                    open=Decimal(r["open"]),
                    high=Decimal(r["high"]),
                    low=Decimal(r["low"]),
                    close=Decimal(r["close"]),
                    volume=int(r["volume"]),
                ),
            )
            pending += 1
            total_price_rows += 1
            if pending >= BATCH_SIZE:
                session.commit()
                pending = 0
    if pending:
        session.commit()

    # 3. Signal snapshot
    snapshot_date = date.fromisoformat(snapshot["date"])
    snapshot_rows = [_parse_signal_row(r) for r in snapshot.get("rows", [])]
    save_signal_snapshot(session, snapshot_date, snapshot_rows, overwrite=True)

    # 4. 示例 pool（幂等：name 重复跳过）
    pool_created = False
    if pool_meta:
        svc = PoolService(session)
        try:
            svc.create(
                name=pool_meta["name"],
                description=pool_meta.get("description"),
                etf_codes=list(pool_meta["etf_codes"]),
            )
            pool_created = True
        except PoolNameConflictError:
            logger.info("pool '%s' 已存在，跳过创建", pool_meta["name"])

    return {
        "etfs": len(etfs),
        "daily_prices": total_price_rows,
        "signals": len(snapshot_rows),
        "pool": pool_meta.get("name"),
        "pool_created": pool_created,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="灌入 etf-momentum 演示数据集")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help=f"fixture JSON 路径（默认 {DEFAULT_FIXTURE_PATH}）",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    session = SessionLocal()
    try:
        summary = load_demo_data(session, args.fixture)
        print(
            f"loaded: etfs={summary['etfs']} daily_prices={summary['daily_prices']} "
            f"signals={summary['signals']} pool={summary['pool']}"
        )
        return 0
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        session.rollback()
        print(f"ERROR: load failed: {e}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())