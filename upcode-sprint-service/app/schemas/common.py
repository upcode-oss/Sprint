from datetime import datetime
from typing import Annotated, Generic, TypeVar
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

T = TypeVar("T")


def _validated_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("ID must be a valid UUID") from exc


UUIDString = Annotated[str, AfterValidator(_validated_uuid)]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(APIModel):
    message: str


class PaginationMeta(APIModel):
    page: int
    page_size: int
    total: int
    pages: int


class PaginatedResponse(APIModel, Generic[T]):
    items: list[T]
    meta: PaginationMeta


class ErrorDetail(APIModel):
    code: str
    message: str
    fields: dict[str, list[str]] | None = None


class ErrorResponse(APIModel):
    error: ErrorDetail
    request_id: str | None = None


class TimestampedResponse(APIModel):
    id: str
    created_at: datetime
    updated_at: datetime


class IDListRequest(APIModel):
    ids: list[UUIDString] = Field(default_factory=list, max_length=500)
