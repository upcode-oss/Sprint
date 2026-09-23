from fastapi import APIRouter

from app.api.dependencies import CurrentUser, DBSession
from app.schemas.dashboard import PersonalDashboardResponse
from app.services.dashboard_service import personal_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=PersonalDashboardResponse)
def dashboard(db: DBSession, current: CurrentUser) -> dict:
    return personal_dashboard(db, current)
