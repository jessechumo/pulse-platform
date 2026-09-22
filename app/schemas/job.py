import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus


class JobCreate(BaseModel):
    # Lets a caller (or a Locust script later) shape how long the synthetic
    # work takes; the worker picks a random duration when omitted.
    duration_seconds: float | None = Field(default=None, ge=0, le=30)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    result: dict | None
    created_at: datetime
    updated_at: datetime
