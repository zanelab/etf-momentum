"""JoinQuant API shim for parity testing.

Loads `main.py` from the repo root in an isolated namespace where every JoinQuant
API (`log`, `attribute_history`, `get_current_data`, etc.) is a stub backed by the
local fixture CSV data. After loading, `shim.filter_etfs(context)` mirrors the
original JoinQuant strategy signature.
"""
from __future__ import annotations

import datetime as _dt
import math
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

from app.data_sources.fixture import FixtureCSVSource

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = REPO_ROOT / "main.py"
FIXTURES_DIR = REPO_ROOT / "backend" / "data" / "fixtures"


class _Log:
    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

    def set_level(self, *args, **kwargs):
        pass


def _make_security_info(code: str, name: str) -> SimpleNamespace:
    return SimpleNamespace(display_name=name, code=code)


def _make_current_data_entry(code: str, market: FixtureCSVSource, as_of: datetime) -> SimpleNamespace:
    snap = market.snapshot(code, as_of)
    return SimpleNamespace(
        last_price=snap["last_price"],
        volume=snap["volume"],
        money=snap["money"],
        paused=False,
        high_limit=snap["last_price"] * 1.10,
        low_limit=snap["last_price"] * 0.90,
        name=code,
    )


class JQShim:
    """Loads main.py with all JoinQuant APIs stubbed."""

    def __init__(
        self,
        display_names: dict[str, str] | None = None,
        static_pool: list[str] | None = None,
    ) -> None:
        self.market = FixtureCSVSource(FIXTURES_DIR)
        self.display_names = display_names or {}
        self.shim_ns: dict[str, Any] = {}
        self._install_globals()
        self._load_main_py(static_pool)

    def _install_globals(self) -> None:
        ns = self.shim_ns
        ns["__name__"] = "main_shim"
        ns["datetime"] = _dt
        ns["math"] = math
        ns["pd"] = pd

        # Logging
        ns["log"] = _Log()

        # Configuration
        def set_option(*args, **kwargs):
            return None

        def set_slippage(*args, **kwargs):
            return None

        class FixedSlippage:
            def __init__(self, *args, **kwargs):
                pass

        class OrderCost:
            def __init__(self, *args, **kwargs):
                pass

        def set_order_cost(*args, **kwargs):
            return None

        def run_daily(*args, **kwargs):
            return None

        def order(*args, **kwargs):
            return None

        def get_all_securities(*args, **kwargs):
            return pd.DataFrame()

        ns["set_option"] = set_option
        ns["set_slippage"] = set_slippage
        ns["FixedSlippage"] = FixedSlippage
        ns["OrderCost"] = OrderCost
        ns["set_order_cost"] = set_order_cost
        ns["run_daily"] = run_daily
        ns["order"] = order
        ns["get_all_securities"] = get_all_securities

        # Market data: history(count, '1d', field, list_of_codes, df=True, skip_paused)
        # JoinQuant semantics: the returned window ends at the bar BEFORE the
        # current session; today's price lives in get_current_data().last_price.
        def history(count, freq, field, codes, df=True, skip_paused=True):
            as_of = self._current_as_of
            end_exclusive = as_of.date() - _dt.timedelta(days=1)
            out = {}
            for code in codes:
                full = self.market.history(
                    code,
                    end_exclusive - _dt.timedelta(days=count * 3),
                    end_exclusive,
                    fields=[field] if isinstance(field, str) else field,
                )
                if full.empty:
                    continue
                out[code] = full[field].tail(count)
            return pd.DataFrame(out) if df else out

        def attribute_history(security, count, freq, fields):
            as_of = self._current_as_of
            end_exclusive = as_of.date() - _dt.timedelta(days=1)
            full = self.market.history(
                security,
                end_exclusive - _dt.timedelta(days=count * 3),
                end_exclusive,
                fields=fields,
            )
            if full.empty:
                return None
            return full.tail(count)

        def get_price(security, start_date, end_date, frequency, fields):
            return self.market.history(security, start_date, end_date, fields=fields)

        def get_security_info(security):
            name = self.display_names.get(security, security)
            return _make_security_info(security, name)

        def get_current_data():
            as_of = self._current_as_of
            return {
                code: _make_current_data_entry(code, self.market, as_of)
                for code in self._current_pool
            }

        ns["history"] = history
        ns["attribute_history"] = attribute_history
        ns["get_price"] = get_price
        ns["get_security_info"] = get_security_info
        ns["get_current_data"] = get_current_data

    def _load_main_py(self, static_pool: list[str] | None) -> None:
        source = MAIN_PY.read_text(encoding="utf-8")
        # Compile first so syntax errors surface with file/line info.
        code = compile(source, str(MAIN_PY), "exec")
        ns = self.shim_ns
        ns["g_dynamic_pool"] = []
        if static_pool is not None:
            ns["STATIC_ETF_POOL"] = list(static_pool)
        exec(code, ns)

    def configure(
        self,
        as_of: datetime,
        static_pool: list[str] | None = None,
        dynamic_pool: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> SimpleNamespace:
        """Set up context + STRATEGY_CONFIG for one filter_etfs() invocation."""
        self._current_as_of = as_of
        self._current_pool = []
        ns = self.shim_ns

        if static_pool is not None:
            ns["STATIC_ETF_POOL"] = list(static_pool)
        self._current_pool.extend(ns["STATIC_ETF_POOL"])
        if dynamic_pool is not None:
            ns["g_dynamic_pool"] = list(dynamic_pool)
            self._current_pool.extend(ns["g_dynamic_pool"])
        else:
            ns["g_dynamic_pool"] = []
        self._current_pool = list(set(self._current_pool))

        if config is not None:
            ns["STRATEGY_CONFIG"] = dict(config)
        # else: leave the defaults from main.py untouched

        return SimpleNamespace(current_dt=as_of, portfolio=SimpleNamespace(positions={}))

    def filter_etfs(self, as_of: datetime, **kwargs) -> list[str]:
        ctx = self.configure(as_of, **kwargs)
        return self.shim_ns["filter_etfs"](ctx)
