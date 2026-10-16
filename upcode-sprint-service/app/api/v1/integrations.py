from fastapi import HTTPException
from fastapi.routing import APIRoute
from sqlalchemy import select

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.core.errors import APIError
from app.core.installation import installation_store
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.instance_link import create_link_router
from app.models.identity import Organization
from app.models.integration import InstanceConnection
from app.services.auth_service import authenticate as authenticate_user
from app.services.permission_service import require_permissions


class IntegrationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request):
            try:
                return await handler(request)
            except HTTPException as exc:
                raise APIError(
                    exc.status_code, "instance_connection_error", str(exc.detail)
                ) from exc

        return handle


def administrator(user: CurrentUser):
    require_permissions(user, ["settings.manage"])
    return user


def authenticate(db, username, password, request):
    user = authenticate_user(db, username, password)
    require_permissions(user, ["settings.manage"])


def identity(db):
    organization = db.scalar(select(Organization))
    if organization is None:
        raise HTTPException(503, "Complete the installation setup first")
    return {"name": organization.name, "url": settings.public_app_url}


router = create_link_router(
    product="sprint",
    model=InstanceConnection,
    get_db=get_db,
    admin=administrator,
    authenticate=authenticate,
    identity=identity,
    encrypt=installation_store.encrypt,
    decrypt=installation_store.decrypt,
    pair_limit=limiter.limit(settings.login_rate_limit),
    route_class=IntegrationRoute,
)
