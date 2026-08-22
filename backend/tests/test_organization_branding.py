import base64

import pytest
from sqlalchemy.orm import Session

from app.api.v1 import settings as settings_api
from app.core.errors import APIError
from app.services.organization_service import (
    remove_organization_logo,
    replace_organization_logo,
    resolve_staged_organization_logo,
    save_staged_organization_logo,
)
from app.storage.local import LocalOrganizationLogoStorage

VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_organization_logo_uses_random_internal_key(tmp_path) -> None:
    storage = LocalOrganizationLogoStorage(tmp_path / "organization-logos")
    stored = save_staged_organization_logo(VALID_PNG, "image/png", storage)

    assert stored.key.endswith(".png")
    assert len(stored.key) == 36
    assert storage.read(stored.key) == VALID_PNG
    assert resolve_staged_organization_logo(stored.key, storage) == stored


@pytest.mark.parametrize(
    ("content", "mime_type"),
    [(b"not-an-image", "image/png"), (VALID_PNG, "image/jpeg")],
)
def test_invalid_organization_logo_is_rejected(
    tmp_path, content: bytes, mime_type: str
) -> None:
    storage = LocalOrganizationLogoStorage(tmp_path / "organization-logos")

    with pytest.raises(APIError) as error:
        save_staged_organization_logo(content, mime_type, storage)

    assert error.value.status_code == 422
    assert error.value.code == "invalid_organization_logo"


def test_replacing_and_removing_organization_logo(
    db: Session, workspace: dict[str, object], tmp_path
) -> None:
    organization = workspace["organization"]
    storage = LocalOrganizationLogoStorage(tmp_path / "organization-logos")
    first = replace_organization_logo(db, organization, VALID_PNG, "image/png", storage)
    second = replace_organization_logo(db, organization, VALID_PNG, "image/png", storage)

    assert organization.logo_key == second.key
    assert organization.logo_mime_type == "image/png"
    expected_version = int(organization.updated_at.timestamp())
    assert organization.logo_url == f"/api/v1/organization/logo?v={expected_version}"
    assert first.key not in organization.logo_url
    with pytest.raises(APIError) as error:
        storage.read(first.key)
    assert error.value.status_code == 404

    remove_organization_logo(db, organization, storage)
    assert organization.logo_key is None
    assert organization.logo_mime_type is None
    assert organization.logo_url is None
    with pytest.raises(APIError):
        storage.read(second.key)


def test_branding_and_logo_are_available_before_login(
    db: Session, workspace: dict[str, object], tmp_path, monkeypatch
) -> None:
    organization = workspace["organization"]
    storage = LocalOrganizationLogoStorage(tmp_path / "organization-logos")
    monkeypatch.setattr(settings_api, "organization_logo_storage", storage)
    replace_organization_logo(db, organization, VALID_PNG, "image/png", storage)

    branding = settings_api.organization_branding(db)
    logo = settings_api.organization_logo(db)

    assert branding.name == "Test Organization"
    assert branding.logo_url == organization.logo_url
    assert logo.body == VALID_PNG
    assert logo.media_type == "image/png"
