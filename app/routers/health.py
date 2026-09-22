from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: process is up and able to serve requests."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """Readiness probe: process can serve traffic right now.

    No external dependencies exist yet, so this always succeeds. Once
    Postgres/Redis are wired in, this should check those connections and
    return 503 when they're unreachable.
    """
    return {"status": "ready"}
