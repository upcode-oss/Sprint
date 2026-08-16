import os
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.errors import APIError
from app.storage.base import StoredAvatar

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class LocalAvatarStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        if Path(key).name != key:
            raise APIError(404, "avatar_not_found", "Avatar not found")
        path = (self.root / key).resolve()
        if path.parent != self.root:
            raise APIError(404, "avatar_not_found", "Avatar not found")
        return path

    def save(self, content: bytes, mime_type: str) -> StoredAvatar:
        extension = EXTENSIONS[mime_type]
        key = f"{uuid.uuid4().hex}{extension}"
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self._path(f".{key}.tmp")
        final = self._path(key)
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
            os.replace(temporary, final)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise APIError(500, "avatar_storage_failed", "Avatar could not be stored") from exc
        return StoredAvatar(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except OSError as exc:
            raise APIError(404, "avatar_not_found", "Avatar not found") from exc

    def delete(self, key: str | None) -> None:
        if not key:
            return
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as exc:
            raise APIError(500, "avatar_storage_failed", "Avatar could not be removed") from exc


avatar_storage = LocalAvatarStorage(settings.avatar_storage_path)
