import smtplib

from fastapi import APIRouter
from sqlalchemy import select

from app.core.errors import APIError
from app.core.installation import installation_store
from app.db.session import get_session_factory
from app.models.identity import Organization
from app.schemas.setup import (
    ConnectionTestResponse,
    DatabaseConfiguration,
    SetupCompleteRequest,
    SetupStatusResponse,
    SMTPTestRequest,
)
from app.services.mail_service import send_test_email
from app.services.setup_service import complete_setup, test_database_connection

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
def setup_status() -> SetupStatusResponse:
    if not installation_store.is_complete:
        return SetupStatusResponse(completed=False)
    db = get_session_factory()()
    try:
        organization = db.scalar(select(Organization))
        return SetupStatusResponse(
            completed=True, organization_name=organization.name if organization else None
        )
    finally:
        db.close()


@router.post("/database/test", response_model=ConnectionTestResponse)
def test_database(payload: DatabaseConfiguration) -> ConnectionTestResponse:
    if installation_store.is_complete:
        raise APIError(409, "setup_already_completed", "Initial setup is already complete")
    test_database_connection(payload)
    return ConnectionTestResponse(success=True, message="Database connection succeeded")


@router.post("/smtp/test", response_model=ConnectionTestResponse)
def test_smtp(payload: SMTPTestRequest) -> ConnectionTestResponse:
    if installation_store.is_complete:
        raise APIError(409, "setup_already_completed", "Initial setup is already complete")
    if not payload.smtp.enabled:
        raise APIError(422, "smtp_disabled", "Enable SMTP before sending a test")
    try:
        send_test_email(payload.smtp, str(payload.recipient))
    except (OSError, smtplib.SMTPException) as exc:
        raise APIError(400, "smtp_connection_failed", "SMTP test failed") from exc
    return ConnectionTestResponse(success=True, message="Test email sent")


@router.post("/complete", response_model=SetupStatusResponse, status_code=201)
def finish_setup(payload: SetupCompleteRequest) -> SetupStatusResponse:
    organization, _ = complete_setup(payload)
    return SetupStatusResponse(completed=True, organization_name=organization.name)
