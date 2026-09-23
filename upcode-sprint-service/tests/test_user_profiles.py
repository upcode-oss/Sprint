import base64
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.users import _profile_response
from app.core.config import settings
from app.core.errors import APIError
from app.models.identity import Permission, User, UserPresence, UserProfile
from app.permissions.catalog import PermissionKey
from app.schemas.identity import (
    ContactCreate,
    ContactUpdate,
    PresenceUpdate,
    ProfileUpdate,
    UserResponse,
)
from app.services.permission_service import require_permissions
from app.services.presence_service import (
    expire_temporary_presence,
    presence_summary,
    technical_presence,
    touch_presence,
    update_presence,
)
from app.services.profile_service import (
    create_contact,
    save_avatar,
    update_contact,
    update_profile,
    visible_contacts,
)
from app.storage.local import LocalAvatarStorage

VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _colleague(db: Session, workspace: dict[str, object]) -> User:
    team = workspace["team"]
    organization = workspace["organization"]
    viewer_role = workspace["viewer_role"]
    colleague = User(
        organization_id=organization.id,
        username="colleague",
        email="colleague@example.com",
        first_name="Cara",
        last_name="Colleague",
        password_hash="unused-in-profile-tests",
        roles=[viewer_role],
        profile=UserProfile(timezone="Europe/Vienna"),
        presence=UserPresence(),
    )
    team.members.append(colleague)
    db.add(colleague)
    db.commit()
    return colleague


def test_multiple_phone_and_email_contacts_with_one_primary_per_type(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    first_phone = create_contact(
        db,
        member,
        ContactCreate(
            type="phone",
            label="Business",
            value="+43 1 555 100",
            is_primary=True,
            visibility="organization",
        ),
    )
    second_phone = create_contact(
        db,
        member,
        ContactCreate(
            type="phone",
            label="Personal",
            value="+43 1 555 200",
            is_primary=True,
            visibility="private",
        ),
    )
    first_email = create_contact(
        db,
        member,
        ContactCreate(
            type="email",
            label="Business",
            value="CONTACT@EXAMPLE.COM",
            is_primary=True,
            visibility="organization",
        ),
    )
    second_email = create_contact(
        db,
        member,
        ContactCreate(
            type="email",
            label="Personal",
            value="private@example.com",
            visibility="private",
        ),
    )
    db.refresh(first_phone)
    assert not first_phone.is_primary
    assert second_phone.is_primary
    assert first_email.is_primary
    assert not second_email.is_primary
    assert first_email.value == "contact@example.com"
    assert len(member.contacts) == 4


def test_updating_primary_contact_unsets_previous_primary(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    first = create_contact(
        db,
        member,
        ContactCreate(type="mobile", label="One", value="+43 660 11111", is_primary=True),
    )
    second = create_contact(
        db,
        member,
        ContactCreate(type="mobile", label="Two", value="+43 660 22222"),
    )
    update_contact(db, member, second, ContactUpdate(is_primary=True))
    db.refresh(first)
    assert not first.is_primary
    assert second.is_primary


def test_contact_visibility_private_team_and_organization(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    admin = workspace["admin"]
    outsider = workspace["outsider"]
    colleague = _colleague(db, workspace)
    for index, visibility in enumerate(("private", "teams", "organization"), start=1):
        create_contact(
            db,
            member,
            ContactCreate(
                type="phone",
                label=visibility.title(),
                value=f"+43 1 9000{index}",
                visibility=visibility,
            ),
        )

    assert {item.visibility for item in visible_contacts(db, member, member)} == {
        "private",
        "teams",
        "organization",
    }
    assert {item.visibility for item in visible_contacts(db, admin, member)} == {
        "private",
        "teams",
        "organization",
    }
    assert {item.visibility for item in visible_contacts(db, colleague, member)} == {
        "teams",
        "organization",
    }
    assert {item.visibility for item in visible_contacts(db, outsider, member)} == {"organization"}


def test_contact_view_permission_grants_private_access(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    outsider = workspace["outsider"]
    viewer_role = workspace["viewer_role"]
    private = create_contact(
        db,
        member,
        ContactCreate(type="mobile", label="Private", value="+43 699 12345"),
    )
    assert private not in visible_contacts(db, outsider, member)
    permission = db.scalar(
        select(Permission).where(Permission.key == PermissionKey.USERS_CONTACTS_VIEW.value)
    )
    viewer_role.permissions.append(permission)
    db.commit()
    assert private in visible_contacts(db, outsider, member)


def test_profile_editing_and_timezone_validation(db: Session, workspace: dict[str, object]) -> None:
    member = workspace["member"]
    update_profile(
        db,
        member,
        ProfileUpdate(
            first_name="Miriam",
            last_name="Member",
            display_name="Miri",
            job_title="Software Developer",
            department="Engineering",
            bio="Builds useful things.",
            timezone="Europe/Vienna",
            locale="de-AT",
        ),
    )
    assert member.first_name == "Miriam"
    assert member.display_name == "Miri"
    assert member.job_title == "Software Developer"
    assert member.timezone == "Europe/Vienna"
    with pytest.raises(ValidationError):
        ProfileUpdate(timezone="Mars/Olympus")


def test_user_list_response_never_contains_contacts(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    create_contact(
        db,
        member,
        ContactCreate(type="phone", label="Private", value="+43 1 55555"),
    )
    response = UserResponse.model_validate(member).model_dump()
    assert "contacts" not in response
    assert "+43 1 55555" not in str(response)


def test_profile_response_contains_only_visible_contacts(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    outsider = workspace["outsider"]
    create_contact(
        db,
        member,
        ContactCreate(type="phone", label="Private", value="+43 1 11111"),
    )
    organization_contact = create_contact(
        db,
        member,
        ContactCreate(
            type="phone",
            label="Office",
            value="+43 1 22222",
            visibility="organization",
        ),
    )
    response = _profile_response(db, outsider, member)
    assert [contact.id for contact in response.contacts] == [organization_contact.id]
    assert "+43 1 11111" not in response.model_dump_json()


def test_avatar_upload_uses_random_storage_key(
    db: Session, workspace: dict[str, object], tmp_path
) -> None:
    member = workspace["member"]
    storage = LocalAvatarStorage(tmp_path / "avatars")
    stored = save_avatar(db, member, VALID_PNG, "image/png", storage)
    assert stored.key.endswith(".png")
    assert len(stored.key) == 36
    assert storage.read(stored.key) == VALID_PNG
    assert member.avatar_url and stored.key not in member.avatar_url


@pytest.mark.parametrize(
    ("content", "mime_type"),
    [(b"not-an-image", "image/png"), (VALID_PNG, "image/jpeg")],
)
def test_invalid_avatar_upload_is_rejected(
    db: Session, workspace: dict[str, object], tmp_path, content: bytes, mime_type: str
) -> None:
    with pytest.raises(APIError) as error:
        save_avatar(
            db,
            workspace["member"],
            content,
            mime_type,
            LocalAvatarStorage(tmp_path / "avatars"),
        )
    assert error.value.status_code == 422


def test_avatar_size_limit_is_enforced(
    db: Session, workspace: dict[str, object], tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "avatar_max_bytes", 16)
    with pytest.raises(APIError) as error:
        save_avatar(
            db,
            workspace["member"],
            VALID_PNG,
            "image/png",
            LocalAvatarStorage(tmp_path / "avatars"),
        )
    assert error.value.status_code == 413


def test_presence_status_message_and_effective_status(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    now = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
    member.presence.last_seen_at = now
    update_presence(
        db,
        member,
        PresenceUpdate(
            status="do_not_disturb",
            status_message="In a meeting",
            status_until=now + timedelta(hours=1),
        ),
        now,
    )
    summary = presence_summary(member.presence, now + timedelta(minutes=5))
    assert summary["status"] == "do_not_disturb"
    assert summary["technical_status"] == "away"
    assert summary["status_message"] == "In a meeting"


def test_temporary_presence_expires_automatically(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    now = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
    member.presence.manual_status = "away"
    member.presence.status_message = "Lunch"
    member.presence.status_until = now - timedelta(seconds=1)
    member.presence.last_seen_at = now
    db.commit()
    presence = expire_temporary_presence(db, member, now)
    assert presence.manual_status is None
    assert presence.status_message is None
    assert presence_summary(presence, now)["status"] == "available"


def test_last_seen_updates_are_throttled(db: Session, workspace: dict[str, object]) -> None:
    member = workspace["member"]
    now = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
    assert touch_presence(db, member, now, force=True)
    assert not touch_presence(db, member, now + timedelta(seconds=30))
    assert touch_presence(db, member, now + timedelta(seconds=61))
    assert member.presence.last_seen_at == now + timedelta(seconds=61)


def test_technical_presence_thresholds() -> None:
    now = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
    assert technical_presence(now, now) == "available"
    assert technical_presence(now - timedelta(seconds=301), now) == "away"
    assert technical_presence(now - timedelta(seconds=901), now) == "offline"


def test_new_profile_permissions_are_server_side_permissions(workspace: dict[str, object]) -> None:
    member = workspace["member"]
    admin = workspace["admin"]
    with pytest.raises(APIError) as error:
        require_permissions(member, [PermissionKey.USERS_PROFILE_EDIT])
    assert error.value.status_code == 403
    require_permissions(
        admin,
        [
            PermissionKey.USERS_PROFILE_EDIT,
            PermissionKey.USERS_CONTACTS_EDIT,
            PermissionKey.USERS_PRESENCE_EDIT,
        ],
    )
