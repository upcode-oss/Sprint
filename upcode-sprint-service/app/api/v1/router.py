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
    two_factor,
    users,
)
from app.mcp_key_routes import feature_router as mcp_feature_router
from app.mcp_key_routes import router as mcp_keys_router
from app.mcp_oauth_routes import router as mcp_oauth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(setup.router)
api_router.include_router(auth.router)
api_router.include_router(mcp_keys_router)
api_router.include_router(mcp_oauth_router)
api_router.include_router(mcp_feature_router)
api_router.include_router(two_factor.router)
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
