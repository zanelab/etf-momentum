"""Tests for make_source() factory."""
from app.data_sources import make_source
from app.data_sources.akshare_source import AkShareSource
from app.data_sources.cache import CachedSource
from app.data_sources.fixture import FixtureCSVSource


def test_make_source_default_is_fixture(monkeypatch) -> None:
    monkeypatch.delenv("ETF_DATA_SOURCE", raising=False)
    src = make_source()
    assert isinstance(src, FixtureCSVSource)


def test_make_source_from_env_var(monkeypatch) -> None:
    """ETF_DATA_SOURCE=akshare returns CachedSource(AkShareSource) — even if
    akshare isn't installed, the wrapper import succeeds (the AkShareSource
    constructor fails only at call time without akshare)."""
    monkeypatch.setenv("ETF_DATA_SOURCE", "akshare")
    # Inject fake akshare so the import in AkShareSource.__init__ resolves
    import sys
    import types

    sys.modules["akshare"] = types.ModuleType("akshare")
    sys.modules["akshare"].fund_etf_hist_em = lambda *a, **kw: None
    sys.modules["akshare"].fund_etf_name_em = lambda *a, **kw: None
    try:
        src = make_source()
        assert isinstance(src, CachedSource)
        assert isinstance(src._inner, AkShareSource)
    finally:
        monkeypatch.delenv("ETF_DATA_SOURCE", raising=False)
        sys.modules.pop("akshare", None)


def test_make_source_explicit_name_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("ETF_DATA_SOURCE", "akshare")
    src = make_source("fixture")
    assert isinstance(src, FixtureCSVSource)


def test_make_source_unknown_name_raises(monkeypatch) -> None:
    monkeypatch.delenv("ETF_DATA_SOURCE", raising=False)
    try:
        make_source("nonexistent")
    except ValueError as e:
        assert "nonexistent" in str(e)
        assert "fixture" in str(e)
        assert "akshare" in str(e)
    else:
        raise AssertionError("Expected ValueError")
