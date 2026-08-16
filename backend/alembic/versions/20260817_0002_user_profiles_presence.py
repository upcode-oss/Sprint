"""Add user profiles, contact information and presence.

Revision ID: 20260817_0002
Revises: 20260816_0001
Create Date: 2026-08-17
"""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "20260817_0002"
down_revision = "20260816_0001"
branch_labels = None
depends_on = None


def _create_profile_table(existing: set[str]) -> None:
    if "user_profiles" in existing:
        return
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("job_title", sa.String(150), nullable=True),
        sa.Column("department", sa.String(150), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("locale", sa.String(20), nullable=True),
        sa.Column("avatar_key", sa.String(255), nullable=True),
        sa.Column("avatar_mime_type", sa.String(50), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])


def _create_contact_table(existing: set[str]) -> None:
    if "user_contacts" in existing:
        return
    op.create_table(
        "user_contacts",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("value", sa.String(320), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("primary_slot", sa.String(10), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", "value", name="uq_user_contacts_user_type_value"),
        sa.UniqueConstraint(
            "user_id", "type", "primary_slot", name="uq_user_contacts_user_type_primary"
        ),
    )
    op.create_index("ix_user_contacts_user_id", "user_contacts", ["user_id"])
    op.create_index("ix_user_contacts_type", "user_contacts", ["type"])


def _create_presence_table(existing: set[str]) -> None:
    if "user_presences" in existing:
        return
    op.create_table(
        "user_presences",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("manual_status", sa.String(30), nullable=True),
        sa.Column("status_message", sa.String(280), nullable=True),
        sa.Column("status_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_user_presences_last_seen_at", "user_presences", ["last_seen_at"])


def _backfill_users() -> None:
    connection = op.get_bind()
    now = datetime.now(UTC)
    user_ids = list(connection.execute(sa.text("SELECT id FROM users")).scalars())
    profile_ids = set(connection.execute(sa.text("SELECT user_id FROM user_profiles")).scalars())
    presence_ids = set(connection.execute(sa.text("SELECT user_id FROM user_presences")).scalars())
    profile_table = sa.table(
        "user_profiles",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("timezone", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    presence_table = sa.table(
        "user_presences",
        sa.column("user_id", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    profiles = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "timezone": "UTC",
            "created_at": now,
            "updated_at": now,
        }
        for user_id in user_ids
        if user_id not in profile_ids
    ]
    presences = [
        {"user_id": user_id, "updated_at": now}
        for user_id in user_ids
        if user_id not in presence_ids
    ]
    if profiles:
        op.bulk_insert(profile_table, profiles)
    if presences:
        op.bulk_insert(presence_table, presences)


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    _create_profile_table(existing)
    _create_contact_table(existing)
    _create_presence_table(existing)
    _backfill_users()


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table_name in ("user_contacts", "user_presences", "user_profiles"):
        if table_name in existing:
            op.drop_table(table_name)
