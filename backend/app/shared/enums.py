"""Business enum values used by init.sql and seed.sql."""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "quan_tri_vien"
    MANAGER = "quan_ly"
    EMPLOYEE = "nhan_vien"


class ItemType(str, Enum):
    RAW_MATERIAL = "nguyen_vat_lieu"
    COMPONENT = "linh_kien"
    SUB_ASSEMBLY = "ban_thanh_pham"
    FINISHED_GOOD = "thanh_pham"


class WorkOrderStatus(str, Enum):
    DRAFT = "nhap"
    SENT = "da_gui"
    IN_PROGRESS = "dang_thuc_hien"
    COMPLETED = "hoan_thanh"
    CANCELLED = "da_huy"


class MaterialIssueStatus(str, Enum):
    DRAFT = "nhap"
    PENDING = "cho_duyet"
    APPROVED = "da_duyet"
    REJECTED = "tu_choi"


class GoodsReceiptStatus(str, Enum):
    DRAFT = "nhap"
    COMPLETED = "hoan_thanh"


class StockMovementType(str, Enum):
    RECEIPT = "nhap_vat_tu"
    ISSUANCE_TO_PRODUCTION = "xuat_vat_tu"
    PRODUCTION_RECEIPT = "nhap_san_pham_san_xuat"
    DISPATCH = "xuat_thanh_pham"
    ADJUSTMENT = "dieu_chinh_ton_kho"
