from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.models.associations import role_permissions, user_roles


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "username", name="uq_users_org_username"),
        UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(default=1, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="users")
    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles, back_populates="users", lazy="selectin"
    )
    teams: Mapped[list["Team"]] = relationship(  # noqa: F821
        secondary="team_members", back_populates="members"
    )
    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin", uselist=False
    )
    contacts: Mapped[list["UserContact"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    presence: Mapped["UserPresence | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin", uselist=False
    )

    @property
    def display_name(self) -> str:
        preferred = (
            self.profile.display_name.strip() if self.profile and self.profile.display_name else ""
        )
        return preferred or f"{self.first_name} {self.last_name}".strip()

    @property
    def avatar_url(self) -> str | None:
        if not self.profile or not self.profile.avatar_key:
            return None
        version = int(self.profile.updated_at.timestamp())
        return f"/api/v1/users/{self.id}/avatar?v={version}"

    @property
    def job_title(self) -> str | None:
        return self.profile.job_title if self.profile else None

    @property
    def department(self) -> str | None:
        return self.profile.department if self.profile else None

    @property
    def bio(self) -> str | None:
        return self.profile.bio if self.profile else None

    @property
    def timezone(self) -> str:
        return self.profile.timezone if self.profile else "UTC"

    @property
    def locale(self) -> str | None:
        return self.profile.locale if self.profile else None

    @property
    def presence_summary(self) -> dict[str, object]:
        from app.services.presence_service import presence_summary

        return presence_summary(self.presence)


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(150))
    department: Mapped[str | None] = mapped_column(String(150))
    bio: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    locale: Mapped[str | None] = mapped_column(String(20))
    avatar_key: Mapped[str | None] = mapped_column(String(255))
    avatar_mime_type: Mapped[str | None] = mapped_column(String(50))

    user: Mapped[User] = relationship(back_populates="profile")


class UserContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_contacts"
    __table_args__ = (
        UniqueConstraint("user_id", "type", "value", name="uq_user_contacts_user_type_value"),
        UniqueConstraint(
            "user_id", "type", "primary_slot", name="uq_user_contacts_user_type_primary"
        ),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(String(320), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    primary_slot: Mapped[str | None] = mapped_column(String(10))
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)

    user: Mapped[User] = relationship(back_populates="contacts")


class UserPresence(Base):
    __tablename__ = "user_presences"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    manual_status: Mapped[str | None] = mapped_column(String(30))
    status_message: Mapped[str | None] = mapped_column(String(280))
    status_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="presence")


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_roles_org_name"),)

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions, back_populates="permissions"
    )


class SMTPConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "smtp_configurations"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    password_encrypted: Mapped[str | None] = mapped_column(Text)
    encryption: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    from_address: Mapped[str] = mapped_column(String(320), nullable=False)
    from_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
