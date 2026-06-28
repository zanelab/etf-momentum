"""Parity test: original main.py filter_etfs vs migrated implementation.

Runs both implementations against identical fixture inputs and asserts that the
target ETF lists match exactly. The original `filter_etfs` runs through a
JoinQuant shim that wires `attribute_history`, `get_current_data`, etc. to the
local fixture CSV source.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.services.screening import (
    DEFAULT_DEFENSIVE_ETF,
)
from app.services.screening import (
    filter_etfs as new_filter_etfs,
)
from app.services.types import StrategyParams
from tests._jq_shim import JQShim

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"


ALL_FIXTURE_ETFS = sorted(p.stem for p in FIXTURES_DIR.glob("*.csv"))

DISPLAY_NAMES = {
    "510300.XSHG": "沪深300ETF",
    "510500.XSHG": "中证500ETF",
    "510050.XSHG": "上证50ETF",
    "510880.XSHG": "红利ETF",
    "511880.XSHG": "银华日利ETF",
    "159915.XSHE": "创业板ETF",
    "159919.XSHE": "嘉实沪深300ETF",
    "518880.XSHG": "黄金ETF",
    "513050.XSHG": "中概互联网ETF",
    "513100.XSHG": "纳指ETF",
}


def _default_config(**overrides) -> dict:
    cfg = {
        "stock_sum": 1,
        "momentum_days": 25,
        "enable_volume_check": True,
        "volume_lookback": 5,
        "volume_threshold": 2.5,
        "ma_short": 20,
        "ma_long": 60,
        "enable_ma_filter": True,
        "defensive_etf": DEFAULT_DEFENSIVE_ETF,
        "enable_industry_diverse": False,
    }
    cfg.update(overrides)
    return cfg


def _new_params(**overrides) -> StrategyParams:
    defaults = dict(
        stock_sum=1,
        momentum_days=25,
        volume_lookback=5,
        volume_threshold=2.5,
        ma_short=20,
        ma_long=60,
        enable_volume_check=True,
        enable_ma_filter=True,
        defensive_etf=DEFAULT_DEFENSIVE_ETF,
        enable_industry_diverse=False,
    )
    defaults.update(overrides)
    return StrategyParams(**defaults)


@pytest.fixture(scope="module")
def shim() -> JQShim:
    return JQShim(display_names=DISPLAY_NAMES)


@pytest.mark.parametrize(
    "as_of,static_pool,dynamic_pool,config_overrides",
    [
        # Case 1: default config, all fixture ETFs, mid-2026
        (
            datetime(2026, 1, 15),
            ALL_FIXTURE_ETFS,
            [],
            {},
        ),
        # Case 2: stock_sum=3, industry diversification on
        (
            datetime(2026, 3, 10),
            ALL_FIXTURE_ETFS,
            [],
            {"stock_sum": 3, "enable_industry_diverse": True},
        ),
        # Case 3: MA filter disabled
        (
            datetime(2026, 5, 20),
            ALL_FIXTURE_ETFS,
            [],
            {"enable_ma_filter": False, "stock_sum": 2},
        ),
    ],
    ids=["default-config", "industry-diverse", "ma-filter-off"],
)
def test_filter_etfs_parity(
    shim: JQShim,
    as_of: datetime,
    static_pool: list[str],
    dynamic_pool: list[str],
    config_overrides: dict,
) -> None:
    config = _default_config(**config_overrides)
    old_targets = shim.filter_etfs(
        as_of,
        static_pool=static_pool,
        dynamic_pool=dynamic_pool,
        config=config,
    )

    # The old implementation uses the THEME_KEYWORDS global from main.py for
    # industry diversification; mirror that input for the new implementation so
    # the two are running on equivalent theme dictionaries.
    themes = shim.shim_ns["THEME_KEYWORDS"]

    pool_for_new = [e for e in static_pool if e != config["defensive_etf"]]
    params_overrides = {
        k: v for k, v in config_overrides.items() if k in StrategyParams.model_fields
    }
    new_targets = new_filter_etfs(
        as_of,
        static_pool=pool_for_new,
        dynamic_pool=dynamic_pool,
        themes=themes,
        params=_new_params(**params_overrides),
        market=shim.market,
        display_names=DISPLAY_NAMES,
    )

    assert old_targets == new_targets, (
        f"Parity mismatch for {as_of.date()} config={config_overrides}\n"
        f"  old (main.py): {old_targets}\n"
        f"  new:           {new_targets}"
    )


def test_shim_runs_main_py_unmodified(tmp_path: Path) -> None:
    """Smoke test: shim executes main.py without source modification."""
    shim = JQShim(display_names=DISPLAY_NAMES)
    result = shim.filter_etfs(
        datetime(2026, 1, 15),
        static_pool=ALL_FIXTURE_ETFS,
        config=_default_config(stock_sum=1),
    )
    assert isinstance(result, list)
