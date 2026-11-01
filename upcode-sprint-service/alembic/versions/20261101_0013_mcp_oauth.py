"""Persist OAuth grants for authenticated MCP clients such as ChatGPT."""

import sqlalchemy as sa

from alembic import op

revision = "20261101_0013"
down_revision = "20261031_0012"


def upgrade():
    existing = sa.inspect(op.get_bind()).get_table_names()
    if "mcp_oauth_clients" not in existing:
        op.create_table(
            "mcp_oauth_clients",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("metadata_encrypted", sa.Text(), nullable=False),
        )
    for table in ("mcp_oauth_requests", "mcp_oauth_codes", "mcp_oauth_tokens"):
        if table in existing:
            continue
        columns = [
            sa.Column("digest", sa.String(64), primary_key=True),
            sa.Column(
                "client_id",
                sa.String(128),
                sa.ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        ]
        if table == "mcp_oauth_requests":
            columns.extend(
                [
                    sa.Column("data", sa.Text(), nullable=False),
                    sa.Column(
                        "user_id",
                        sa.String(36),
                        sa.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=True,
                    ),
                    sa.Column("csrf_digest", sa.String(64), nullable=True),
                ]
            )
        else:
            columns.append(
                sa.Column(
                    "key_id",
                    sa.String(36),
                    sa.ForeignKey("mcp_keys.id", ondelete="CASCADE"),
                    nullable=False,
                )
            )
            if table == "mcp_oauth_codes":
                columns.append(sa.Column("data", sa.Text(), nullable=False))
            else:
                columns.extend(
                    [
                        sa.Column("kind", sa.String(8), nullable=False),
                        sa.Column("resource", sa.Text(), nullable=False),
                    ]
                )
        op.create_table(table, *columns)
        if table == "mcp_oauth_tokens":
            op.create_index("ix_mcp_oauth_tokens_key_id", table, ["key_id"])


def downgrade():
    for table in ("mcp_oauth_tokens", "mcp_oauth_codes", "mcp_oauth_requests", "mcp_oauth_clients"):
        op.drop_table(table)
