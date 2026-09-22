import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.config import get_settings

ACCESS_LOGGER_NAME = "pulse.access"


def configure_logging() -> None:
    settings = get_settings()

    formatter = JsonFormatter(
        "{asctime}{levelname}{name}{message}",
        style="{",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        timestamp=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)

    # Uvicorn ships its own handlers; replace them so every log line is JSON.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
