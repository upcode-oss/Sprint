"""Add the organization timezone, defaulting existing installations to UTC."""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0009"
down_revision = "20260830_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.add_column(
            sa.Column("timezone", sa.String(100), nullable=False, server_default="UTC")
        )


def downgrade() -> None:
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_column("timezone")
