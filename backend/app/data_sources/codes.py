"""ETF code normalization utilities.

Canonical form: `XXXXXX.XSHG` (Shanghai) or `XXXXXX.XSHE` (Shenzhen).

A-share ETF codes are 6 digits. Exchange is inferred by the first digit:
- 5, 6 → XSHG (Shanghai Stock Exchange)
- 1, 0, 3 → XSHE (Shenzhen Stock Exchange)

Inputs in any of these forms are accepted:
- bare 6 digits: `"510300"`
- canonical form: `"510300.XSHG"`
- lowercase canonical: `"510300.xshg"`
- with surrounding whitespace: `"  510300.XSHG  "`

Malformed input raises `ValueError`.
"""
from __future__ import annotations

_VALID_SUFFIXES = ("XSHG", "XSHE")

# A-share ETF first-digit → exchange mapping.
_SHANGHAI_PREFIXES = ("5", "6")
_SHENZHEN_PREFIXES = ("1", "0", "3")


def normalize_etf_code(code: str) -> str:
    """Return the canonical form of an ETF code.

    Examples:
        >>> normalize_etf_code("510300")
        '510300.XSHG'
        >>> normalize_etf_code("159915")
        '159915.XSHE'
        >>> normalize_etf_code("510300.XSHG")
        '510300.XSHG'
        >>> normalize_etf_code("  510300.xshg  ")
        '510300.XSHG'

    Raises:
        ValueError: if `code` is None, empty, not a 6-digit numeric
            (with or without valid suffix), or has an unrecognized prefix.
    """
    if code is None:
        raise ValueError("ETF code must not be None")
    if not isinstance(code, str):
        raise ValueError(f"ETF code must be str, got {type(code).__name__}")
    cleaned = code.strip().upper()
    if not cleaned:
        raise ValueError("ETF code must not be empty")

    # Already-canonical form: 6 digits + dot + suffix (11 chars total)
    if "." in cleaned:
        if len(cleaned) != 11:
            raise ValueError(f"ETF code with suffix must be 11 chars, got {cleaned!r}")
        digits, suffix = cleaned.split(".", 1)
        if suffix not in _VALID_SUFFIXES:
            raise ValueError(f"Invalid exchange suffix: {suffix!r} (expected XSHG or XSHE)")
        if not (len(digits) == 6 and digits.isdigit()):
            raise ValueError(f"ETF code digits must be 6 numeric chars, got {digits!r}")
        return cleaned

    # Bare 6-digit form: infer exchange from first digit
    if len(cleaned) != 6 or not cleaned.isdigit():
        raise ValueError(f"Bare ETF code must be 6 digits, got {cleaned!r}")
    first = cleaned[0]
    if first in _SHANGHAI_PREFIXES:
        return f"{cleaned}.XSHG"
    if first in _SHENZHEN_PREFIXES:
        return f"{cleaned}.XSHE"
    raise ValueError(
        f"Cannot infer exchange for code {cleaned!r} "
        f"(first digit {first!r} is not in {_SHANGHAI_PREFIXES + _SHENZHEN_PREFIXES})"
    )


def same_etf(a: str, b: str) -> bool:
    """Return True if both codes normalize to the same canonical string."""
    return normalize_etf_code(a) == normalize_etf_code(b)
