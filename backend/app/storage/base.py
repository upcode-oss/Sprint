from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredImage:
    key: str
    mime_type: str


class ImageStorage(Protocol):
    def save(self, content: bytes, mime_type: str) -> StoredImage: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str | None) -> None: ...


# Backwards-compatible names for the existing profile service.
StoredAvatar = StoredImage
AvatarStorage = ImageStorage
