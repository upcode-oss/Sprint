from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.schemas.project import TaskCreate, TaskMove, TaskUpdate
from app.services.dashboard_service import project_overview
from app.services.task_service import board, create_task, move_task, update_task


def test_tracked_time_is_editable_and_summed_for_project(
    db: Session, workspace: dict[str, object]
) -> None:
    project = workspace["project"]
    member = workspace["member"]
    first = create_task(
        db, project, member.id, TaskCreate(title="First", tracked_minutes=90)
    )
    create_task(db, project, member.id, TaskCreate(title="Second", tracked_minutes=30))

    updated = update_task(db, first, TaskUpdate(tracked_minutes=120), member.id)
    overview = project_overview(db, project.id)

    assert updated.tracked_minutes == 120
    assert overview["total_tracked_minutes"] == 150


def test_done_tasks_are_hidden_after_project_retention_period(
    db: Session, workspace: dict[str, object]
) -> None:
    project = workspace["project"]
    member = workspace["member"]
    task = create_task(db, project, member.id, TaskCreate(title="Completed work"))
    done_column = next(column for column in project.columns if column.is_done)

    moved = move_task(db, task, TaskMove(column_id=done_column.id), member.id)
    assert project.done_task_retention_days == 2
    assert moved.completed_at is not None
    assert moved.id in {item.id for item in board(db, project.id)[1]}

    moved.completed_at = datetime.now(UTC) - timedelta(days=3)
    db.commit()
    assert moved.id not in {item.id for item in board(db, project.id)[1]}

    project.done_task_retention_days = 4
    db.commit()
    assert moved.id in {item.id for item in board(db, project.id)[1]}

    moved.completed_at = datetime.now(UTC) - timedelta(days=5)
    db.commit()
    assert moved.id not in {item.id for item in board(db, project.id)[1]}

    backlog_column = next(column for column in project.columns if not column.is_done)
    reopened = move_task(db, moved, TaskMove(column_id=backlog_column.id), member.id)
    assert reopened.completed_at is None
    assert reopened.id in {item.id for item in board(db, project.id)[1]}
