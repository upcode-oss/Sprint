from typing import Literal

from pydantic import Field

from app.mcp_toolkit import APITool
from app.permissions.catalog import PERMISSION_DESCRIPTIONS
from app.schemas.collaboration import DocumentCreate, DocumentUpdate
from app.schemas.common import UUIDString
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    SprintCompleteRequest,
    SprintCreate,
    SprintUpdate,
    TaskCommentCreate,
    TaskCreate,
    TaskUpdate,
)

PROJECT = {"project_id": UUIDString}
TASK = {**PROJECT, "task_id": UUIDString}
DOCUMENT = {**PROJECT, "document_id": UUIDString}
SPRINT = {**PROJECT, "sprint_id": UUIDString}
PAGING = {
    "page": (int, Field(default=1, ge=1)),
    "page_size": (int, Field(default=25, ge=1, le=100)),
}
SEARCH = (str | None, Field(default=None, max_length=200))

TOOLS = [
    APITool(
        "get_current_user",
        "Read the authenticated key owner's own account.",
        "profile.read",
        "GET",
        "/auth/me",
    ),
    APITool(
        "list_projects",
        "List projects visible through the owner's current team memberships and roles.",
        "projects.view",
        "GET",
        "/projects",
        query_fields={**PAGING, "search": SEARCH},
    ),
    APITool(
        "get_project",
        "Read an accessible project's details.",
        "projects.view",
        "GET",
        "/projects/{project_id}",
        PROJECT,
    ),
    APITool(
        "get_project_overview",
        "Read an accessible project's overview.",
        "projects.view",
        "GET",
        "/projects/{project_id}/overview",
        PROJECT,
    ),
    APITool(
        "get_project_activity",
        "Read an accessible project's activity history.",
        "projects.view",
        "GET",
        "/projects/{project_id}/activity",
        PROJECT,
        PAGING,
    ),
    APITool(
        "create_project",
        "Create a project using the owner's existing project-creation permission.",
        "projects.create",
        "POST",
        "/projects",
        payload=ProjectCreate,
    ),
    APITool(
        "update_project",
        "Update an accessible project with Projects Edit permission.",
        "projects.edit",
        "PATCH",
        "/projects/{project_id}",
        PROJECT,
        payload=ProjectUpdate,
    ),
    APITool(
        "delete_project",
        "Permanently delete an accessible project with Projects Delete permission.",
        "projects.delete",
        "DELETE",
        "/projects/{project_id}",
        PROJECT,
    ),
    APITool(
        "list_tasks",
        "List tasks in an accessible project.",
        "kanban.view",
        "GET",
        "/projects/{project_id}/tasks",
        PROJECT,
    ),
    APITool(
        "get_task",
        "Read a task belonging to the specified accessible project.",
        "kanban.view",
        "GET",
        "/projects/{project_id}/tasks/{task_id}",
        TASK,
    ),
    APITool(
        "create_task",
        "Create a task in an accessible project with Kanban Manage permission.",
        "kanban.manage",
        "POST",
        "/projects/{project_id}/tasks",
        PROJECT,
        payload=TaskCreate,
    ),
    APITool(
        "update_task",
        "Update a task belonging to an accessible project with Kanban Manage permission.",
        "kanban.manage",
        "PATCH",
        "/projects/{project_id}/tasks/{task_id}",
        TASK,
        payload=TaskUpdate,
    ),
    APITool(
        "delete_task",
        "Delete a task belonging to an accessible project with Kanban Manage permission.",
        "kanban.manage",
        "DELETE",
        "/projects/{project_id}/tasks/{task_id}",
        TASK,
    ),
    APITool(
        "list_task_comments",
        "Read comments on a task belonging to an accessible project.",
        "kanban.view",
        "GET",
        "/projects/{project_id}/tasks/{task_id}/comments",
        TASK,
    ),
    APITool(
        "comment_on_task",
        "Comment on an accessible project's task with Kanban Manage permission.",
        "kanban.manage",
        "POST",
        "/projects/{project_id}/tasks/{task_id}/comments",
        TASK,
        payload=TaskCommentCreate,
    ),
    APITool(
        "list_documents",
        "List documents in an accessible project.",
        "documents.view",
        "GET",
        "/projects/{project_id}/documents",
        PROJECT,
        {"search": SEARCH},
    ),
    APITool(
        "get_document",
        "Read a document belonging to an accessible project.",
        "documents.view",
        "GET",
        "/projects/{project_id}/documents/{document_id}",
        DOCUMENT,
    ),
    APITool(
        "create_document",
        "Create a document in an accessible project.",
        "documents.create",
        "POST",
        "/projects/{project_id}/documents",
        PROJECT,
        payload=DocumentCreate,
    ),
    APITool(
        "update_document",
        "Update a document belonging to an accessible project.",
        "documents.edit",
        "PATCH",
        "/projects/{project_id}/documents/{document_id}",
        DOCUMENT,
        payload=DocumentUpdate,
    ),
    APITool(
        "delete_document",
        "Delete a document belonging to an accessible project.",
        "documents.delete",
        "DELETE",
        "/projects/{project_id}/documents/{document_id}",
        DOCUMENT,
    ),
    APITool(
        "list_sprints",
        "List Scrum sprints in an accessible project.",
        "scrum.view",
        "GET",
        "/projects/{project_id}/sprints",
        PROJECT,
        {"status": (Literal["planned", "active", "completed", "cancelled"] | None, None)},
    ),
    APITool(
        "create_sprint",
        "Create a Scrum sprint in an accessible project.",
        "scrum.manage",
        "POST",
        "/projects/{project_id}/sprints",
        PROJECT,
        payload=SprintCreate,
    ),
    APITool(
        "update_sprint",
        "Update a sprint belonging to an accessible project.",
        "scrum.manage",
        "PATCH",
        "/projects/{project_id}/sprints/{sprint_id}",
        SPRINT,
        payload=SprintUpdate,
    ),
    APITool(
        "start_sprint",
        "Start a sprint belonging to an accessible project.",
        "scrum.manage",
        "POST",
        "/projects/{project_id}/sprints/{sprint_id}/start",
        SPRINT,
    ),
    APITool(
        "complete_sprint",
        "Complete a sprint belonging to an accessible project.",
        "scrum.manage",
        "POST",
        "/projects/{project_id}/sprints/{sprint_id}/complete",
        SPRINT,
        payload=SprintCompleteRequest,
    ),
    APITool(
        "cancel_sprint",
        "Cancel a sprint belonging to an accessible project.",
        "scrum.manage",
        "POST",
        "/projects/{project_id}/sprints/{sprint_id}/cancel",
        SPRINT,
    ),
]

BY_NAME = {tool.name: tool for tool in TOOLS}
SCOPE_DESCRIPTIONS = {
    scope: PERMISSION_DESCRIPTIONS.get(scope, "Read your own account profile")
    for scope in sorted({tool.scope for tool in TOOLS})
}
