import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import app.models
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    APIError,
    api_error_handler,
    integrity_error_handler,
    validation_error_handler,
)
from app.core.installation import installation_store
from app.core.rate_limit import limiter
from app.db.migrations import upgrade_database
from app.db.session import current_database_url, get_engine, get_session_factory
from app.services.permission_service import sync_permission_catalog

logger = logging.getLogger("sprint")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_for_startup()
    if installation_store.is_complete:
        upgrade_database(current_database_url())
        db = get_session_factory()()
        try:
            sync_permission_catalog(db)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Database initialization failed")
            raise
        finally:
            db.close()
    yield


app = FastAPI(
    title="Upcode sprint API",
    version=settings.app_version,
    description="API for the self-hosted agile project management platform.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, _: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {"code": "rate_limited", "message": "Too many requests", "fields": None},
            "request_id": getattr(request.state, "request_id", None),
        },
        headers={"Retry-After": "60"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def security_and_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:100]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str | bool]:
    if not installation_store.is_complete:
        return {"status": "setup_required", "ready": True}
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "database_unavailable", "ready": False}
    return {"status": "ready", "ready": True}


app.include_router(api_router)
