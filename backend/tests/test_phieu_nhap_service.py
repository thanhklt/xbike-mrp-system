"""UC-20..22: receipt business rules independently of HTTP/PostgreSQL."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.errors import ForbiddenException
from app.modules.phieu_nhap.errors import ReceiptPreconditionFailed, ReceiptPreconditionRequired
from app.modules.phieu_nhap.schemas import PhieuNhapCreate, PhieuNhapListQuery, PhieuNhapPatch
from app.modules.phieu_nhap.service import PhieuNhapService


@pytest.mark.parametrize("price", ["12500", "12500.50", 1.5, True, -1, 2**63])
def test_uc20_gr_ac02_money_is_strict_integer_vnd(price):
    with pytest.raises(ValidationError):
        PhieuNhapCreate(
            ncc_id=1,
            ngay_nhap="2026-11-14",
            chi_tiet=[{"mat_hang_id": 1, "so_luong": 1, "don_gia_thuc": price}],
        )


@pytest.mark.parametrize("roles", [["nhan_vien"], ["quan_tri_vien"], []])
async def test_uc22_gr_ac01_list_requires_manager(roles):
    repository = SimpleNamespace(begin_read_snapshot=AsyncMock(), list_receipts=AsyncMock())
    service = PhieuNhapService(repository, None, None, None)
    with pytest.raises(ForbiddenException):
        await service.list_receipts(PhieuNhapListQuery(), {"sub": "1", "roles": roles}, "test")
    repository.begin_read_snapshot.assert_not_awaited()


@pytest.mark.parametrize("tag", [None, "", " "])
def test_uc21_gr_ac11_missing_validator(tag):
    with pytest.raises(ReceiptPreconditionRequired):
        PhieuNhapService._require_if_match(tag)


@pytest.mark.parametrize("tag", ["*", 'W/"abc"', '"abc"', '"' + "a" * 64 + '","' + "b" * 64 + '"'])
def test_uc21_gr_ac11_invalid_validator(tag):
    with pytest.raises(ReceiptPreconditionFailed):
        PhieuNhapService._require_if_match(tag)


@pytest.mark.parametrize("operation", ["get", "create", "patch", "delete", "complete"])
@pytest.mark.parametrize("roles", [["nhan_vien"], ["quan_tri_vien"]])
async def test_uc20_uc21_uc22_gr_ac01_direct_service_rejects_unauthorized_actor(operation, roles):
    service = PhieuNhapService(None, None, None, None)
    actor = {"sub": "1", "roles": roles}
    payload = PhieuNhapCreate(
        ncc_id=1,
        ngay_nhap="2026-11-14",
        chi_tiet=[{"mat_hang_id": 1, "so_luong": 1, "don_gia_thuc": 1}],
    )
    with pytest.raises(ForbiddenException):
        if operation == "get":
            await service.get_receipt(1, actor, "test")
        elif operation == "create":
            await service.create_receipt(payload, actor, "test")
        elif operation == "patch":
            await service.patch_receipt(1, PhieuNhapPatch(), None, actor, "test")
        elif operation == "delete":
            await service.delete_receipt(1, None, actor)
        else:
            await service.complete_receipt(1, None, actor, "test")


@pytest.mark.parametrize("quantity", [True, "1", 0, -1, 2**31])
def test_uc20_gr_ac02_quantity_is_positive_strict_integer(quantity):
    with pytest.raises(ValidationError):
        PhieuNhapCreate(
            ncc_id=1,
            ngay_nhap="2026-11-14",
            chi_tiet=[{"mat_hang_id": 1, "so_luong": quantity, "don_gia_thuc": 1}],
        )
