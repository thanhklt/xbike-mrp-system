from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import settings
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
    "ma_bi_trung": 409,
    "thieu_if_match": 428,
    "du_lieu_da_thay_doi": 412,
    "danh_muc_chua_san_sang": 503,
    "mat_hang_ngung_hoat_dong": 409,
    "bom_co_chu_trinh": 409,
    "thieu_bom": 409,
    "du_lieu_khong_hop_le": 422,
    "trang_thai_khong_hop_le": 409,
    "nguoi_duoc_giao_khong_hop_le": 409,
    "ke_hoach_da_thay_doi": 409,
    "phu_thuoc_khong_hop_le": 409,
    "dang_duoc_tham_chieu": 409,
    "vuot_nhu_cau": 409,
    "khong_du_ton_kho": 409,
}


def _uses_contract_envelope(request: Request) -> bool:
    path = request.url.path
    prefix = settings.api_v1_str
    return path.startswith(f"{prefix}/auth/") or any(
        path == f"{prefix}/{resource}" or path.startswith(f"{prefix}/{resource}/")
        for resource in (
            "nhan_vien",
            "vai_tro",
            "mat_hang",
            "danh_muc_mat_hang",
            "nha_cung_cap",
            "bom",
            "yeu_cau_san_xuat",
            "phieu_nhap",
            "phieu_xuat",
        )
    )


def _contract_error(
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

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        prefix = settings.api_v1_str
        if any(
            request.url.path == f"{prefix}/{name}"
            or request.url.path.startswith(f"{prefix}/{name}/")
            for name in ("mat_hang", "danh_muc_mat_hang")
        ):
            code = {
                412: "du_lieu_da_thay_doi",
                428: "thieu_if_match",
                422: "du_lieu_khong_hop_le",
            }.get(exc.status_code, "loi_http")
            response = _contract_error(request, exc.status_code, code, str(exc.detail), [])
            response.headers.update(exc.headers or {})
            return response
        return await http_exception_handler(request, exc)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        status = ERROR_STATUS.get(exc.code, 500)
        if _uses_contract_envelope(request):
            code = {
                "UNAUTHORIZED": "chua_xac_thuc",
                "FORBIDDEN": "khong_co_quyen",
                "CONFLICT": "trang_thai_khong_hop_le",
                "NOT_FOUND": "khong_tim_thay",
            }.get(exc.code, exc.code)
            return _contract_error(
                request, status, code, exc.message, getattr(exc, "public_details", [])
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
        if _uses_contract_envelope(request):
            details = [
                {
                    "field": ".".join(str(part) for part in error["loc"][1:]),
                    "reason": error["msg"],
                }
                for error in exc.errors()
            ]
            return _contract_error(
                request, 422, "du_lieu_khong_hop_le", "Dữ liệu không hợp lệ", details
            )
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

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception):
        if _uses_contract_envelope(request):
            return _contract_error(request, 500, "loi_noi_bo", "Không thể xử lý yêu cầu", [])
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
