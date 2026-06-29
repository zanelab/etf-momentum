"""Tests for load_display_names dual-lookup (canonical-form fallback).

Verifies that callers may pass either bare 6-digit codes or canonical
`XXXXXX.XSHG/XSHE` codes and resolve to the same display name.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.db import get_engine, init_db, session_scope
from app.models.static_pool import StaticPool
from app.services.today import load_display_names


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Per-test sqlite DB so seed data is fresh and isolated."""
    monkeypatch.setenv("ETF_DB_PATH", str(tmp_path / "test.db"))
    from app import db as db_module

    db_module.reset_engine_for_tests()
    init_db()
    yield
    db_module.reset_engine_for_tests()


def _seed_static_pool(rows: list[StaticPool]) -> None:
    """Insert raw StaticPool rows directly (bypassing API validation)."""
    with session_scope(get_engine()) as s:
        for r in rows:
            s.add(r)


def test_load_display_names_canonical_input_resolves() -> None:
    """Given static_pool row code='510300.XSHG' name='沪深300'
    When load_display_names(['510300.XSHG']) is called
    Then result maps '510300.XSHG' → '沪深300'.
    """
    _seed_static_pool(
        [
            StaticPool(
                code="510300.XSHG",
                display_name="沪深300ETF",
                enabled=True,
                added_at=datetime(2026, 1, 1),
            )
        ]
    )
    out = load_display_names(["510300.XSHG"])
    assert out == {"510300.XSHG": "沪深300ETF"}


def test_load_display_names_bare_input_falls_back_to_canonical() -> None:
    """Given static_pool row code='510300.XSHG' name='沪深300'
    When load_display_names(['510300']) is called (bare form)
    Then result maps the INPUT key '510300' → '沪深300'.
    The output key is the input code; the value comes from the matched row.
    """
    _seed_static_pool(
        [
            StaticPool(
                code="510300.XSHG",
                display_name="沪深300ETF",
                enabled=True,
                added_at=datetime(2026, 1, 1),
            )
        ]
    )
    out = load_display_names(["510300"])
    assert out == {"510300": "沪深300ETF"}


def test_load_display_names_mixed_inputs_all_resolve() -> None:
    """Both bare and canonical inputs in the same call resolve correctly."""
    _seed_static_pool(
        [
            StaticPool(code="510300.XSHG", display_name="沪深300ETF", enabled=True, added_at=datetime(2026, 1, 1)),
            StaticPool(code="510500.XSHG", display_name="中证500ETF", enabled=True, added_at=datetime(2026, 1, 1)),
        ]
    )
    out = load_display_names(["510300", "510500.XSHG"])
    assert out == {"510300": "沪深300ETF", "510500.XSHG": "中证500ETF"}


def test_load_display_names_unmatched_returns_code_itself() -> None:
    """If neither the input nor its canonical form exists in static_pool,
    the result maps the input to itself (so callers always get a string)."""
    out = load_display_names(["999999"])
    assert out == {"999999": "999999"}


def test_load_display_names_empty_input_returns_empty() -> None:
    """Empty input list returns empty dict."""
    assert load_display_names([]) == {}


def test_load_display_names_exact_match_takes_precedence() -> None:
    """If both an exact match AND a canonical-form match exist, the exact
    match wins (avoids aliasing ambiguity when duplicate-looking codes exist).
    """
    _seed_static_pool(
        [
            StaticPool(code="510300", display_name="裸码", enabled=True, added_at=datetime(2026, 1, 1)),
            StaticPool(code="510300.XSHG", display_name="后缀码", enabled=True, added_at=datetime(2026, 1, 1)),
        ]
    )
    # Asking with bare form: exact match '510300' wins
    out_bare = load_display_names(["510300"])
    assert out_bare == {"510300": "裸码"}
    # Asking with canonical form: exact match wins
    out_canonical = load_display_names(["510300.XSHG"])
    assert out_canonical == {"510300.XSHG": "后缀码"}
