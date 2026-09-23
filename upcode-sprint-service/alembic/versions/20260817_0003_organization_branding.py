"""Add persistent organization branding.

Revision ID: 20260817_0003
Revises: 20260817_0002
Create Date: 2026-08-17
"""

import sqlalchemy as sa

from alembic import op

revision = "20260817_0003"
down_revision = "20260817_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organizations" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("organizations")}
    if "logo_key" not in existing:
        op.add_column("organizations", sa.Column("logo_key", sa.String(255), nullable=True))
    if "logo_mime_type" not in existing:
        op.add_column(
            "organizations", sa.Column("logo_mime_type", sa.String(50), nullable=True)
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organizations" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("organizations")}
    if "logo_mime_type" in existing:
        op.drop_column("organizations", "logo_mime_type")
    if "logo_key" in existing:
        op.drop_column("organizations", "logo_key")
