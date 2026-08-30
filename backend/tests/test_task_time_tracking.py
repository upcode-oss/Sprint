from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.db.migrations import upgrade_database
from app.schemas.project import TaskCreate, TaskMove, TaskUpdate
from app.services.dashboard_service import project_overview
from app.services.task_service import board, create_task, move_task, update_task


def test_time_tracking_migration_converts_minutes_to_seconds(tmp_path: Path) -> None:
    database = tmp_path / "tracked-time.db"
    url = f"sqlite:///{database}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE tasks "
                "(id VARCHAR(36) PRIMARY KEY, tracked_minutes INTEGER NOT NULL)"
            )
        )
        connection.execute(text("INSERT INTO tasks VALUES ('task-1', 91)"))
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('20260830_0007')")
        )
    engine.dispose()

    upgrade_database(url)

    engine = create_engine(url)
    with engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("tasks")}
        assert "tracked_minutes" not in columns
        assert "tracked_seconds" in columns
        assert connection.scalar(text("SELECT tracked_seconds FROM tasks")) == 5_460
    engine.dispose()


def test_tracked_time_is_editable_and_summed_for_project(
    db: Session, workspace: dict[str, object]
) -> None:
    project = workspace["project"]
    member = workspace["member"]
    first = create_task(
        db, project, member.id, TaskCreate(title="First", tracked_seconds=5_401)
    )
    second = create_task(
        db, project, member.id, TaskCreate(title="Second", tracked_seconds=1_801)
    )

    updated = update_task(db, first, TaskUpdate(tracked_seconds=7_201), member.id)
    overview = project_overview(db, project.id)

    assert updated.tracked_seconds == 7_201
    assert overview["total_tracked_seconds"] == 9_002
    assert [task.id for task in overview["tracked_tasks"]] == [updated.id, second.id]


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
