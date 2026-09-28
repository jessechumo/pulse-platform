import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.worker import process_job

client = TestClient(app)


@pytest.mark.integration
def test_job_lifecycle_queued_to_done():
    response = client.post("/jobs", json={"duration_seconds": 0.01})
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert response.json()["status"] == "queued"

    asyncio.run(process_job({}, job_id))

    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert "checksum" in body["result"]


@pytest.mark.integration
def test_get_job_returns_404_for_unknown_id():
    response = client.get(f"/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
