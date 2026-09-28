import asyncio
import logging
import random
import time
import uuid

from app.db import async_session
from app.models.job import Job, JobStatus
from app.queue import arq_redis_settings

logger = logging.getLogger("pulse.worker")


async def process_job(ctx: dict, job_id: str) -> None:
    async with async_session() as session:
        job = await session.get(Job, uuid.UUID(job_id))
        if job is None:
            logger.warning("job not found", extra={"job_id": job_id})
            return

        job.status = JobStatus.RUNNING
        await session.commit()

        duration = (job.payload or {}).get("duration_seconds")
        if duration is None:
            duration = random.uniform(0.5, 3.0)

        try:
            job.result = await _do_work(duration)
            job.status = JobStatus.DONE
        except Exception:
            logger.exception("job failed", extra={"job_id": job_id})
            job.status = JobStatus.FAILED
            job.result = {"error": "job failed"}

        await session.commit()


async def _do_work(duration_seconds: float) -> dict:
    start = time.perf_counter()
    # A mix of I/O wait and CPU work, closer to a real task than a bare sleep.
    await asyncio.sleep(duration_seconds)
    checksum = sum(i * i for i in range(200_000))
    return {"duration_seconds": round(time.perf_counter() - start, 3), "checksum": checksum}


class WorkerSettings:
    functions = [process_job]
    redis_settings = arq_redis_settings
