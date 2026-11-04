"""Public confirmation failure after the ticket transaction has committed."""

from app.core.errors import ConflictException


class AdjustmentFailed(ConflictException):
    code = "dieu_chinh_khong_hop_le"

    def __init__(self, message: str, details: list[dict], *, phieu_id: int, ticket_id: int):
        super().__init__(message=message)
        self.public_details = details
        self.public_extra = {
            "phieu_dieu_chinh_kho_id": phieu_id,
            "trang_thai_phieu": "loi",
            "ticket_id": ticket_id,
            "ticket_da_luu": True,
        }
