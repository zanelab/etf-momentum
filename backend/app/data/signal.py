"""实时信号 CLI 入口。

Usage:
    python -m app.data.signal run --date 2024-12-31 --pool 510300,510500
    python -m app.data.signal show --date 2024-12-31
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.daily_price import DailyPrice
from app.models.signal_snapshot import SignalSnapshot
from app.signals.compute import compute_signals
from app.signals.persistence import save_signal_snapshot

logger = logging.getLogger(__name__)


def _load_price_history(
    session,
    pool: list[str],
    signal_date: date,
    lookback: int,
    skip: int,
) -> dict[str, list[tuple[date, Decimal]]]:
    """从 daily_prices 读每只 ETF 在 signal_date 之前 (lookback+skip+1) 个 close。"""
    limit = lookback + skip + 1
    history: dict[str, list[tuple[date, Decimal]]] = {}
    for code in pool:
        rows = session.execute(
            select(DailyPrice.date, DailyPrice.close)
            .where(DailyPrice.code == code, DailyPrice.date < signal_date)
            .order_by(DailyPrice.date.desc())
            .limit(limit)
        ).all()
        # 按日期升序
        rows.reverse()
        history[code] = [(d, close) for d, close in rows]
    return history


def cmd_run(args: argparse.Namespace) -> int:
    signal_date = date.fromisoformat(args.date)
    pool = [c.strip() for c in args.pool.split(",") if c.strip()]
    lookback = 252
    skip = 21

    session = SessionLocal()
    try:
        history = _load_price_history(session, pool, signal_date, lookback, skip)
        rows = compute_signals(
            pool, history, signal_date,
            top_n=args.top_n, lookback=lookback, skip=skip,
        )
        written = save_signal_snapshot(
            session, signal_date, rows, overwrite=args.force,
        )
        skipped = len(pool) - len(written) if not args.force else 0
        print(f"wrote {len(written)} rows to signal_snapshots"
              + (f", skipped {skipped} (use --force to overwrite)" if skipped else ""))
        return 0
    finally:
        session.close()


def cmd_show(args: argparse.Namespace) -> int:
    signal_date = date.fromisoformat(args.date)
    session = SessionLocal()
    try:
        snaps = session.execute(
            select(SignalSnapshot)
            .where(SignalSnapshot.date == signal_date)
            .order_by(SignalSnapshot.rank.is_(None), SignalSnapshot.rank, SignalSnapshot.etf_code)
        ).scalars().all()
        if not snaps:
            print(f"No snapshot for {args.date}")
            return 0
        print(f"{'rank':>4}  {'code':<8}  {'score':>10}  action")
        for s in snaps:
            score_str = f"{s.momentum_score:.6f}" if s.momentum_score is not None else "       N/A"
            rank_str = f"{s.rank:>4}" if s.rank is not None else "  N/A"
            print(f"{rank_str}  {s.etf_code:<8}  {score_str:>10}  {s.action}")
        return 0
    finally:
        session.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.data.signal",
        description="实时信号计算与查询 CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="计算并落库指定日期的信号快照")
    p_run.add_argument("--date", required=True, help="信号日期 YYYY-MM-DD")
    p_run.add_argument("--pool", required=True, help="ETF 池，逗号分隔")
    p_run.add_argument("--top-n", type=int, default=5, help="top N 买入（默认 5）")
    p_run.add_argument("--force", action="store_true", help="覆盖已存在的同 date 快照")
    p_run.set_defaults(func=cmd_run)

    p_show = sub.add_parser("show", help="查询指定日期的信号快照")
    p_show.add_argument("--date", required=True, help="信号日期 YYYY-MM-DD")
    p_show.set_defaults(func=cmd_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
