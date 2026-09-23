import smtplib
from typing import Annotated

from fastapi import APIRouter, File, Path, Response, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import APIError
from app.core.installation import installation_store
from app.db.session import get_session_factory
from app.models.identity import Organization
from app.schemas.setup import (
    ConnectionTestResponse,
    DatabaseConfiguration,
    SetupCompleteRequest,
    SetupLogoUploadResponse,
    SetupStatusResponse,
    SMTPTestRequest,
)
from app.services.mail_service import send_test_email
from app.services.organization_service import save_staged_organization_logo
from app.services.setup_service import complete_setup, test_database_connection
from app.storage.local import organization_logo_storage

router = APIRouter(prefix="/setup", tags=["setup"])

LogoToken = Annotated[
    str,
    Path(min_length=36, max_length=36, pattern=r"^[0-9a-f]{32}\.(jpg|png|webp)$"),
]


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


@router.post(
    "/logo",
    response_model=SetupLogoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_setup_logo(logo: UploadFile = File(...)) -> SetupLogoUploadResponse:
    if installation_store.is_complete:
        raise APIError(409, "setup_already_completed", "Initial setup is already complete")
    content = await logo.read(settings.organization_logo_max_bytes + 1)
    stored = save_staged_organization_logo(
        content, logo.content_type, organization_logo_storage
    )
    return SetupLogoUploadResponse(
        upload_token=stored.key,
        preview_url=f"/api/v1/setup/logo/{stored.key}",
    )


@router.get("/logo/{logo_token}")
def preview_setup_logo(logo_token: LogoToken) -> Response:
    if installation_store.is_complete:
        raise APIError(404, "organization_logo_not_found", "Organization logo not found")
    content = organization_logo_storage.read(logo_token)
    mime_type = (
        "image/jpeg"
        if logo_token.endswith(".jpg")
        else f"image/{logo_token.rsplit('.', 1)[1]}"
    )
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


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
