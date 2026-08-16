from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, Field, model_validator

from app.schemas.common import APIModel, TimestampedResponse, UUIDString
from app.schemas.identity import UserBrief

ScopeType = Literal["personal", "organization", "team", "project"]


class DocumentCreate(APIModel):
    title: str = Field(min_length=1, max_length=250)
    slug: str = Field(min_length=1, max_length=250, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    markdown_content: str = Field(default="", max_length=500000)
    parent_id: UUIDString | None = None


class DocumentUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    slug: str | None = Field(
        default=None, min_length=1, max_length=250, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    markdown_content: str | None = Field(default=None, max_length=500000)
    parent_id: UUIDString | None = None


class DocumentResponse(TimestampedResponse):
    project_id: str
    title: str
    slug: str
    markdown_content: str
    parent_id: str | None
    created_by: UserBrief
    updated_by: UserBrief


class MeetingCreate(APIModel):
    title: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    start: datetime
    end: datetime
    location: str | None = Field(default=None, max_length=300)
    meeting_url: AnyHttpUrl | None = None
    scope_type: ScopeType
    scope_id: UUIDString | None = None
    participant_ids: list[UUIDString] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scope_and_time(self) -> "MeetingCreate":
        if self.end <= self.start:
            raise ValueError("Meeting end must be after start")
        if self.scope_type in {"team", "project"} and not self.scope_id:
            raise ValueError("Scope ID is required for team and project meetings")
        return self


class MeetingUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    start: datetime | None = None
    end: datetime | None = None
    location: str | None = Field(default=None, max_length=300)
    meeting_url: AnyHttpUrl | None = None
    participant_ids: list[UUIDString] | None = None


class MeetingParticipantResponse(APIModel):
    user: UserBrief
    response: str


class MeetingResponse(TimestampedResponse):
    title: str
    description: str | None
    start: datetime
    end: datetime
    location: str | None
    meeting_url: str | None
    creator: UserBrief
    scope_type: str
    scope_id: str | None
    participants: list[MeetingParticipantResponse]


class CalendarEventCreate(APIModel):
    title: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    start: datetime
    end: datetime
    all_day: bool = False
    location: str | None = Field(default=None, max_length=300)
    scope_type: ScopeType
    scope_id: UUIDString | None = None

    @model_validator(mode="after")
    def validate_scope_and_time(self) -> "CalendarEventCreate":
        if self.end <= self.start:
            raise ValueError("Event end must be after start")
        if self.scope_type in {"team", "project"} and not self.scope_id:
            raise ValueError("Scope ID is required for team and project events")
        return self


class CalendarEventUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=20000)
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool | None = None
    location: str | None = Field(default=None, max_length=300)


class CalendarEventResponse(TimestampedResponse):
    title: str
    description: str | None
    start: datetime
    end: datetime
    all_day: bool
    location: str | None
    scope_type: str
    scope_id: str | None
    source: str = "event"


class CalendarMeetingResponse(APIModel):
    id: str
    title: str
    description: str | None
    start: datetime
    end: datetime
    all_day: bool = False
    location: str | None
    scope_type: str
    scope_id: str | None
    creator: UserBrief
    participants: list[MeetingParticipantResponse]
    source: str = "meeting"


class CalendarSourceResponse(APIModel):
    key: str
    label: str
    type: str


class CalendarFeedResponse(APIModel):
    items: list[CalendarEventResponse | CalendarMeetingResponse]
    available_sources: list[CalendarSourceResponse]
