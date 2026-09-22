from fastapi.testclient import TestClient

from app.db import check_database
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready_when_database_reachable():
    app.dependency_overrides[check_database] = lambda: True
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.pop(check_database, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_ready_returns_503_when_database_unreachable():
    app.dependency_overrides[check_database] = lambda: False
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.pop(check_database, None)

    assert response.status_code == 503
    assert response.json() == {"status": "not ready", "checks": {"database": "unreachable"}}


def test_metrics_exposes_prometheus_format():
    # Hit an endpoint first so the counter has at least one sample.
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "pulse_http_requests_total" in response.text
    assert "pulse_http_request_duration_seconds" in response.text
