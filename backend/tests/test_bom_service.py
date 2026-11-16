"""UC-15–19: schema and precondition behavior, independent of HTTP/database."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from test_catalog_service import MANAGER, item

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.modules.bom.ports import BomContext
from app.modules.bom.schemas import BomCreate, BomFormula, BomRead
from app.modules.bom.service import BomService
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.mutation import MatHangMutation


@pytest.mark.parametrize(
    "method,args",
    [
        ("create_version", (1, None, {"sub": "2", "roles": ["nhan_vien"]}, None, "test")),
        ("activate_bom", (1, {"sub": "2", "roles": ["nhan_vien"]}, None, "test")),
        ("delete_bom", (1, {"sub": "2", "roles": ["nhan_vien"]}, None)),
        ("get_bom", (1, {"sub": "3", "roles": ["quan_tri_vien"]}, "test")),
    ],
)
async def test_bom_ac01_public_service_denies_before_io(method, args):
    from app.modules.bom.service import BomService

    repository, mutation = AsyncMock(), AsyncMock()
    service = BomService(repository, AsyncMock(), mutation, AsyncMock())
    with pytest.raises(ForbiddenException):
        await getattr(service, method)(*args)
    assert not repository.mock_calls and not mutation.mock_calls


@pytest.mark.parametrize("amount", [True, False, 0, -1, 1.5, "2"])
def test_uc16_ac7_strict_positive_quantity(amount):
    with pytest.raises(ValidationError):
        BomCreate.model_validate(
            {"mat_hang_id": 1, "chi_tiet": [{"mat_hang_id": 2, "so_luong": amount}]}
        )


@pytest.mark.parametrize("value", [None, "", " "])
def test_bom_ac07_missing_precondition(value):
    from app.core.preconditions import verify_if_match

    with pytest.raises(PreconditionRequiredException):
        verify_if_match(value, '"abc"')


@pytest.mark.parametrize("value", ['W/"abc"', "*", "abc", '"old"', '"abc", "other"'])
def test_bom_ac07_reject_non_matching_strong_tag(value):
    from app.core.preconditions import verify_if_match

    with pytest.raises(PreconditionFailedException):
        verify_if_match(value, '"abc"')


@pytest.mark.parametrize("roles", [[], ["nhan_vien"], ["quan_tri_vien"], "quan_ly"])
async def test_bom_ac01_write_guard_precedes_repository(roles):
    from app.modules.bom.service import require_manager

    repo = AsyncMock()
    with pytest.raises(ForbiddenException):
        require_manager({"sub": "1", "roles": roles})
        await repo.add()
    repo.add.assert_not_called()


def version(version_id=1, *, active=True):
    return BomRead(
        id=version_id,
        mat_hang_id=1,
        version=version_id,
        created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        kich_hoat_gan_nhat_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        is_active=active,
        da_duoc_su_dung=False,
        chi_tiet=[{"id": version_id, "mat_hang_id": 2, "so_luong": 1}],
    )


@pytest.fixture
def bom_service():
    cache = MatHangCache()
    cache.replace([item(loai_mat_hang="thanh_pham"), item(2)])
    service = BomService(
        AsyncMock(), AsyncMock(), MatHangMutation(AsyncMock(), cache), AsyncMock()
    )
    service.items.lock_items.return_value = [item(2)]
    return service


# PR-10 D3: active thiếu version đang dùng phải 409, không sửa dữ liệu/audit/cache.
async def test_stop_rejects_active_item_without_active_formula(bom_service):
    service = bom_service
    before = BomContext(item(loai_mat_hang="thanh_pham"), (version(active=False),))
    service.repository.context.return_value = before
    snapshot = service.mutation.cache.snapshot()
    with pytest.raises(ConflictException, match="Trạng thái thành phẩm và công thức không khớp") as error:
        async with service.mutation.scope():
            await service.stop_for_item_in_transaction(1, MANAGER)
    assert error.value.code == "CONFLICT"
    service.items.update.assert_not_awaited()
    service.repository.deactivate.assert_not_awaited()
    service.audit.append.assert_not_awaited()
    assert service.mutation.cache.snapshot() is snapshot


# PR-10 D3: item ngừng còn version active phải 409, không tự đồng bộ/audit.
async def test_reuse_rejects_stopped_item_with_active_formula(bom_service):
    service = bom_service
    stopped = item(loai_mat_hang="thanh_pham").model_copy(update={"is_active": False})
    service.repository.context.return_value = BomContext(stopped, (version(),))
    snapshot = service.mutation.cache.snapshot()
    with pytest.raises(ConflictException, match="Trạng thái thành phẩm và công thức không khớp") as error:
        async with service.mutation.scope():
            await service.reuse_last_for_item_in_transaction(1, MANAGER)
    assert error.value.code == "CONFLICT"
    service.items.update.assert_not_awaited()
    service.repository.activate.assert_not_awaited()
    service.repository.deactivate.assert_not_awaited()
    service.audit.append.assert_not_awaited()
    assert service.mutation.cache.snapshot() is snapshot


@pytest.mark.parametrize(
    "method", ["stop_for_item_in_transaction", "reuse_last_for_item_in_transaction"]
)
@pytest.mark.parametrize("missing_context", [True, False])
# PR-10 D3: giữ nguyên 409 chưa có công thức khi không có phiên bản nào.
async def test_item_lifecycle_without_versions_keeps_conflict(bom_service, method, missing_context):
    service = bom_service
    service.repository.context.return_value = (
        None if missing_context else BomContext(item(loai_mat_hang="thanh_pham"), ())
    )
    with pytest.raises(ConflictException, match="Thành phẩm chưa có công thức") as error:
        async with service.mutation.scope():
            await getattr(service, method)(1, MANAGER)
    assert error.value.code == "CONFLICT"
    service.items.update.assert_not_awaited()
    service.audit.append.assert_not_awaited()


@pytest.mark.parametrize("was_active", [True, False])
# PR-10 F10: tạo phiên bản chỉ UPDATE item đang ngừng; cache lấy item từ after.
async def test_create_version_updates_only_stopped_item(bom_service, was_active):
    service = bom_service
    before_item = item(loai_mat_hang="thanh_pham").model_copy(update={"is_active": was_active})
    old = version(active=was_active)
    before = BomContext(before_item, (old,))
    created = version(2)
    after_item = before_item.model_copy(update={"is_active": True})
    after = BomContext(after_item, (old.model_copy(update={"is_active": False}), created))
    service.repository.add.return_value = created
    # A repository return is deliberately different: publication must use after.item.
    service.items.update.return_value = before_item
    service.repository.context_for_bom.return_value = before
    _, tag = await service.get_bom(1, MANAGER, "test")
    service.repository.context_for_bom.side_effect = [before, before, after]
    result, _ = await service.create_version(
        1, BomFormula(chi_tiet=[{"mat_hang_id": 2, "so_luong": 1}]), MANAGER, tag, "test"
    )
    assert result.data == created
    if was_active:
        service.items.update.assert_not_awaited()
        service.repository.deactivate.assert_awaited_once_with(1)
    else:
        service.items.update.assert_awaited_once_with(1, {"is_active": True})
        service.repository.deactivate.assert_not_awaited()
    assert service.mutation.cache.snapshot().by_id[1] == after_item
    assert service.audit.append.await_count == (1 if was_active else 2)


@pytest.mark.parametrize("was_active", [True, False])
# PR-10 F10: kích hoạt version chỉ UPDATE item khi trước đó đang ngừng.
async def test_activate_version_updates_only_stopped_item(bom_service, was_active):
    service = bom_service
    before_item = item(loai_mat_hang="thanh_pham").model_copy(update={"is_active": was_active})
    target, current = version(active=False), version(2, active=was_active)
    before = BomContext(before_item, (target, current))
    after_item = before_item.model_copy(update={"is_active": True})
    after = BomContext(after_item, (version(), version(2, active=False)))
    service.repository.context_for_bom.return_value = before
    _, tag = await service.get_bom(1, MANAGER, "test")
    service.repository.context_for_bom.side_effect = [before, before, after]
    result, _ = await service.activate_bom(1, MANAGER, tag, "test")
    assert result.data.is_active
    if was_active:
        service.items.update.assert_not_awaited()
    else:
        service.items.update.assert_awaited_once_with(1, {"is_active": True})
    assert service.mutation.cache.snapshot().by_id[1] == after_item
