"""Business failures for receipt validation and lifecycle transitions."""

from app.core.errors import AppException, ConflictException


class ReceiptDependencyInvalid(ConflictException):
    code = "phu_thuoc_khong_hop_le"
    default_message = "Receipt items must be active raw materials or components"


class ReceiptCodeConflict(ConflictException):
    code = "ma_bi_trung"
    default_message = "Receipt code already exists"


class ReceiptPreconditionRequired(AppException):
    code = "thieu_if_match"
    default_message = "Send If-Match from GET receipt detail"


class ReceiptPreconditionFailed(AppException):
    code = "du_lieu_da_thay_doi"
    default_message = "Receipt has changed; reload it before retrying"


class ReceiptReferenced(ConflictException):
    code = "dang_duoc_tham_chieu"
    default_message = "Receipt items already have stock ledger references"
