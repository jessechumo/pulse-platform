from fastapi import APIRouter, Depends, Response

from app.db import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: process is up and able to serve requests."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    response: Response, database_ok: bool = Depends(check_database)
) -> dict[str, object]:
    """Readiness probe: process can serve traffic right now.

    Checks every external dependency the app actually needs to do its job.
    Kubernetes uses this (not /health) to decide whether to route traffic
    to a pod, so a dependency outage should pull the pod out of rotation
    without killing and restarting it.
    """
    checks = {"database": "ok" if database_ok else "unreachable"}
    all_ok = all(value == "ok" for value in checks.values())

    if not all_ok:
        response.status_code = 503

    return {"status": "ready" if all_ok else "not ready", "checks": checks}
