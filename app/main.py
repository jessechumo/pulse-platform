import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.logging import configure_logging
from app.metrics import MetricsMiddleware, metrics_response
from app.routers import health

configure_logging()
logger = logging.getLogger("pulse.app")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "service starting",
        extra={"environment": settings.environment, "version": settings.version},
    )
    yield
    logger.info("service stopping")


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.add_middleware(MetricsMiddleware)
app.include_router(health.router)


@app.get("/metrics")
def metrics():
    return metrics_response()
