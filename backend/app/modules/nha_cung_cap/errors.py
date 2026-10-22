"""Supplier mutation failures translated by the contract HTTP handler."""

from app.core.errors import AppException, ConflictException


class SupplierCodeConflict(ConflictException):
    code = "ma_bi_trung"
    default_message = "Mã nhà cung cấp đã tồn tại"


class SupplierReferenced(ConflictException):
    code = "dang_duoc_tham_chieu"
    default_message = "Nhà cung cấp đã có phiếu tham chiếu, không thể xóa hoặc đổi mã"


class SupplierPreconditionRequired(AppException):
    code = "thieu_if_match"
    default_message = "Cần gửi If-Match từ GET chi tiết"


class SupplierPreconditionFailed(AppException):
    code = "du_lieu_da_thay_doi"
    default_message = "ETag không khớp, hãy tải lại nhà cung cấp"
