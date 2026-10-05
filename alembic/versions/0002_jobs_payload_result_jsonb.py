"""convert jobs.payload and jobs.result to jsonb

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "jobs",
        "payload",
        type_=postgresql.JSONB(),
        postgresql_using="payload::jsonb",
    )
    op.alter_column(
        "jobs",
        "result",
        type_=postgresql.JSONB(),
        postgresql_using="result::jsonb",
    )


def downgrade() -> None:
    op.alter_column(
        "jobs",
        "payload",
        type_=sa.JSON(),
        postgresql_using="payload::json",
    )
    op.alter_column(
        "jobs",
        "result",
        type_=sa.JSON(),
        postgresql_using="result::json",
    )
