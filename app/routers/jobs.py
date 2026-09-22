import uuid

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.job import Job
from app.queue import get_arq_pool
from app.schemas.job import JobCreate, JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    body: JobCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> Job:
    job = Job(payload={"duration_seconds": body.duration_seconds})
    session.add(job)
    await session.commit()
    await session.refresh(job)

    await arq_pool.enqueue_job("process_job", str(job.id))

    response.headers["Location"] = f"/jobs/{job.id}"
    return job


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
