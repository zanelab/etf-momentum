"""Tests for ETF code normalization utilities.

Canonical form: 'XXXXXX.XSHG' (Shanghai) or 'XXXXXX.XSHE' (Shenzhen).

Exchange inference by first digit (A-share ETF convention):
- 5, 6 → XSHG (Shanghai)
- 1, 0, 3 → XSHE (Shenzhen)
"""
from __future__ import annotations

import pytest

from app.data_sources.codes import normalize_etf_code, same_etf


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Shanghai (5/6 prefix)
        ("510300", "510300.XSHG"),
        ("510050", "510050.XSHG"),
        ("600000", "600000.XSHG"),
        ("588080", "588080.XSHG"),
        ("501018", "501018.XSHG"),
        # Shenzhen (1/0/3 prefix)
        ("159915", "159915.XSHE"),
        ("159206", "159206.XSHE"),
        ("161226", "161226.XSHE"),
        ("000001", "000001.XSHE"),
        ("300750", "300750.XSHE"),
    ],
)
def test_normalize_bare_6digit(raw: str, expected: str) -> None:
    """Bare 6-digit codes infer exchange from first digit."""
    assert normalize_etf_code(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "510300.XSHG",
        "159915.XSHE",
        "600000.XSHG",
        "161226.XSHE",
    ],
)
def test_normalize_idempotent_on_canonical(raw: str) -> None:
    """Canonical input passes through unchanged."""
    assert normalize_etf_code(raw) == raw


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  510300.xshg  ", "510300.XSHG"),
        ("159915.xshe", "159915.XSHE"),
        ("\t510300.XSHG\n", "510300.XSHG"),
    ],
)
def test_normalize_strips_whitespace_and_uppercases(raw: str, expected: str) -> None:
    """Whitespace is stripped and suffix is uppercased."""
    assert normalize_etf_code(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",                # empty
        "abc",             # letters
        "12345",           # 5 digits
        "1234567",         # 7 digits
        "12345X",          # mixed
        "510300.SH",       # wrong suffix
        "510300.SSE",      # wrong suffix
        "410300",          # 6 digits starting with 4 (invalid exchange)
        "910300",          # 6 digits starting with 9 (invalid exchange)
    ],
)
def test_normalize_rejects_malformed(raw: str) -> None:
    """Malformed input raises ValueError."""
    with pytest.raises(ValueError):
        normalize_etf_code(raw)


def test_normalize_rejects_none() -> None:
    """None input raises ValueError."""
    with pytest.raises(ValueError):
        normalize_etf_code(None)  # type: ignore[arg-type]


def test_same_etf_true_across_formats() -> None:
    """same_etf returns True for equivalent codes in different formats."""
    assert same_etf("510300", "510300.XSHG") is True
    assert same_etf("510300.XSHG", "510300") is True
    assert same_etf("  510300.xshg  ", "510300.XSHG") is True


def test_same_etf_false_for_different_etfs() -> None:
    """same_etf returns False for different ETFs even if both well-formed."""
    assert same_etf("510300.XSHG", "159915.XSHE") is False
    assert same_etf("510300", "159915") is False


def test_same_etf_true_for_identical_inputs() -> None:
    """same_etf returns True for identical canonical inputs."""
    assert same_etf("510300.XSHG", "510300.XSHG") is True
    assert same_etf("159915.XSHE", "159915.XSHE") is True


def test_same_etf_propagates_value_error() -> None:
    """same_etf raises ValueError if either input is malformed."""
    with pytest.raises(ValueError):
        same_etf("abc", "510300.XSHG")
    with pytest.raises(ValueError):
        same_etf("510300.XSHG", "abc")
