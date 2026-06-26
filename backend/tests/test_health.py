"""健康检查端点的测试。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_status():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_require_external_resources():
    """健康检查不应因为缺少下游依赖（数据库、外部 API）而失败。"""
    response = client.get("/health")
    assert response.status_code == 200


def test_docs_endpoint_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_endpoint_available():
    response = client.get("/redoc")
    assert response.status_code == 200
