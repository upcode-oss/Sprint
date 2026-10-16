"""Add the reciprocal Forge/Sprint instance connection."""

import sqlalchemy as sa

from alembic import op

revision = "20261016_0010"
down_revision = "20260918_0009"


def upgrade():
    # Sprint's original migration also creates the current model metadata on fresh installs.
    if "instance_connections" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "instance_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("connection_id", sa.String(36), nullable=False, unique=True),
        sa.Column("peer_url", sa.String(500), nullable=False),
        sa.Column("peer_name", sa.String(200), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("instance_connections")
