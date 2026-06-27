"""演示数据集生成器（开发者手工工具，不入 CI / 不入容器镜像）。

通过 akshare 拉取 15 只代表性 ETF 的真实数据，写入 demo_data.json fixture。
仅在 dev 环境手动跑一次，用于刷新仓库内置的演示数据。

⚠️ 演示数据仅用于系统功能演示，不构成投资建议。

Usage:
    cd backend && uv run python -m app.data.seed_demo_generator
    uv run python -m app.data.seed_demo_generator --lookback-days 750
    uv run python -m app.data.seed_demo_generator --output /path/to/demo.json
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from app.data.client import AkshareHttpClient, DailyPriceRow, EtfMasterRow, _coerce_date
from app.signals.compute import SignalRow, compute_signals

logger = logging.getLogger(__name__)


# 15 只目标 ETF：10 宽基 + 5 行业
DEFAULT_CODES: list[str] = [
    # 10 宽基
    "510300",  # 沪深300
    "510500",  # 中证500
    "159915",  # 创业板
    "588000",  # 科创50
    "510880",  # 红利
    "510050",  # 上证50
    "159901",  # 深100
    "510330",  # 华夏300
    "510180",  # 上证180
    "159905",  # 深红利
    # 5 行业
    "512760",  # 半导体
    "512170",  # 医疗
    "512690",  # 酒
    "159928",  # 消费
    "518880",  # 黄金
]

FIXTURE_VERSION = 1


def _infer_market(code: str) -> str:
    """从 ETF 代码前 3 位推断交易所：上海 51x/56x/58x/60x，深圳 15x/16x/18x。"""
    if code.startswith(("51", "56", "58", "60")):
        return "SH"
    if code.startswith(("15", "16", "18")):
        return "SZ"
    return ""


def _fetch_etfs(client: AkshareHttpClient, codes: list[str]) -> list[EtfMasterRow]:
    """从 akshare 拉全市场 ETF 主数据，过滤出目标 codes。"""
    all_etfs = client.list_etfs()
    by_code = {r.code: r for r in all_etfs}
    rows: list[EtfMasterRow] = []
    missing: list[str] = []
    for code in codes:
        if code not in by_code:
            missing.append(code)
            continue
        r = by_code[code]
        rows.append(
            EtfMasterRow(
                code=r.code,
                name=r.name,
                market=_infer_market(r.code) or r.market,
                category=r.category or "指数",
            )
        )
    if missing:
        logger.warning("akshare 未返回以下 ETF: %s（跳过）", missing)
    return rows


def _fetch_prices(
    client: AkshareHttpClient,
    codes: list[str],
    end_date: date,
    lookback_days: int,
) -> dict[str, list[DailyPriceRow]]:
    """对每只 ETF 拉最近 ~lookback_days 个日历天的行情。"""
    # calendar days ≈ trading days × 365/252 × 1.5（含节假日缓冲）
    start = end_date - timedelta(days=int(lookback_days * 365 / 252 * 1.5))
    out: dict[str, list[DailyPriceRow]] = {}
    for code in codes:
        rows = client.fetch_etf_hist(code, start, end_date)
        # 统一日期类型（AkshareHttpClient 在不同 pandas 版本下可能返回 str）
        normalized = [
            DailyPriceRow(
                date=_coerce_date(r.date),
                open=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                volume=r.volume,
            )
            for r in rows
        ]
        out[code] = normalized
        logger.info(
            "fetched %s: %d rows (%s..%s)",
            code, len(normalized),
            normalized[0].date if normalized else "-",
            normalized[-1].date if normalized else "-",
        )
    return out


def _compute_signal(
    codes: list[str],
    prices: dict[str, list[DailyPriceRow]],
    signal_date: date,
    top_n: int = 5,
) -> list[SignalRow]:
    """对 signal_date 当日算 12-1 动量信号。"""
    price_history: dict[str, list[tuple[date, Decimal]]] = {
        code: [(r.date, r.close) for r in prices.get(code, [])]
        for code in codes
    }
    return compute_signals(
        etf_pool=codes,
        price_history=price_history,
        signal_date=signal_date,
        top_n=top_n,
        lookback=252,
        skip=21,
    )


def generate(
    *,
    codes: list[str] = DEFAULT_CODES,
    lookback_days: int = 750,
    output: Path,
) -> dict:
    """生成 fixture，返回 dict（同时 dump 到 output）。"""
    client = AkshareHttpClient()

    logger.info("拉取 ETF 主数据...")
    etfs = _fetch_etfs(client, codes)

    logger.info("拉取日线（lookback=%d 个交易日）...", lookback_days)
    end_date = date.today()
    prices = _fetch_prices(client, codes, end_date, lookback_days)

    last_dates = [rows[-1].date for rows in prices.values() if rows]
    signal_date = max(last_dates) if last_dates else end_date
    logger.info("signal_date = %s", signal_date)

    logger.info("计算 signal snapshot...")
    signal_rows = _compute_signal(codes, prices, signal_date)

    fixture = {
        "version": FIXTURE_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_note": "akshare 一次性快照（演示数据，非投资建议）",
        "etfs": [
            {
                "code": r.code,
                "name": r.name,
                "market": r.market,
                "category": r.category,
            }
            for r in etfs
        ],
        "daily_prices": {
            code: [
                {
                    "date": r.date.isoformat(),
                    "open": str(r.open),
                    "high": str(r.high),
                    "low": str(r.low),
                    "close": str(r.close),
                    "volume": r.volume,
                }
                for r in prices.get(code, [])
            ]
            for code in codes
        },
        "signal_snapshot": {
            "date": signal_date.isoformat(),
            "rows": [
                {
                    "etf_code": row.etf_code,
                    "momentum_score": str(row.momentum_score) if row.momentum_score is not None else None,
                    "rank": row.rank,
                    "action": row.action,
                }
                for row in signal_rows
            ],
        },
        "pool": {
            "name": "宽基三杰",
            "description": "示例宽基 ETF 池（沪深300 + 中证500 + 创业板）",
            "etf_codes": ["510300", "510500", "159915"],
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")

    size_kb = output.stat().st_size / 1024
    n_prices = sum(len(rows) for rows in prices.values())
    actions = [r["action"] for r in fixture["signal_snapshot"]["rows"]]
    buy_n = sum(1 for a in actions if a == "BUY")
    hold_n = sum(1 for a in actions if a == "HOLD")
    watch_n = sum(1 for a in actions if a == "WATCH")
    print(
        f"wrote: etfs={len(etfs)} daily_prices={n_prices} "
        f"signals={len(signal_rows)} (BUY={buy_n} HOLD={hold_n} WATCH={watch_n}) "
        f"pool=宽基三杰 file_size={size_kb:.1f}KB"
    )
    return fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 etf-momentum 演示数据集 fixture")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "fixtures" / "demo_data.json",
        help="输出 JSON 路径（默认 backend/app/data/fixtures/demo_data.json）",
    )
    parser.add_argument(
        "--codes",
        default=",".join(DEFAULT_CODES),
        help="逗号分隔的 ETF codes（默认 15 只）",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=750,
        help="约多少个交易日的日线（默认 750 ≈ 3 年）",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    try:
        generate(codes=codes, lookback_days=args.lookback_days, output=args.output)
    except Exception as e:
        logger.error("生成失败: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())