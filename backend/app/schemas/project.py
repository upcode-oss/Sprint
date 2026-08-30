from datetime import date, datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APIModel, TimestampedResponse, UUIDString
from app.schemas.identity import UserBrief

ProjectStatus = Literal["planned", "active", "on_hold", "completed", "archived"]
TaskType = Literal["task", "story", "bug", "epic"]
TaskPriority = Literal["lowest", "low", "medium", "high", "highest"]
SprintStatus = Literal["planned", "active", "completed", "cancelled"]


class TeamCreate(APIModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    member_ids: list[UUIDString] = Field(default_factory=list)


class TeamUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=5000)


class TeamBrief(APIModel):
    id: str
    name: str


class TeamResponse(TimestampedResponse):
    name: str
    description: str | None
    members: list[UserBrief]


class ProjectCreate(APIModel):
    name: str = Field(min_length=2, max_length=200)
    key: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z][A-Za-z0-9]*$")
    description: str | None = Field(default=None, max_length=10000)
    status: ProjectStatus = "active"
    start_date: date | None = None
    end_date: date | None = None
    team_ids: list[UUIDString] = Field(default_factory=list)
    done_task_retention_days: int = Field(default=2, ge=0, le=3650)

    @field_validator("key")
    @classmethod
    def uppercase_key(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def dates_in_order(self) -> "ProjectCreate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("End date cannot precede start date")
        return self


class ProjectUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    done_task_retention_days: int | None = Field(default=None, ge=0, le=3650)


class ProjectResponse(TimestampedResponse):
    name: str
    key: str
    description: str | None
    status: str
    start_date: date | None
    end_date: date | None
    done_task_retention_days: int
    teams: list[TeamBrief]


class KanbanColumnResponse(TimestampedResponse):
    project_id: str
    name: str
    key: str
    position: int
    is_done: bool


class KanbanColumnCreate(APIModel):
    name: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    position: int = Field(ge=0, le=100)
    is_done: bool = False


class TaskCreate(APIModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=50000)
    type: TaskType = "task"
    priority: TaskPriority = "medium"
    assignee_id: UUIDString | None = None
    sprint_id: UUIDString | None = None
    due_date: datetime | None = None
    tracked_seconds: int = Field(default=0, ge=0, le=315_360_000)


class TaskUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=50000)
    type: TaskType | None = None
    priority: TaskPriority | None = None
    assignee_id: UUIDString | None = None
    sprint_id: UUIDString | None = None
    due_date: datetime | None = None
    tracked_seconds: int | None = Field(default=None, ge=0, le=315_360_000)


class TaskMove(APIModel):
    column_id: UUIDString
    before_task_id: UUIDString | None = None
    after_task_id: UUIDString | None = None


class TaskResponse(TimestampedResponse):
    project_id: str
    number: int
    reference: str
    title: str
    description: str | None
    status: str
    type: str
    priority: str
    assignee: UserBrief | None
    reporter: UserBrief
    sprint_id: str | None
    kanban_column_id: str | None
    parent_task_id: str | None
    position: float
    due_date: datetime | None
    tracked_seconds: int
    completed_at: datetime | None


class TaskCommentCreate(APIModel):
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        body = value.strip()
        if not body:
            raise ValueError("Comment must not be empty")
        return body


class TaskCommentResponse(TimestampedResponse):
    task_id: str
    body: str
    author: UserBrief


class TaskActivityChange(APIModel):
    before: str | int | float | bool | None = None
    after: str | int | float | bool | None = None


class TaskActivityResponse(TimestampedResponse):
    project_id: str
    task_id: str
    task_reference: str
    task_title: str
    actor: UserBrief | None
    action: str
    changes: dict[str, TaskActivityChange]


class BoardResponse(APIModel):
    columns: list[KanbanColumnResponse]
    tasks: list[TaskResponse]


class SprintCreate(APIModel):
    name: str = Field(min_length=1, max_length=150)
    goal: str | None = Field(default=None, max_length=10000)
    start_date: date | None = None
    end_date: date | None = None


class SprintUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    goal: str | None = Field(default=None, max_length=10000)
    start_date: date | None = None
    end_date: date | None = None


class SprintResponse(TimestampedResponse):
    project_id: str
    name: str
    goal: str | None
    start_date: date | None
    end_date: date | None
    status: str
    tasks: list[TaskResponse]


class SprintCompleteRequest(APIModel):
    incomplete_action: Literal["backlog", "sprint"]
    target_sprint_id: UUIDString | None = None

    @model_validator(mode="after")
    def target_required(self) -> "SprintCompleteRequest":
        if self.incomplete_action == "sprint" and not self.target_sprint_id:
            raise ValueError("A target sprint is required")
        return self
