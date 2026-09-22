from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.cache import check_redis
from app.db import check_database
from app.main import app

client = TestClient(app)


@contextmanager
def readiness_overrides(*, database_ok: bool, redis_ok: bool):
    app.dependency_overrides[check_database] = lambda: database_ok
    app.dependency_overrides[check_redis] = lambda: redis_ok
    try:
        yield
    finally:
        app.dependency_overrides.pop(check_database, None)
        app.dependency_overrides.pop(check_redis, None)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready_when_all_dependencies_reachable():
    with readiness_overrides(database_ok=True, redis_ok=True):
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok"},
    }


def test_ready_returns_503_when_database_unreachable():
    with readiness_overrides(database_ok=False, redis_ok=True):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not ready",
        "checks": {"database": "unreachable", "redis": "ok"},
    }


def test_ready_returns_503_when_redis_unreachable():
    with readiness_overrides(database_ok=True, redis_ok=False):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not ready",
        "checks": {"database": "ok", "redis": "unreachable"},
    }


def test_metrics_exposes_prometheus_format():
    # Hit an endpoint first so the counter has at least one sample.
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "pulse_http_requests_total" in response.text
    assert "pulse_http_request_duration_seconds" in response.text
