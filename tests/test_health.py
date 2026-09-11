"""Easy-to-read endpoint tests for the monitoring API."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_service_summary() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "System Health & Service Monitoring API"
    assert body["status"] == "running"


def test_health_endpoint_reports_healthy() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_endpoint_reports_ready() -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["status"] == "ready"


def test_status_endpoint_returns_runtime_information() -> None:
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "operational"
    assert body["environment"] == "development"
    assert body["uptime_seconds"] >= 0
    assert body["python_version"]


def test_unknown_endpoint_returns_not_found() -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
