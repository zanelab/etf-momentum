"""config 配置测试。"""


def test_default_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # 重新导入以触发模块级 os.getenv 评估
    import importlib
    import app.core.config as cfg
    importlib.reload(cfg)
    assert cfg.DATABASE_URL == "sqlite:///./etf_momentum.db"


def test_env_overrides_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    import importlib
    import app.core.config as cfg
    importlib.reload(cfg)
    assert cfg.DATABASE_URL == "postgresql://user:pass@localhost/db"
