"""Store tracked task time with second precision.

Revision ID: 20260830_0008
Revises: 20260830_0007
Create Date: 2026-08-30
"""

import sqlalchemy as sa

from alembic import op

revision = "20260830_0008"
down_revision = "20260830_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "tracked_seconds" not in columns:
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.add_column(
                sa.Column("tracked_seconds", sa.Integer(), nullable=False, server_default="0")
            )
    if "tracked_minutes" in columns:
        op.execute(
            sa.text("UPDATE tasks SET tracked_seconds = tracked_minutes * 60")
        )
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.drop_column("tracked_minutes")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "tracked_minutes" not in columns:
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.add_column(
                sa.Column("tracked_minutes", sa.Integer(), nullable=False, server_default="0")
            )
    if "tracked_seconds" in columns:
        op.execute(sa.text("UPDATE tasks SET tracked_minutes = tracked_seconds / 60"))
        with op.batch_alter_table("tasks") as batch_op:
            batch_op.drop_column("tracked_seconds")
