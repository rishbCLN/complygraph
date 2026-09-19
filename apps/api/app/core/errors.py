"""Structured API error handling.

All errors are returned in the shape:
    {"error": {"code": ..., "message": ..., "request_id": ...}}
Stack traces are logged server-side and never leaked to the client.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("complygraph.api")


class AppError(Exception):
    """Base application error mapped to a structured JSON response."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"


class AuthError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


def _error_body(code: str, message: str, request: Request) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):  # noqa: ANN202
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):  # noqa: ANN202
        code = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
        }.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
        return JSONResponse(status_code=exc.status_code, content=_error_body(code, message, request))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):  # noqa: ANN202
        return JSONResponse(
            status_code=422,
            content=_error_body("VALIDATION_ERROR", "Request validation failed.", request)
            | {"details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):  # noqa: ANN202
        logger.error(
            "Unhandled exception on %s %s\n%s",
            request.method,
            request.url.path,
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        )
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "An internal error occurred.", request),
        )
