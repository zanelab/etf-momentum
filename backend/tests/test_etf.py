"""ETF model CRUD 测试。"""

from sqlalchemy.exc import IntegrityError

from app.models.etf import ETF
from app.repositories.etf_repository import EtfRepository


def test_create_etf_returns_id(db_session):
    etf = ETF(code="510300", name="沪深300ETF", market="SH")
    db_session.add(etf)
    db_session.commit()

    assert etf.id is not None
    assert etf.id > 0


def test_etf_code_must_be_unique(db_session):
    db_session.add(ETF(code="510300", name="沪深300ETF", market="SH"))
    db_session.commit()

    db_session.add(ETF(code="510300", name="重复", market="SH"))
    import pytest
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_etf_repository_get_by_code(db_session):
    db_session.add(ETF(code="510500", name="中证500ETF", market="SH"))
    db_session.commit()

    repo = EtfRepository(db_session)
    etf = repo.get_by_code("510500")
    assert etf is not None
    assert etf.name == "中证500ETF"


def test_etf_repository_list_all_ordered_by_code(db_session):
    db_session.add_all([
        ETF(code="159915", name="创业板ETF", market="SZ"),
        ETF(code="510300", name="沪深300ETF", market="SH"),
        ETF(code="510500", name="中证500ETF", market="SH"),
    ])
    db_session.commit()

    repo = EtfRepository(db_session)
    codes = [e.code for e in repo.list_all()]
    assert codes == ["159915", "510300", "510500"]
