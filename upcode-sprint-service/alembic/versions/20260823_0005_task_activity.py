"""Add project task activity logs.

Revision ID: 20260823_0005
Revises: 20260823_0004
Create Date: 2026-08-23
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision = "20260823_0005"
down_revision = "20260823_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "task_activities" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "task_activities",
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("task_reference", sa.String(50), nullable=False),
        sa.Column("task_title", sa.String(300), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_activities_action", "task_activities", ["action"])
    op.create_index("ix_task_activities_actor_id", "task_activities", ["actor_id"])
    op.create_index("ix_task_activities_project_id", "task_activities", ["project_id"])
    op.create_index("ix_task_activities_task_id", "task_activities", ["task_id"])
    connection = op.get_bind()
    source_tables = sa.inspect(connection).get_table_names()
    tasks = (
        list(
            connection.execute(
                sa.text(
                    "SELECT tasks.id, tasks.project_id, tasks.title, tasks.reporter_id, "
                    "tasks.created_at, tasks.updated_at, tasks.number, projects.key "
                    "FROM tasks JOIN projects ON projects.id = tasks.project_id"
                )
            ).mappings()
        )
        if "tasks" in source_tables and "projects" in source_tables
        else []
    )
    if tasks:
        activity_table = sa.table(
            "task_activities",
            sa.column("id", sa.String),
            sa.column("project_id", sa.String),
            sa.column("task_id", sa.String),
            sa.column("task_reference", sa.String),
            sa.column("task_title", sa.String),
            sa.column("actor_id", sa.String),
            sa.column("action", sa.String),
            sa.column("changes", sa.JSON),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        )
        op.bulk_insert(
            activity_table,
            [
                {
                    "id": str(uuid.uuid4()),
                    "project_id": task["project_id"],
                    "task_id": task["id"],
                    "task_reference": f"{task['key']}-{task['number']}",
                    "task_title": task["title"],
                    "actor_id": task["reporter_id"],
                    "action": "created",
                    "changes": {},
                    "created_at": task["created_at"],
                    "updated_at": task["updated_at"],
                }
                for task in tasks
            ],
        )


def downgrade() -> None:
    if "task_activities" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("task_activities")
