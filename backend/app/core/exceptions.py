from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
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
from app.core.request_context import get_request_id

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
    "thong_tin_dang_nhap_khong_hop_le": 401,
    "tai_khoan_bi_vo_hieu_hoa": 403,
    "NOT_FOUND": 404,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "CONFLICT": 409,
}


def _is_auth(request: Request) -> bool:
    return request.url.path.startswith(f"{settings.API_V1_STR}/auth/")


def _auth_error(
    request: Request, status: int, code: str, message: str, details: list
) -> JSONResponse:
    headers = {"Cache-Control": "no-store", "Pragma": "no-cache"}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={
            "error": {"code": code, "message": message, "details": details},
            "meta": {"request_id": get_request_id(request)},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers custom exception handlers on the FastAPI app instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        status = ERROR_STATUS.get(exc.code, 500)
        if _is_auth(request):
            code = {
                "UNAUTHORIZED": "chua_xac_thuc",
                "FORBIDDEN": "khong_co_quyen",
                "CONFLICT": "trang_thai_khong_hop_le",
            }.get(exc.code, exc.code)
            return _auth_error(request, status, code, exc.message, [])
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
        if _is_auth(request):
            details = [
                {
                    "field": ".".join(str(part) for part in error["loc"][1:]),
                    "reason": error["msg"],
                }
                for error in exc.errors()
            ]
            return _auth_error(
                request, 422, "du_lieu_khong_hop_le", "Dữ liệu không hợp lệ", details
            )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "details": exc.errors(),
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

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception):
        if _is_auth(request):
            return _auth_error(request, 500, "loi_noi_bo", "Không thể xử lý yêu cầu", [])
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
