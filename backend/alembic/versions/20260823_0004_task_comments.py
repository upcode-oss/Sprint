"""Add task comments.

Revision ID: 20260823_0004
Revises: 20260817_0003
Create Date: 2026-08-23
"""

import sqlalchemy as sa

from alembic import op

revision = "20260823_0004"
down_revision = "20260817_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "task_comments" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "task_comments",
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("author_id", sa.String(36), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_comments_author_id", "task_comments", ["author_id"])
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])


def downgrade() -> None:
    if "task_comments" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("task_comments")
