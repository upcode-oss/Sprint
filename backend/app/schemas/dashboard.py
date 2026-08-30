from app.schemas.collaboration import CalendarEventResponse, DocumentResponse, MeetingResponse
from app.schemas.common import APIModel
from app.schemas.project import ProjectResponse, SprintResponse, TaskResponse, TeamResponse


class PersonalDashboardResponse(APIModel):
    projects: list[ProjectResponse]
    teams: list[TeamResponse]
    tasks: list[TaskResponse]
    active_sprints: list[SprintResponse]
    upcoming_meetings: list[MeetingResponse]
    upcoming_events: list[CalendarEventResponse]


class ProjectOverviewResponse(APIModel):
    tasks: list[TaskResponse]
    active_sprint: SprintResponse | None
    upcoming_meetings: list[MeetingResponse]
    recent_documents: list[DocumentResponse]
    member_count: int
    total_tracked_seconds: int
    tracked_tasks: list[TaskResponse]
