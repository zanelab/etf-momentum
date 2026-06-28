"""Generate 2 years of daily CSV fixtures for representative ETFs.

Run from repo root:
    python -m backend.scripts.generate_fixtures

Or:
    cd backend && python -m scripts.generate_fixtures

Output: backend/data/fixtures/<code>.csv
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# (code, base_price, daily_vol, daily_drift, avg_money)
FIXTURES: list[tuple[str, float, float, float, float]] = [
    ("510300.XSHG", 3.85, 0.012, 0.0002, 4.5e8),
    ("510500.XSHG", 5.70, 0.014, 0.0003, 3.0e8),
    ("510050.XSHG", 2.95, 0.013, 0.0002, 2.5e8),
    ("510880.XSHG", 1.000, 0.001, 0.00005, 5.0e7),
    ("511880.XSHG", 100.00, 0.0008, 0.00003, 8.0e7),
    ("159915.XSHE", 2.50, 0.020, 0.0004, 2.0e8),
    ("159919.XSHE", 3.30, 0.018, 0.0003, 2.2e8),
    ("518880.XSHG", 4.20, 0.010, 0.0002, 1.5e8),
    ("513050.XSHG", 1.20, 0.025, 0.0006, 1.8e8),
    ("513100.XSHG", 1.50, 0.024, 0.0005, 1.6e8),
]


def generate_one(
    code: str,
    base_price: float,
    daily_vol: float,
    daily_drift: float,
    avg_money: float,
    start: date,
    days: int,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=days)
    rets = rng.normal(loc=daily_drift, scale=daily_vol, size=days)
    closes = base_price * np.exp(np.cumsum(rets))
    opens = closes * (1.0 + rng.normal(0, 0.002, size=days))
    highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0, 0.003, size=days)))
    lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0, 0.003, size=days)))
    base_vol = avg_money / np.maximum(closes, 1e-6)
    volumes = (base_vol * (1.0 + rng.normal(0, 0.10, size=days))).clip(min=0).astype(int)
    money = (closes * volumes).round(2)
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "open": np.round(opens, 4),
            "high": np.round(highs, 4),
            "low": np.round(lows, 4),
            "close": np.round(closes, 4),
            "volume": volumes,
            "money": money,
        }
    )


def main(out_dir: Path, end: date, days: int, base_seed: int = 42) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    start = end - timedelta(days=int(days * 1.6))
    for idx, (code, base, vol, drift, money) in enumerate(FIXTURES):
        df = generate_one(code, base, vol, drift, money, start, days, seed=base_seed + idx)
        path = out_dir / f"{code}.csv"
        df.to_csv(path, index=False)
        print(f"  wrote {path} ({len(df)} rows, {df['date'].iloc[0]}..{df['date'].iloc[-1]})")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    out = repo_root / "backend" / "data" / "fixtures"
    end = date.today()
    main(out, end=end, days=500, base_seed=42)
    print(f"\nGenerated {len(FIXTURES)} fixtures in {out}")
