from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

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
    "ACCOUNT_INACTIVE": 401,
}


def _employee_contract(request: Request) -> bool:
    return bool(
        {"nhan_vien", "vai_tro"}.intersection(getattr(request.scope.get("route"), "tags", []))
    )


def _employee_error(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: object = None,
    headers: dict | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    request.state.request_id = request_id
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else [],
            },
            "meta": {"request_id": request_id},
        },
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers custom exception handlers on the FastAPI app instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        if _employee_contract(request):
            codes = {
                "NOT_FOUND": (404, "khong_tim_thay"),
                "FORBIDDEN": (403, "khong_co_quyen"),
                "UNAUTHORIZED": (401, "chua_xac_thuc"),
                "ACCOUNT_INACTIVE": (403, "tai_khoan_bi_vo_hieu_hoa"),
                "CONFLICT": (409, "ma_bi_trung"),
                "BAD_REQUEST": (422, "du_lieu_khong_hop_le"),
            }
            status, code = codes.get(exc.code, (getattr(exc, "status_code", 500), exc.code))
            return _employee_error(
                request,
                status,
                code,
                exc.message,
                headers={"WWW-Authenticate": "Bearer"} if status == 401 else None,
            )
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
        if _employee_contract(request):
            details = [
                {
                    "field": ".".join(
                        str(p) for p in error["loc"] if p not in {"body", "query", "path"}
                    ),
                    "reason": error["msg"],
                }
                for error in exc.errors()
            ]
            return _employee_error(
                request, 422, "du_lieu_khong_hop_le", "Dữ liệu không hợp lệ.", details
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

    @app.exception_handler(HTTPException)
    async def employee_http_error(request: Request, exc: HTTPException):
        if _employee_contract(request):
            return _employee_error(
                request,
                exc.status_code,
                "chua_xac_thuc" if exc.status_code == 401 else "du_lieu_khong_hop_le",
                "Yêu cầu không hợp lệ.",
                headers=exc.headers,
            )
        return await http_exception_handler(request, exc)

    @app.exception_handler(SQLAlchemyError)
    async def employee_database_error(request: Request, exc: SQLAlchemyError):
        if _employee_contract(request):
            return _employee_error(
                request, 503, "dich_vu_tam_thoi_khong_kha_dung", "Database tạm thời không khả dụng."
            )
        raise exc

    @app.exception_handler(Exception)
    async def unexpected_employee_error(request: Request, exc: Exception):
        if _employee_contract(request):
            return _employee_error(request, 500, "loi_noi_bo", "Lỗi nội bộ.")
        raise exc

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
