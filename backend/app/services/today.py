"""Determine the "as-of" trading day for current signals / portfolio.

For the local mock we use the latest trading day present in the fixture set.
A production impl would use today's date (or the most recent market close) and
fall back if it's a holiday/weekend.
"""
from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path

import pandas as pd
from sqlmodel import select


def resolve_today(fixtures_dir: Path) -> datetime:
    """Return the latest date available across all fixture CSVs.

    The day starts at 14:00 (after-market close) so downstream consumers see
    a post-close snapshot.
    """
    latest: pd.Timestamp | None = None
    for csv_path in fixtures_dir.glob("*.csv"):
        df = pd.read_csv(csv_path, parse_dates=["date"], usecols=["date"])
        if df.empty:
            continue
        candidate = df["date"].max()
        if latest is None or candidate > latest:
            latest = candidate
    if latest is None:
        raise RuntimeError(f"No fixture CSVs found under {fixtures_dir}")
    return datetime.combine(latest.date(), time(14, 0))


def load_strategy_params(defaults: dict | None = None) -> dict:
    """Read strategy params from the DB and merge over defaults.

    Useful for endpoints that need a flat dict (the screening service wants
    a flat kwargs surface).
    """
    from app import db as db_module
    from app.models.strategy_param import StrategyParam

    merged: dict = dict(defaults or {})
    with db_module.session_scope() as session:
        rows = list(session.exec(select(StrategyParam)).all())
        # Read attributes inside the session to avoid DetachedInstanceError.
        for row in rows:
            try:
                merged[row.key] = json.loads(row.value_json)
            except (json.JSONDecodeError, TypeError):
                merged[row.key] = row.value_json
    return merged


def select_kwargs_for_params(merged: dict, fields: set[str]) -> dict:
    """Project `merged` down to the keys valid for StrategyParams."""
    from app.services.types import StrategyParams
    return {k: v for k, v in merged.items() if k in StrategyParams.model_fields}


def load_static_pool(enabled_only: bool = True) -> list[str]:
    """Return static pool ETF codes ordered by code."""
    from app import db as db_module
    from app.models.static_pool import StaticPool

    with db_module.session_scope() as session:
        stmt = select(StaticPool).order_by(StaticPool.code)
        rows = list(session.exec(stmt).all())
        codes = [r.code for r in rows if (not enabled_only or r.enabled)]
    return codes


def load_themes() -> dict[str, list[str]]:
    """Return the theme keyword dictionary."""
    from app import db as db_module
    from app.models.theme_keyword import ThemeKeyword

    themes: dict[str, list[str]] = {}
    with db_module.session_scope() as session:
        rows = list(
            session.exec(
                select(ThemeKeyword).order_by(ThemeKeyword.theme, ThemeKeyword.keyword)
            ).all()
        )
        for row in rows:
            themes.setdefault(row.theme, []).append(row.keyword)
    return themes


def load_display_names(codes: list[str]) -> dict[str, str]:
    """Return a {input_code: display_name} map for the requested codes.

    Performs a dual-lookup against `static_pool.code`:
    1. Exact match on the input code (canonical-form rows in static_pool).
    2. Fallback to normalized canonical form, so bare 6-digit inputs (akshare)
       resolve to canonical-form rows.

    Output keys preserve the input form (so callers can map back); unmatched
    inputs map to themselves.
    """
    from app import db as db_module
    from app.data_sources.codes import normalize_etf_code
    from app.models.static_pool import StaticPool

    if not codes:
        return {}

    # Pre-compute canonical forms; skip normalization for malformed input
    # (treat as-is so the row lookup still works against legacy bare codes).
    canonical_of: dict[str, str] = {}
    for c in codes:
        try:
            canonical_of[c] = normalize_etf_code(c)
        except ValueError:
            canonical_of[c] = c

    with db_module.session_scope() as session:
        rows = list(session.exec(select(StaticPool)).all())
        # Read attributes inside the session to avoid DetachedInstanceError.
        by_code: dict[str, str] = {r.code: (r.display_name or r.code) for r in rows}

    result: dict[str, str] = {}
    for c in codes:
        # Exact match wins (avoids aliasing when both bare + canonical rows
        # happen to coexist; see test_load_display_names_exact_match_takes_precedence).
        if c in by_code:
            result[c] = by_code[c]
            continue
        canonical = canonical_of[c]
        if canonical != c and canonical in by_code:
            result[c] = by_code[canonical]
            continue
        # No match: fall back to the input code itself so callers always
        # receive a string they can use as a label.
        result[c] = c
    return result
