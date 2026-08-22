from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associations import project_teams, team_members


class Team(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_teams_org_name"),)

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    members: Mapped[list["User"]] = relationship(  # noqa: F821
        secondary=team_members, back_populates="teams", lazy="selectin"
    )
    projects: Mapped[list["Project"]] = relationship(
        secondary=project_teams, back_populates="teams"
    )


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_projects_org_key"),
        UniqueConstraint("organization_id", "name", name="uq_projects_org_name"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    task_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    teams: Mapped[list[Team]] = relationship(
        secondary=project_teams, back_populates="projects", lazy="selectin"
    )
    columns: Mapped[list["KanbanColumn"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="KanbanColumn.position"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    sprints: Mapped[list["Sprint"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    task_activities: Mapped[list["TaskActivity"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class KanbanColumn(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kanban_columns"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_kanban_columns_project_key"),
        UniqueConstraint("project_id", "position", name="uq_kanban_columns_project_position"),
    )

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_done: Mapped[bool] = mapped_column(default=False, nullable=False)

    project: Mapped[Project] = relationship(back_populates="columns")
    tasks: Mapped[list["Task"]] = relationship(back_populates="column")


class Sprint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sprints"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_sprints_project_name"),)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="planned", nullable=False, index=True)

    project: Mapped[Project] = relationship(back_populates="sprints")
    tasks: Mapped[list["Task"]] = relationship(back_populates="sprint")


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("project_id", "number", name="uq_tasks_project_number"),)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="backlog", nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), default="task", nullable=False)
    priority: Mapped[str] = mapped_column(String(30), default="medium", nullable=False)
    assignee_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reporter_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    sprint_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sprints.id", ondelete="SET NULL"), index=True
    )
    kanban_column_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("kanban_columns.id", ondelete="SET NULL"), index=True
    )
    position: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), default=Decimal("1000"), nullable=False
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )

    project: Mapped[Project] = relationship(back_populates="tasks")
    sprint: Mapped[Sprint | None] = relationship(back_populates="tasks")
    column: Mapped[KanbanColumn | None] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])  # noqa: F821
    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])  # noqa: F821
    parent: Mapped["Task | None"] = relationship(
        remote_side="Task.id", back_populates="subtasks"
    )
    subtasks: Mapped[list["Task"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    comments: Mapped[list["TaskComment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskComment.created_at",
    )

    @property
    def reference(self) -> str:
        return f"{self.project.key}-{self.number}"


class TaskComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_comments"

    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped[Task] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship()  # noqa: F821


class TaskActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_activities"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[str] = mapped_column(String(36), index=True)
    task_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    task_title: Mapped[str] = mapped_column(String(300), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    changes: Mapped[dict[str, dict[str, object]]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="task_activities")
    actor: Mapped["User | None"] = relationship()  # noqa: F821
