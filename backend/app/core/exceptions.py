from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import (
    AppException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    IncorrectIssueType,
    NotFoundException,
    UnauthorizedException,
    WorkflowNotImplemented,
)

__all__ = [
    "AppException",
    "BadRequestException",
    "ConflictException",
    "ForbiddenException",
    "NotFoundException",
    "UnauthorizedException",
    "register_exception_handlers",
]

ERROR_STATUS = {
    "NOT_FOUND": 404,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "CONFLICT": 409,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Registers custom exception handlers on the FastAPI app instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=ERROR_STATUS.get(exc.code, 500),
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "details": jsonable_encoder(exc.errors()),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.exception_handler(IncorrectIssueType)
    async def incorrect_issue_type_handler(request: Request, exc: IncorrectIssueType):
        return JSONResponse(
            status_code=422, content={"detail": "Incorrect issue type for this endpoint"}
        )

    @app.exception_handler(WorkflowNotImplemented)
    async def unimplemented_handler(request: Request, exc: WorkflowNotImplemented):
        return JSONResponse(
            status_code=501,
            content={"detail": "This workflow has not been implemented; no data was changed."},
        )
