"""Production request service."""

from app.modules.san_xuat.service.yeu_cau_san_xuat import (
    YeuCauSanXuatService,
    generate_yeu_cau_etag,
)

__all__ = ["YeuCauSanXuatService", "generate_yeu_cau_etag"]
