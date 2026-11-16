"""Catalog UC/AC policies independent of HTTP and PostgreSQL."""

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from app.core.errors import ConflictException, ForbiddenException, InvalidInputException
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.mutation import MatHangMutation
from app.modules.mat_hang.ports import ItemReferences
from app.modules.mat_hang.schemas import MatHangListQuery, MatHangPatch, MatHangRead
from app.modules.mat_hang.service import MatHangReader, MatHangService
from app.modules.nha_cung_cap.schemas import NhaCungCapCreate, NhaCungCapListQuery, NhaCungCapPatch
from app.modules.nha_cung_cap.service import SupplierService

MANAGER = {"sub": "1", "roles": ["quan_ly"]}
SUPPLIER = dict(
    ten_ncc="  Vendor  ",
    so_dien_thoai="phone",
    dia_chi="address",
    phuong=" Ward ",
    tinh=" Province ",
)


def item(record_id=1, **values):
    return MatHangRead(
        id=record_id,
        ma_mat_hang=f"MH-{record_id:06}",
        ten_mat_hang=values.pop("ten_mat_hang", "Frame"),
        sku="secret-sku",
        loai_mat_hang=values.pop("loai_mat_hang", "linh_kien"),
        don_vi_tinh="chiec",
        mau_sac=None,
        mo_ta=None,
        don_gia=100,
        is_active=True,
        so_luong_ton=10,
        so_luong_dang_giu=3,
        so_luong_con_dung=7,
        ton_kho_updated_at=None,
        **values,
    )


@pytest.mark.parametrize("role", ["quan_tri_vien", "quan_ly", "nhan_vien"])
async def test_uc09_ac01_reader_roles(role):
    cache = MatHangCache()
    cache.replace([item()])
    reader = MatHangReader(cache, AsyncMock())
    result = await reader.danh_muc({"roles": [role]})
    assert result.data[0].so_luong_con_dung == 7


@pytest.mark.parametrize("roles", [[], "quan_ly", ["invalid"]])
async def test_cat_ac01_service_read_guard_before_io(roles):
    cache = Mock()
    reader = MatHangReader(cache, AsyncMock())
    with pytest.raises(ForbiddenException):
        await reader.list_mat_hang(MatHangListQuery(), {"roles": roles})
    cache.snapshot.assert_not_called()


@pytest.mark.parametrize(
    "q,expected", [("FRAME", [1]), ("%_", [2]), ("secret-sku", []), (" ", [1, 2])]
)
async def test_uc09_cat_ac03_literal_code_name_only(q, expected):
    cache = MatHangCache()
    cache.replace([item(), item(2, ten_mat_hang="Bike %_ name", loai_mat_hang="thanh_pham")])
    result = await MatHangReader(cache, AsyncMock()).list_mat_hang(MatHangListQuery(q=q), MANAGER)
    assert [v.id for v in result.data] == expected


async def test_uc09_cat_ac03_active_applies_only_to_finished_items():
    cache = MatHangCache()
    cache.replace([item(), item(2, loai_mat_hang="thanh_pham")])
    reader = MatHangReader(cache, AsyncMock())
    result = await reader.list_mat_hang(MatHangListQuery(is_active=True), MANAGER)
    assert [v.id for v in result.data] == [2]
    with pytest.raises(InvalidInputException):
        await reader.list_mat_hang(
            MatHangListQuery(is_active=False, loai_mat_hang="linh_kien"), MANAGER
        )


async def test_uc09_ac04_ac05_combined_filters_stable_pages():
    cache = MatHangCache()
    cache.replace([item(3), item(1), item(2, ten_mat_hang="Different")])
    reader = MatHangReader(cache, AsyncMock())
    ids = []
    for page in [1, 2, 3]:
        result = await reader.list_mat_hang(
            MatHangListQuery(
                q="frame",
                loai_mat_hang="linh_kien",
                don_vi_tinh="chiec",
                don_gia_min=100,
                don_gia_max=100,
                sort="-don_gia",
                page=page,
                page_size=1,
            ),
            MANAGER,
        )
        assert result.meta.total == 2 and result.meta.total_pages == 2
        ids.extend(v.id for v in result.data)
    assert ids == [1, 3]
    empty = await reader.list_mat_hang(MatHangListQuery(mau_sac="do"), MANAGER)
    assert not empty.data and empty.meta.total == 0


@pytest.mark.parametrize("schema", [NhaCungCapCreate, NhaCungCapPatch])
@pytest.mark.parametrize("field", list(SUPPLIER))
@pytest.mark.parametrize("bad", [None, "", " \t "])
def test_uc14_uc44_cat_ac02_reject_missing_information(schema, field, bad):
    with pytest.raises(ValidationError):
        schema.model_validate({**SUPPLIER, field: bad})


def test_uc14_ac04_preserve_raw_text_and_uc13_normalize_filters():
    assert NhaCungCapCreate(**SUPPLIER).model_dump() == SUPPLIER
    assert NhaCungCapListQuery(q=" ", tinh=" Province ").model_dump()["tinh"] == "Province"
    assert NhaCungCapListQuery(q=" ").q is None
    assert NhaCungCapPatch().model_dump(exclude_unset=True) == {}


@pytest.mark.parametrize(
    "method,args",
    [
        ("list_suppliers", (NhaCungCapListQuery(), {"roles": ["nhan_vien"]}, "r")),
        ("get_supplier", (1, {"roles": ["nhan_vien"]}, "r")),
        ("create_supplier", (NhaCungCapCreate(**SUPPLIER), {"roles": ["quan_tri_vien"]}, "r")),
        ("patch_supplier", (1, NhaCungCapPatch(), {"roles": ["quan_tri_vien"]}, None, "r")),
    ],
)
async def test_uc13_uc14_uc44_cat_ac01_service_guard(method, args):
    repo, audit, transaction = AsyncMock(), AsyncMock(), AsyncMock()
    with pytest.raises(ForbiddenException):
        await getattr(SupplierService(repo, audit, transaction), method)(*args)
    assert not repo.mock_calls and not audit.mock_calls and not transaction.mock_calls


@pytest.fixture
def patch_service():
    before = item(loai_mat_hang="thanh_pham")
    repository, audit, boms = AsyncMock(), AsyncMock(), AsyncMock()
    # main (PR 9): _locked_item lấy record và tag qua BomService.lock_item.
    boms.lock_item.return_value = (before, '"current"')
    repository.find_duplicate.return_value = False
    repository.get_references.return_value = ItemReferences(False, False, False)
    boms.item_detail.return_value = (before, '"current"')
    cache = MatHangCache()
    cache.replace([before])
    service = MatHangService(repository, audit, MatHangMutation(AsyncMock(), cache), boms)
    return service, before


@pytest.mark.parametrize("has_bom,has_docs", [(False, False), (True, False), (False, True)])
# PR-10 F4/D2: chỉ thành phần công thức/chứng từ khóa đơn vị tính, tồn kho không khóa.
async def test_finished_item_unit_reference_policy(patch_service, has_bom, has_docs):
    service, before = patch_service
    service.repository.get_references.return_value = ItemReferences(has_bom, has_docs, True)
    after = before.model_copy(update={"don_vi_tinh": "bo"})
    service.repository.update.return_value = after
    if has_bom or has_docs:
        with pytest.raises(ConflictException, match="Unit cannot change after a reference"):
            await service.patch_mat_hang(1, MatHangPatch(don_vi_tinh="bo"), '"current"', MANAGER)
        service.repository.update.assert_not_awaited()
        service.audit.append.assert_not_awaited()
    else:
        service.boms.item_detail.return_value = (after, '"after"')
        result, _ = await service.patch_mat_hang(
            1, MatHangPatch(don_vi_tinh="bo"), '"current"', MANAGER
        )
        assert result.don_vi_tinh == "bo"
    service.repository.get_references.assert_awaited_once_with(1)


@pytest.mark.parametrize(
    "values,reference_calls",
    [
        ({"sku": "new", "don_vi_tinh": "bo"}, 1),
        ({"don_gia": 200}, 0),
        ({"sku": "secret-sku", "don_vi_tinh": "chiec"}, 0),
    ],
)
# PR-10 F7/F10: dùng chung references; audit sửa thường dùng before, không đọc lại previous.
async def test_patch_reads_only_required_snapshots(patch_service, values, reference_calls):
    service, before = patch_service
    after = before.model_copy(update=values)
    service.repository.update.return_value = after
    service.boms.item_detail.return_value = (after, '"after"')
    await service.patch_mat_hang(1, MatHangPatch(**values), '"current"', MANAGER)
    assert service.repository.get_references.await_count == reference_calls
    assert service.boms.item_detail.await_count == 1
    if after != before:
        entry = service.audit.append.call_args.args[0]
        assert entry.du_lieu_truoc == before.model_dump(mode="json")
    else:
        service.repository.update.assert_not_awaited()
        service.audit.append.assert_not_awaited()


@pytest.mark.parametrize(
    "has_bom,has_docs,has_stock",
    [(True, False, False), (False, True, False), (False, False, True)],
)
# PR-10 F4/D2: SKU vẫn bị khóa bởi bất kỳ tham chiếu hoặc tồn kho nào.
async def test_sku_remains_locked_by_any_reference(patch_service, has_bom, has_docs, has_stock):
    service, _ = patch_service
    service.repository.get_references.return_value = ItemReferences(has_bom, has_docs, has_stock)
    with pytest.raises(ConflictException, match="SKU cannot change"):
        await service.patch_mat_hang(1, MatHangPatch(sku="new"), '"current"', MANAGER)
    service.repository.get_references.assert_awaited_once_with(1)
    service.repository.update.assert_not_awaited()
    service.audit.append.assert_not_awaited()


@pytest.mark.parametrize("was_active", [True, False])
# PR-10 F7: audit sửa sau stop/reuse phải lấy trạng thái mới làm previous.
async def test_patch_state_and_description_refreshes_previous(patch_service, was_active):
    service, original = patch_service
    before = original.model_copy(update={"is_active": was_active})
    previous = before.model_copy(update={"is_active": not was_active})
    after = previous.model_copy(update={"don_gia": 200})
    service.boms.lock_item.return_value = (before, '"current"')
    service.repository.update.return_value = after
    service.boms.item_detail.side_effect = [
        (previous, '"state"'),
        (after, '"after"'),
    ]
    await service.patch_mat_hang(
        1, MatHangPatch(is_active=not was_active, don_gia=200), '"current"', MANAGER
    )
    assert service.boms.item_detail.await_count == 2
    lifecycle = (
        service.boms.stop_for_item_in_transaction
        if was_active
        else service.boms.reuse_last_for_item_in_transaction
    )
    lifecycle.assert_awaited_once_with(1, MANAGER)
    entry = service.audit.append.call_args.args[0]
    assert entry.du_lieu_truoc == previous.model_dump(mode="json")
    service.repository.get_references.assert_not_awaited()
