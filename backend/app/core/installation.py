import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class InstallationStore:
    """Stores bootstrap state without exposing database or SMTP credentials."""

    def __init__(self, path: Path | None = None, secret: str | None = None) -> None:
        self.path = path or settings.installation_config_path
        digest = hashlib.sha256((secret or settings.app_secret_key).encode()).digest()
        self._cipher = Fernet(base64.urlsafe_b64encode(digest))

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"setup_completed": False}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"setup_completed": False}

    @property
    def is_complete(self) -> bool:
        return bool(self.load().get("setup_completed"))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2, sort_keys=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".installation-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.chmod(temporary_name, 0o600)
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    def encrypt(self, value: str) -> str:
        return self._cipher.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._cipher.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("Installation secrets cannot be decrypted") from exc

    def configured_database_url(self) -> str | None:
        encrypted = self.load().get("database_url_encrypted")
        return self.decrypt(encrypted) if encrypted else None


installation_store = InstallationStore()
