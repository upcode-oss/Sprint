from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, list[str]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        super().__init__(message)


def _payload(request: Request, code: str, message: str, fields: Any = None) -> dict[str, Any]:
    return {
        "error": {"code": code, "message": message, "fields": fields},
        "request_id": getattr(request.state, "request_id", None),
    }


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_payload(request, exc.code, exc.message, exc.fields),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, list[str]] = {}
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body") or "request"
        fields.setdefault(location, []).append(error["msg"])
    return JSONResponse(
        status_code=422,
        content=_payload(request, "validation_error", "The request is invalid", fields),
    )


async def integrity_error_handler(request: Request, _: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=_payload(
            request,
            "conflict",
            "The operation conflicts with an existing record",
        ),
    )
