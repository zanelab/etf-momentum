"""Tests for portfolio DB service."""
from __future__ import annotations

import pytest

from app.db import init_db
from app.services.portfolio import delete_holding, get_all_holdings, upsert_holding


def test_get_all_holdings_empty():
    """Empty database returns empty list."""
    init_db()
    assert get_all_holdings() == []


def test_upsert_and_get():
    """Upsert creates a record that can be retrieved."""
    init_db()
    h = upsert_holding("510300.XSHG", "华夏沪深300ETF", 10000, 3.85)
    assert h.code == "510300.XSHG"
    assert h.shares == 10000
    assert h.cost_price == 3.85

    holdings = get_all_holdings()
    assert len(holdings) == 1
    assert holdings[0].code == "510300.XSHG"
    assert holdings[0].shares == 10000


def test_upsert_updates_existing():
    """Upserting the same code updates rather than duplicates."""
    init_db()
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 10000, 3.85)
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 20000, 4.00)

    holdings = get_all_holdings()
    assert len(holdings) == 1
    assert holdings[0].shares == 20000
    assert holdings[0].cost_price == 4.00


def test_delete_holding():
    """Delete removes the record."""
    init_db()
    upsert_holding("510300.XSHG", "华夏沪深300ETF", 10000, 3.85)
    deleted = delete_holding("510300.XSHG")
    assert deleted is True
    assert get_all_holdings() == []


def test_delete_nonexistent():
    """Deleting a non-existent code returns False."""
    init_db()
    deleted = delete_holding("nonexistent")
    assert deleted is False
