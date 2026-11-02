"""Application failures; HTTP representation belongs to exception handlers."""

from typing import Any


class AppException(Exception):
    code = "INTERNAL_ERROR"
    default_message = "Internal error"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None):
        self.message = message if message is not None else self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    code = "NOT_FOUND"
    default_message = "Resource not found"


class BadRequestException(AppException):
    code = "BAD_REQUEST"
    default_message = "Invalid request"


class UnauthorizedException(AppException):
    code = "UNAUTHORIZED"
    default_message = "Unauthorized"


class ForbiddenException(AppException):
    code = "FORBIDDEN"
    default_message = "Forbidden"


class ConflictException(AppException):
    code = "CONFLICT"
    default_message = "Resource conflict"


class DuplicateCodeException(ConflictException):
    code = "ma_bi_trung"
    default_message = "Tên đăng nhập hoặc mã nhân viên đã tồn tại"


class BomCycleException(ConflictException):
    code = "bom_co_chu_trinh"
    default_message = "BOM tạo chu trình trong cấu trúc"


class MissingBomException(ConflictException):
    code = "thieu_bom"
    default_message = "Bán thành phẩm chưa có BOM hiện hành"


class InvalidInputException(AppException):
    code = "du_lieu_khong_hop_le"
    default_message = "Dữ liệu không hợp lệ"


class PreconditionRequiredException(AppException):
    code = "thieu_if_match"
    default_message = "Thiếu header If-Match"


class PreconditionFailedException(AppException):
    code = "du_lieu_da_thay_doi"
    default_message = "Dữ liệu đã thay đổi; hãy tải lại"


class InvalidCredentialsException(UnauthorizedException):
    code = "thong_tin_dang_nhap_khong_hop_le"
    default_message = "Thông tin đăng nhập không hợp lệ"


class InactiveAccountException(ForbiddenException):
    code = "tai_khoan_bi_vo_hieu_hoa"
    default_message = "Tài khoản không hoạt động"


class IncorrectIssueType(Exception):
    """The issue document belongs to the other issuing flow."""


class WorkflowNotImplemented(Exception):
    """Keep the existing unimplemented workflow behavior explicit."""
