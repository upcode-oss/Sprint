from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("project_id", "slug", name="uq_documents_project_slug"),)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL")
    )
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT")
    )

    project: Mapped["Project"] = relationship()  # noqa: F821
    created_by: Mapped["User"] = relationship(foreign_keys=[created_by_id])  # noqa: F821
    updated_by: Mapped["User"] = relationship(foreign_keys=[updated_by_id])  # noqa: F821
    parent: Mapped["Document | None"] = relationship(remote_side="Document.id")


class Meeting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meetings"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(300))
    meeting_url: Mapped[str | None] = mapped_column(String(1000))
    creator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    scope_id: Mapped[str | None] = mapped_column(String(36), index=True)

    creator: Mapped["User"] = relationship()  # noqa: F821
    participants: Mapped[list["MeetingParticipant"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", lazy="selectin"
    )


class MeetingParticipant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "meeting_participants"
    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participants_meeting_user"),
    )

    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    response: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)

    meeting: Mapped[Meeting] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()  # noqa: F821


class CalendarEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "calendar_events"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    all_day: Mapped[bool] = mapped_column(default=False, nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"))
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    scope_id: Mapped[str | None] = mapped_column(String(36), index=True)
    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])  # noqa: F821
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id])  # noqa: F821
