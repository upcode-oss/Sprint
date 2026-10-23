import pytest
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.services.auth_service import authenticate, change_password, issue_tokens


def test_authentication_and_password_change(db: Session, workspace: dict[str, object]) -> None:
    member = workspace["member"]
    authenticated = authenticate(db, "member", "MemberPassword123")
    assert authenticated.id == member.id
    assert authenticated.last_login is not None
    access, refresh = issue_tokens(authenticated)
    assert access and refresh

    old_version = authenticated.token_version
    change_password(db, authenticated, "MemberPassword123", "ChangedPassword123")
    assert authenticated.token_version == old_version + 1
    assert authenticate(db, "member", "ChangedPassword123").id == member.id
    with pytest.raises(APIError, match="incorrect"):
        authenticate(db, "member", "MemberPassword123")


def test_disabled_user_cannot_authenticate(db: Session, workspace: dict[str, object]) -> None:
    member = workspace["member"]
    member.is_active = False
    db.commit()
    with pytest.raises(APIError) as error:
        authenticate(db, "member", "MemberPassword123")
    assert error.value.code == "account_disabled"


def test_password_reset_uses_saved_public_url(db, workspace, tmp_path, monkeypatch):
    from app.core.installation import installation_store
    from app.models.identity import SMTPConfiguration
    from app.services import auth_service

    monkeypatch.setattr(installation_store, "path", tmp_path / "installation.json")
    installation_store.save({"public_app_url": "http://192.168.122.45:3000"})
    db.add(
        SMTPConfiguration(
            organization_id=workspace["organization"].id,
            host="smtp.example.com",
            port=587,
            from_address="sprint@example.com",
            from_name="Sprint",
        )
    )
    db.commit()
    messages = []
    monkeypatch.setattr(auth_service, "send_email", lambda *args: messages.append(args))
    auth_service.request_password_reset(db, workspace["member"].email)
    assert len(messages) == 1
    assert "http://192.168.122.45:3000/reset-password?token=" in messages[0][3]
