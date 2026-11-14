"""UC-34..40: business guards without HTTP/database dependencies."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.errors import (
    ForbiddenException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.modules.phieu_xuat.errors import IssueDependencyInvalid
from app.modules.phieu_xuat.ports import IssuePart, IssueSource
from app.modules.phieu_xuat.schemas import PhieuXuatCreate, PhieuXuatQuery
from app.modules.phieu_xuat.service import PhieuXuatService


@pytest.mark.parametrize("roles", [["nhan_vien"], ["quan_tri_vien"], []])
async def test_uc40_gi_ac01_list_requires_manager(roles):
    repo = SimpleNamespace(begin_read_snapshot=AsyncMock(), list_issues=AsyncMock())
    service = PhieuXuatService(repo, None, None, None)
    with pytest.raises(ForbiddenException):
        await service.list_issues(PhieuXuatQuery(), {"sub": "1", "roles": roles}, "test")
    repo.begin_read_snapshot.assert_not_awaited()


@pytest.mark.parametrize("value", [None, "", " "])
def test_uc35_gi_ac12_missing_validator(value):
    with pytest.raises(PreconditionRequiredException):
        PhieuXuatService._require_if_match(value)


@pytest.mark.parametrize(
    "value",
    ["*", 'W/"abc"', '"abc"', '"' + "a" * 64 + '","' + "b" * 64 + '"', '"' + "A" * 64 + '"'],
)
def test_uc35_gi_ac12_only_one_canonical_strong_validator(value):
    with pytest.raises(PreconditionFailedException):
        PhieuXuatService._require_if_match(value)


def test_uc34_gi_ac03_input_only_source_and_kind():
    payload = PhieuXuatCreate(loai_phieu="xuat_linh_kien", yeu_cau_san_xuat_id=1)
    assert payload.model_dump() == {"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": 1}


@pytest.mark.parametrize("roles", [["quan_ly"], ["quan_tri_vien"]])
async def test_uc34_gi_ac01_manager_cannot_create_directly(roles):
    repository = SimpleNamespace(lock_source=AsyncMock())
    service = PhieuXuatService(repository, None, None, None)
    with pytest.raises(ForbiddenException):
        await service.create_issue(
            PhieuXuatCreate(loai_phieu="xuat_linh_kien", yeu_cau_san_xuat_id=1),
            {"sub": "2", "roles": roles},
            "test",
        )
    repository.lock_source.assert_not_awaited()


@pytest.mark.parametrize("wrong", [True, "1", 1.5, 0, -1, 2147483648])
def test_uc34_gi_ac03_strict_source_id(wrong):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PhieuXuatCreate(loai_phieu="xuat_linh_kien", yeu_cau_san_xuat_id=wrong)


async def test_uc34_gi_ac02_assignment_before_catalog_or_write():
    source = IssueSource("dang_thuc_hien", 3, 1, {7: 7}, "dap_ung", 7, None, None, {})
    repository = SimpleNamespace(
        lock_source=AsyncMock(return_value=source), lock_parts=AsyncMock(), add=AsyncMock()
    )
    service = PhieuXuatService(repository, None, AsyncMock(), None)
    with pytest.raises(ForbiddenException):
        await service.create_issue(
            PhieuXuatCreate(loai_phieu="xuat_linh_kien", yeu_cau_san_xuat_id=1),
            {"sub": "2", "roles": ["nhan_vien"]},
            "test",
        )
    repository.lock_parts.assert_not_awaited()
    repository.add.assert_not_awaited()


async def test_uc37_gi_ac20_old_source_uses_snapshot_not_current_activity():
    source = IssueSource("dang_thuc_hien", 2, 1, {7: 10}, "dap_ung", 0, None, None, {})
    repository = SimpleNamespace(
        lock_parts=AsyncMock(return_value=[IssuePart(7, "thanh_pham", False, 100, 10)])
    )
    service = PhieuXuatService(repository, None, None, None)
    assert (await service._validate("xuat_thanh_pham", source))[0].active is False


def test_uc35_gi_ac15_17_stock_policy_rejects_non_integer_prices():
    from app.modules.inventory.ports import IssueReservation, IssueStockContext

    source = IssueSource("dang_thuc_hien", 2, 1, {7: 7}, "dap_ung", 7, None, None, {})
    record = SimpleNamespace(
        loai_phieu="xuat_linh_kien", chi_tiet=[SimpleNamespace(mat_hang_id=7, so_luong=7)]
    )
    stock = IssueStockContext(
        7, "linh_kien", True, 10, 7, 10, (IssueReservation(1, 1, 7, "linh_kien", 7, None),)
    )
    with pytest.raises(IssueDependencyInvalid):
        PhieuXuatService._stock_policy(record, source, [stock])
