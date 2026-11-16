"""Issue-specific business conflicts, translated to HTTP at the application boundary."""

from app.core.errors import ConflictException


class IssueDemandExceeded(ConflictException):
    code = "vuot_nhu_cau"
    default_message = "Approved issues would exceed the source demand"


class IssueDependencyInvalid(ConflictException):
    code = "phu_thuoc_khong_hop_le"
    default_message = "Item, source or ledger is inconsistent"
