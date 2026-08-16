from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredAvatar:
    key: str
    mime_type: str


class AvatarStorage(Protocol):
    def save(self, content: bytes, mime_type: str) -> StoredAvatar: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str | None) -> None: ...
