import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import async_session
from app.main import app
from app.models.job import Job, JobStatus
from app.queue import require_arq_pool
from app.worker import process_job

client = TestClient(app)


class _FailingArqPool:
    async def enqueue_job(self, *args, **kwargs):
        raise ConnectionError("simulated redis failure between dependency check and enqueue")


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


@pytest.mark.integration
def test_create_job_returns_503_and_marks_job_failed_when_enqueue_fails():
    app.dependency_overrides[require_arq_pool] = lambda: _FailingArqPool()
    try:
        response = client.post("/jobs", json={})
    finally:
        app.dependency_overrides.pop(require_arq_pool, None)

    assert response.status_code == 503

    # The 503 body has no job id (HTTPException bypasses response_model), so
    # find the row by the distinctive result payload this failure path
    # writes -- the point of this test is that the row isn't left stuck at
    # "queued" forever with no worker ever going to see it.
    async def _fetch_latest_failed_job() -> Job:
        async with async_session() as session:
            result = await session.execute(
                select(Job)
                .where(Job.result == {"error": "failed to enqueue"})
                .order_by(Job.created_at.desc())
                .limit(1)
            )
            return result.scalar_one()

    job = asyncio.run(_fetch_latest_failed_job())
    assert job.status == JobStatus.FAILED
