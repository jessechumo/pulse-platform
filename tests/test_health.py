from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_metrics_exposes_prometheus_format():
    # Hit an endpoint first so the counter has at least one sample.
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "pulse_http_requests_total" in response.text
    assert "pulse_http_request_duration_seconds" in response.text
