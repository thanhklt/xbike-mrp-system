"""Production limits, scope and replay policy at the application boundary."""

from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidInputException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.modules.san_xuat.ports import HoanThanhContext, HoanThanhOrder, HoanThanhPosting
from app.modules.san_xuat.schemas import HoanThanhPatch, HoanThanhRead
from app.modules.san_xuat.service import (
    ChungTuHoanThanhService,
    HoanThanhExceeded,
    HoanThanhMissingMaterials,
    check_hoan_thanh_quantities,
    check_hoan_thanh_time,
    generate_hoan_thanh_etag,
)

N = {"sub": "3", "roles": ["nhan_vien"]}
Q = {"sub": "2", "roles": ["quan_ly"]}
NOW = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


class Transaction(AbstractAsyncContextManager):
    async def __aexit__(self, *args):
        return False


@pytest.fixture
def feature():
    document = HoanThanhRead(
        id=1,
        ma_phieu="HTSX-202611-000001",
        lenh_san_xuat_id=1,
        so_luong_hoan_thanh=3,
        nhan_vien_id=3,
        trang_thai="nhap",
        finish_time=NOW,
        created_at=NOW,
        mat_hang_id=1,
    )
    order = HoanThanhOrder(1, 1, 1, 10, "dang_thuc_hien", 3, NOW - timedelta(hours=1))
    repo, audit = AsyncMock(), AsyncMock()
    repo.lock_context.return_value = HoanThanhContext(document, order)
    repo.postings.return_value = []
    return ChungTuHoanThanhService(repo, audit, Transaction()), repo, audit, document, order


def test_quantity_uses_approved_sum_and_entire_frozen_material_demand():
    assert check_hoan_thanh_quantities(10, 3, 7, {6: 20}, {6: 20}) == 10
    with pytest.raises(HoanThanhExceeded):
        check_hoan_thanh_quantities(10, 3, 8, {6: 20}, {6: 20})
    with pytest.raises(HoanThanhMissingMaterials):
        check_hoan_thanh_quantities(10, 0, 3, {6: 20}, {6: 8})
    with pytest.raises(HoanThanhMissingMaterials):
        check_hoan_thanh_quantities(10, 0, 3, {}, {})


def test_finish_time_boundary():
    check_hoan_thanh_time(NOW, NOW, submitting=True)
    with pytest.raises(InvalidInputException):
        check_hoan_thanh_time(NOW - timedelta(seconds=1), NOW, submitting=False)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    check_hoan_thanh_time(future, NOW, submitting=False)
    with pytest.raises(InvalidInputException):
        check_hoan_thanh_time(future, NOW, submitting=True)


async def test_noop_patch_keeps_etag_and_audit(feature):
    service, repo, audit, document, _ = feature
    tag = generate_hoan_thanh_etag(document)
    result, new_tag = await service.patch_entry(
        1, HoanThanhPatch(so_luong_hoan_thanh=3), N, tag, "req"
    )
    assert result.data == document and tag == new_tag
    repo.update.assert_not_awaited()
    audit.append.assert_not_awaited()


@pytest.mark.parametrize(
    "header,error",
    [
        (None, PreconditionRequiredException),
        (" ", PreconditionRequiredException),
        ('"old"', PreconditionFailedException),
        ("*", PreconditionFailedException),
        ('W/"old"', PreconditionFailedException),
    ],
)
async def test_writes_require_current_strong_etag(feature, header, error):
    service, _, _, _, _ = feature
    with pytest.raises(error):
        await service.delete_entry(1, N, header)


async def test_reassignment_removes_employee_access(feature):
    service, repo, _, document, order = feature
    from dataclasses import replace

    repo.lock_context.return_value = HoanThanhContext(document, replace(order, assignee_id=4))
    with pytest.raises(ForbiddenException):
        await service.delete_entry(1, N, generate_hoan_thanh_etag(document))


async def test_approved_replay_ignores_stale_etag_and_closed_order(feature):
    service, repo, audit, document, order = feature
    from dataclasses import replace

    document = document.model_copy(update={"trang_thai": "da_duyet"})
    repo.lock_context.return_value = HoanThanhContext(document, replace(order, state="hoan_thanh"))
    repo.postings.return_value = [HoanThanhPosting(7, 1, 3, "nhap_san_pham_san_xuat", 1)]
    result, _ = await service.duyet(1, Q, '"old"', "req")
    assert result.data.da_ghi_so_truoc_do and result.data.giao_dich_kho_ids == [7]
    audit.append.assert_not_awaited()
    repo.post_output.assert_not_awaited()
    repo.postings.return_value = []
    with pytest.raises(ConflictException):
        await service.duyet(1, Q, '"old"', "req")
    with pytest.raises(PreconditionRequiredException):
        await service.duyet(1, Q, None, "req")
