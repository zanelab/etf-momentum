"""akshare 数据同步 CLI 入口。

Usage:
    python -m app.data.sync etfs
    python -m app.data.sync prices --codes 510300,510500
    python -m app.data.sync prices --codes 510300 --start 2024-01-01 --end 2024-12-31
    python -m app.data.sync prices --codes 510300 --full
    python -m app.data.sync prices --all --full          # 同步 etfs 表里所有 code
    python -m app.data.sync prices --all                 # 增量同步（按各 code 最后日期+1）
"""

import argparse
import json
import logging
import sys
from datetime import date

from sqlalchemy import select

from app.data.client import AkshareClient, AkshareHttpClient
from app.data.daily_prices import sync_daily_prices
from app.data.etf_master import sync_etf_master
from app.db.session import SessionLocal
from app.models.etf import ETF

logger = logging.getLogger(__name__)


def _build_client() -> AkshareClient:
    """默认构造真实 akshare 客户端。测试可通过 monkeypatch 替换。"""
    return AkshareHttpClient()


def cmd_etfs(_args: argparse.Namespace) -> int:
    session = SessionLocal()
    try:
        client = _build_client()
        result = sync_etf_master(session, client)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["upserted"] > 0 or result["fetched"] == 0 else 1
    finally:
        session.close()


def cmd_prices(args: argparse.Namespace) -> int:
    if args.all:
        session = SessionLocal()
        try:
            codes = list(session.execute(select(ETF.code).order_by(ETF.code)).scalars())
        finally:
            session.close()
        if not codes:
            print("ERROR: --all 需要 etfs 表非空；先跑 `sync etfs`", file=sys.stderr)
            return 2
    else:
        codes = [c.strip() for c in (args.codes or "").split(",") if c.strip()]
        if not codes:
            print("ERROR: 必须指定 --codes 或 --all", file=sys.stderr)
            return 2

    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    session = SessionLocal()
    try:
        client = _build_client()
        result = sync_daily_prices(
            session,
            client,
            codes,
            start=start,
            end=end,
            full=args.full,
        )
        print(json.dumps(result, ensure_ascii=False))
        if result["failed"] > 0 and result["succeeded"] == 0:
            return 2
        if result["failed"] > 0:
            return 1
        return 0
    finally:
        session.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.data.sync",
        description="akshare 数据同步 CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_etfs = sub.add_parser("etfs", help="同步全市场 ETF 主数据到 etfs 表")
    p_etfs.set_defaults(func=cmd_etfs)

    p_prices = sub.add_parser("prices", help="同步 ETF 日线行情")
    code_source = p_prices.add_mutually_exclusive_group(required=True)
    code_source.add_argument("--codes", help="逗号分隔的 ETF code 列表")
    code_source.add_argument("--all", action="store_true", help="同步 etfs 表中全部 code")
    p_prices.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    p_prices.add_argument("--end", help="结束日期 (YYYY-MM-DD)")
    p_prices.add_argument("--full", action="store_true", help="拉全量历史")
    p_prices.set_defaults(func=cmd_prices)

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
