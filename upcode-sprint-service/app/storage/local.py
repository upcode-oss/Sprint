import os
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.errors import APIError
from app.storage.base import StoredImage

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class LocalImageStorage:
    def __init__(self, root: Path, asset_name: str) -> None:
        self.root = root.resolve()
        self.asset_name = asset_name
        self.display_name = asset_name.replace("_", " ").title()

    @property
    def not_found_code(self) -> str:
        return f"{self.asset_name}_not_found"

    @property
    def storage_failed_code(self) -> str:
        return f"{self.asset_name}_storage_failed"

    def _path(self, key: str) -> Path:
        if Path(key).name != key:
            raise APIError(404, self.not_found_code, f"{self.display_name} not found")
        path = (self.root / key).resolve()
        if path.parent != self.root:
            raise APIError(404, self.not_found_code, f"{self.display_name} not found")
        return path

    def save(self, content: bytes, mime_type: str) -> StoredImage:
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
            raise APIError(
                500,
                self.storage_failed_code,
                f"{self.display_name} could not be stored",
            ) from exc
        return StoredImage(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except OSError as exc:
            raise APIError(
                404, self.not_found_code, f"{self.display_name} not found"
            ) from exc

    def delete(self, key: str | None) -> None:
        if not key:
            return
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError as exc:
            raise APIError(
                500,
                self.storage_failed_code,
                f"{self.display_name} could not be removed",
            ) from exc


class LocalAvatarStorage(LocalImageStorage):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "avatar")


class LocalOrganizationLogoStorage(LocalImageStorage):
    def __init__(self, root: Path) -> None:
        super().__init__(root, "organization_logo")


avatar_storage = LocalAvatarStorage(settings.avatar_storage_path)
organization_logo_storage = LocalOrganizationLogoStorage(
    settings.organization_logo_storage_path
)
