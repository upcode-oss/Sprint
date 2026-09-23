"""Add task time tracking and done-card retention.

Revision ID: 20260830_0007
Revises: 20260823_0006
Create Date: 2026-08-30
"""

import sqlalchemy as sa

from alembic import op

revision = "20260830_0007"
down_revision = "20260823_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()
    if "projects" in tables:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "done_task_retention_days" not in project_columns:
            with op.batch_alter_table("projects") as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "done_task_retention_days",
                        sa.Integer(),
                        nullable=False,
                        server_default="2",
                    )
                )
    if "tasks" not in tables:
        return
    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    with op.batch_alter_table("tasks") as batch_op:
        if "tracked_minutes" not in task_columns:
            batch_op.add_column(
                sa.Column("tracked_minutes", sa.Integer(), nullable=False, server_default="0")
            )
        if "completed_at" not in task_columns:
            batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True)))
            batch_op.create_index("ix_tasks_completed_at", ["completed_at"])
    if "completed_at" not in task_columns and "kanban_columns" in tables:
        op.execute(
            sa.text(
                "UPDATE tasks SET completed_at = updated_at "
                "WHERE kanban_column_id IN "
                "(SELECT id FROM kanban_columns WHERE is_done = true)"
            )
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tasks" in inspector.get_table_names():
        task_columns = {column["name"] for column in inspector.get_columns("tasks")}
        with op.batch_alter_table("tasks") as batch_op:
            if "completed_at" in task_columns:
                batch_op.drop_index("ix_tasks_completed_at")
                batch_op.drop_column("completed_at")
            if "tracked_minutes" in task_columns:
                batch_op.drop_column("tracked_minutes")
    inspector = sa.inspect(op.get_bind())
    if "projects" in inspector.get_table_names():
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "done_task_retention_days" in project_columns:
            with op.batch_alter_table("projects") as batch_op:
                batch_op.drop_column("done_task_retention_days")
