"""Initial portable schema.

Revision ID: 20260816_0001
Revises:
Create Date: 2026-08-16
"""

import app.models  # noqa: F401
from alembic import op
from app.db.base import Base

revision = "20260816_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
