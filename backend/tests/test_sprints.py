from sqlalchemy.orm import Session

from app.schemas.project import SprintCompleteRequest, SprintCreate, TaskCreate
from app.services.sprint_service import complete_sprint, create_sprint, get_sprint, start_sprint
from app.services.task_service import create_task


def test_only_one_active_sprint_and_incomplete_work_returns_to_backlog(
    db: Session, workspace: dict[str, object]
) -> None:
    project = workspace["project"]
    member = workspace["member"]
    first = create_sprint(db, project.id, SprintCreate(name="Sprint 1"))
    second = create_sprint(db, project.id, SprintCreate(name="Sprint 2"))
    active = start_sprint(db, first)
    task = create_task(
        db,
        project,
        member.id,
        TaskCreate(title="Incomplete story", type="story", sprint_id=active.id),
    )

    from app.core.errors import APIError

    try:
        start_sprint(db, second)
        raised = False
    except APIError as error:
        raised = error.code == "active_sprint_exists"
    assert raised

    completed = complete_sprint(
        db,
        get_sprint(db, project.id, active.id),
        SprintCompleteRequest(incomplete_action="backlog"),
    )
    db.refresh(task)
    assert completed.status == "completed"
    assert task.sprint_id is None
