"""sync_etf_master 集成测试。"""

from app.data.client import EtfMasterRow, FakeAkshareClient
from app.data.etf_master import sync_etf_master
from app.models.etf import ETF


def test_sync_inserts_new_etfs(db_session):
    client = FakeAkshareClient(etfs=[
        EtfMasterRow(code="510300", name="沪深300ETF", market="SH", category="指数"),
        EtfMasterRow(code="510500", name="中证500ETF", market="SH", category="指数"),
        EtfMasterRow(code="159915", name="创业板ETF", market="SZ", category="指数"),
    ])
    result = sync_etf_master(db_session, client)

    assert result == {"fetched": 3, "upserted": 3}
    assert db_session.query(ETF).count() == 3


def test_sync_updates_existing_etf_name(db_session):
    client1 = FakeAkshareClient(etfs=[
        EtfMasterRow(code="510300", name="旧名", market="SH"),
    ])
    sync_etf_master(db_session, client1)
    assert db_session.query(ETF).filter_by(code="510300").one().name == "旧名"

    client2 = FakeAkshareClient(etfs=[
        EtfMasterRow(code="510300", name="新名", market="SH"),
    ])
    result = sync_etf_master(db_session, client2)

    assert result == {"fetched": 1, "upserted": 1}
    assert db_session.query(ETF).count() == 1
    assert db_session.query(ETF).filter_by(code="510300").one().name == "新名"


def test_sync_handles_empty_response(db_session):
    client = FakeAkshareClient(etfs=[])
    result = sync_etf_master(db_session, client)
    assert result == {"fetched": 0, "upserted": 0}
    assert db_session.query(ETF).count() == 0
