"""Add task subtickets.

Revision ID: 20260823_0006
Revises: 20260823_0005
Create Date: 2026-08-23
"""

import sqlalchemy as sa

from alembic import op

revision = "20260823_0006"
down_revision = "20260823_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tasks" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("tasks")}
    if "parent_task_id" in existing:
        return
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("parent_task_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key(
            "fk_tasks_parent_task_id_tasks",
            "tasks",
            ["parent_task_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_tasks_parent_task_id", ["parent_task_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tasks" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("tasks")}
    if "parent_task_id" not in existing:
        return
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_parent_task_id")
        batch_op.drop_constraint("fk_tasks_parent_task_id_tasks", type_="foreignkey")
        batch_op.drop_column("parent_task_id")
