import uuid

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.job import Job, JobStatus
from app.queue import require_arq_pool
from app.schemas.job import JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    body: JobCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(require_arq_pool),
) -> Job:
    job = Job(payload={"duration_seconds": body.duration_seconds})
    session.add(job)
    await session.commit()
    await session.refresh(job)

    try:
        await arq_pool.enqueue_job("process_job", str(job.id))
    except Exception:
        # The row is already committed. require_arq_pool only guarantees
        # Redis was reachable when the dependency resolved -- it can still
        # go down between then and this call. Without this, the job would
        # sit at "queued" forever (no worker will ever see it) while the
        # caller gets an unhandled 500 instead of a clean signal to retry.
        job.status = JobStatus.FAILED
        job.result = {"error": "failed to enqueue"}
        await session.commit()
        raise HTTPException(status_code=503, detail="job queue unavailable") from None

    response.headers["Location"] = f"/jobs/{job.id}"
    return job


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
