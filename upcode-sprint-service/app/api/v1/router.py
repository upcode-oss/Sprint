from fastapi import APIRouter

from app.api.v1 import (
    auth,
    boards,
    calendar,
    dashboard,
    documents,
    meetings,
    permissions,
    projects,
    roles,
    settings,
    setup,
    sprints,
    tasks,
    teams,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(teams.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(boards.router)
api_router.include_router(sprints.router)
api_router.include_router(documents.router)
api_router.include_router(meetings.router)
api_router.include_router(calendar.router)
api_router.include_router(settings.router)
