import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_mcp import base_client as base_client
from test_mcp import call, checked, create_key, rpc
from test_mcp import mcp_client as mcp_client
from test_mcp import projects as projects
from test_mcp_oauth import approve, exchange, start
from test_mcp_oauth import oauth_client as oauth_client

from app.models.project import TaskActivity


def credential(ctx, kind, scopes):
    client = ctx["alice"]
    if kind == "personal":
        return create_key(client, "AlicePassword123", scopes)["key"]
    registration, verifier, request_id = start(client)
    code = approve(client, "AlicePassword123", request_id, scopes=scopes)
    response = exchange(client, registration, verifier, code)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(params=["personal", "oauth"])
def kanban_access(projects, oauth_client, request):
    ctx = projects
    raw = credential(ctx, request.param, ["kanban.view", "kanban.manage"])
    return ctx, raw, request.param


def read_board(ctx, raw):
    result = call(ctx["admin"], raw, "get_kanban_board", {"project_id": ctx["own"]})
    assert result["status"] == 200, result
    return result["data"]


def move(ctx, raw, column_id, **extra):
    return call(
        ctx["admin"],
        raw,
        "move_task",
        {
            "project_id": ctx["own"],
            "task_id": ctx["own_task"],
            "payload": {"column_id": column_id, **extra},
        },
    )


def test_move_between_columns_complete_and_reopen_with_owner_activity(kanban_access):
    ctx, raw, _ = kanban_access
    board = read_board(ctx, raw)
    columns = board["columns"]
    assert [column["position"] for column in columns] == sorted(
        column["position"] for column in columns
    )
    assert all(column["project_id"] == ctx["own"] for column in columns)
    original = next(task for task in board["tasks"] if task["id"] == ctx["own_task"])
    target = next(
        column
        for column in columns
        if not column["is_done"] and column["id"] != original["kanban_column_id"]
    )
    done = next(column for column in columns if column["is_done"])
    tools = rpc(ctx["admin"], raw, "tools/list").json()["result"]["tools"]
    definitions = {tool["name"]: tool for tool in tools}
    assert definitions["get_kanban_board"]["annotations"]["readOnlyHint"] is True
    assert definitions["move_task"]["annotations"]["readOnlyHint"] is False

    for column in (target, done, target):
        result = move(ctx, raw, column["id"])
        assert result["status"] == 200, result
        task = result["data"]
        assert task["kanban_column_id"] == column["id"]
        assert task["status"] == column["key"]
        assert (task["completed_at"] is not None) == column["is_done"]
        for field in (
            "title",
            "description",
            "priority",
            "assignee",
            "reporter",
            "tracked_seconds",
        ):
            assert task[field] == original[field], field

    saved = ctx["admin"].get(f"/api/v1/projects/{ctx['own']}/tasks/{ctx['own_task']}").json()
    assert saved["kanban_column_id"] == target["id"]
    with Session(ctx["engine"]()) as db:
        history = list(
            db.scalars(
                select(TaskActivity)
                .where(
                    TaskActivity.task_id == ctx["own_task"],
                    TaskActivity.action == "moved",
                )
                .order_by(TaskActivity.created_at)
            )
        )
        assert len(history) == 3
        assert all(event.actor_id == ctx["alice_id"] for event in history)
        assert [event.changes["column"]["after"] for event in history] == [
            target["name"],
            done["name"],
            target["name"],
        ]


def test_reorder_uses_real_neighbors_in_the_target_column(kanban_access):
    ctx, raw, _ = kanban_access
    board = read_board(ctx, raw)
    column_id = next(
        task["kanban_column_id"] for task in board["tasks"] if task["id"] == ctx["own_task"]
    )
    second, third = [
        checked(
            ctx["admin"].post(
                f"/api/v1/projects/{ctx['own']}/tasks",
                json={"title": title},
            )
        )
        for title in ("Second ticket", "Third ticket")
    ]

    result = move(ctx, raw, column_id, after_task_id=third["id"])
    assert result["status"] == 200, result
    ordered = [
        task["id"]
        for task in read_board(ctx, raw)["tasks"]
        if task["kanban_column_id"] == column_id
    ]
    assert ordered == [second["id"], third["id"], ctx["own_task"]]

    result = move(ctx, raw, column_id, before_task_id=third["id"])
    assert result["status"] == 200, result
    ordered = [
        task["id"]
        for task in read_board(ctx, raw)["tasks"]
        if task["kanban_column_id"] == column_id
    ]
    assert ordered == [second["id"], ctx["own_task"], third["id"]]


def test_project_task_column_and_neighbor_boundaries_are_enforced(kanban_access):
    ctx, raw, _ = kanban_access
    board = read_board(ctx, raw)
    target = board["columns"][0]["id"]
    foreign_board = ctx["admin"].get(f"/api/v1/projects/{ctx['foreign']}/board").json()
    foreign_column = foreign_board["columns"][0]["id"]
    task_url = f"/api/v1/projects/{ctx['own']}/tasks/{ctx['own_task']}"
    original = ctx["admin"].get(task_url).json()

    assert (
        call(ctx["admin"], raw, "get_kanban_board", {"project_id": ctx["foreign"]})["status"] == 404
    )
    assert (
        call(
            ctx["admin"],
            raw,
            "move_task",
            {
                "project_id": ctx["foreign"],
                "task_id": ctx["task"],
                "payload": {"column_id": foreign_column},
            },
        )["status"]
        == 404
    )
    assert (
        call(
            ctx["admin"],
            raw,
            "move_task",
            {
                "project_id": ctx["own"],
                "task_id": ctx["task"],
                "payload": {"column_id": target},
            },
        )["status"]
        == 404
    )
    assert move(ctx, raw, foreign_column)["status"] == 422
    for neighbor_field in ("before_task_id", "after_task_id"):
        assert move(ctx, raw, target, **{neighbor_field: ctx["task"]})["status"] == 422
    assert ctx["admin"].get(task_url).json() == original
    with Session(ctx["engine"]()) as db:
        assert (
            db.scalar(
                select(TaskActivity).where(
                    TaskActivity.task_id == ctx["own_task"],
                    TaskActivity.action == "moved",
                )
            )
            is None
        )


def test_read_only_connections_cannot_discover_or_call_move(kanban_access):
    ctx, _, kind = kanban_access
    raw = credential(ctx, kind, ["kanban.view"])
    board = read_board(ctx, raw)
    names = {
        tool["name"] for tool in rpc(ctx["admin"], raw, "tools/list").json()["result"]["tools"]
    }
    assert "get_kanban_board" in names
    assert "move_task" not in names
    result = move(ctx, raw, board["columns"][-1]["id"])
    assert result["status"] == 403
    current = next(task for task in read_board(ctx, raw)["tasks"] if task["id"] == ctx["own_task"])
    assert current["kanban_column_id"] == board["columns"][0]["id"]
