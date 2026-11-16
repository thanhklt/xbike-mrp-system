"""UC-24: draft edits, deletion and sending through stateful ports and ASGI."""

from unittest.mock import call

import pytest
from test_uc23_lap_gui_yeu_cau_san_xuat import (
    BODY,
    EMPLOYEE,
    MANAGER,
    URL,
    assert_stock_untouched,
    create,
    send,
)
from test_uc23_lap_gui_yeu_cau_san_xuat import (
    api as api,
)

from app.core.errors import ForbiddenException
from app.modules.san_xuat.ports import YeuCauSanXuatRepository
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.schemas import YeuCauPatch, YeuCauRead
from app.modules.san_xuat.service import generate_yeu_cau_etag

PATCH_BODY = {"loai_yeu_cau": "xuat_giao", **BODY}


@pytest.fixture(autouse=True)
async def transactional_deletion(api):
    deleted = set()
    commit = api.session.commit.side_effect
    rollback = api.session.rollback.side_effect

    async def delete(request_id):
        deleted.add(request_id)

    async def commit_with_deletes():
        await commit()
        for request_id in deleted:
            del api.stored[request_id]
        deleted.clear()

    async def rollback_with_deletes():
        await rollback()
        deleted.clear()

    api.repo.delete.side_effect = delete
    api.session.commit.side_effect = commit_with_deletes
    api.session.rollback.side_effect = rollback_with_deletes


async def patch(api, response, **changes):
    return await api.client.patch(
        f"{URL}/1", json={**PATCH_BODY, **changes},
        headers={"If-Match": response.headers["etag"]},
    )


def assert_unchanged(api, before, history):
    assert api.stored == {1: before}
    assert api.history == history
    assert api.pending == {} and api.pending_history == []
    assert_stock_untouched(api)


# UC-24 AC-1: Sửa số lượng vẫn Nháp, tăng phiên bản, ghi đúng lịch sử và không đổi tồn/giữ
async def test_patch_quantity_keeps_draft_and_audits_old_new_values(api):
    created = await create(api)
    before = YeuCauRead.model_validate(created.json()["data"])
    response = await patch(api, created, so_luong=15)
    assert response.status_code == 200, response.text
    after = api.stored[1].model_copy(update={"so_luong_con_phai_xuat": 15})
    assert response.json()["data"] == after.model_dump(mode="json")
    assert after.trang_thai == "nhap" and after.so_luong == 15
    assert after.bom_id is None and after.gui_at is None
    assert after.phien_ban == before.phien_ban + 1
    assert after.updated_at >= before.updated_at
    assert response.headers["etag"] == generate_yeu_cau_etag(after)
    assert response.headers["etag"] != created.headers["etag"]
    assert [entry.thao_tac for entry in api.history] == ["tao", "sua"]
    entry = api.history[1]
    assert (entry.trang_thai_truoc, entry.trang_thai_sau) == ("nhap", "nhap")
    assert entry.du_lieu_truoc == before.model_dump(mode="json")
    assert entry.du_lieu_sau == after.model_dump(mode="json")
    assert entry.du_lieu_truoc["so_luong"] == 10 and entry.du_lieu_sau["so_luong"] == 15
    assert entry.nhan_vien_id == 10 and entry.doi_tuong_id == 1
    assert entry.loai_doi_tuong == "yeu_cau_san_xuat" and entry.created_at.tzinfo is not None
    api.repo.bom_dang_dung.assert_not_awaited()
    api.item_repo.lock_items.assert_has_awaits([call({1}), call({1})])
    api.employee_repo.get_for_share.assert_has_awaits([call(20), call(20)])
    assert_stock_untouched(api)


# UC-24 AC-1: Nháp đổi được loại xuat_giao sang nhap_kho qua service (R2)
async def test_patch_request_type_through_service(api):
    created = await create(api)
    detail, etag = await api.service.patch_entry(
        1, YeuCauPatch(**{**PATCH_BODY, "loai_yeu_cau": "nhap_kho"}),
        MANAGER, created.headers["etag"], "uc24",
    )
    assert detail.data == api.stored[1].model_copy(update={"so_luong_con_phai_xuat": 10})
    assert detail.data.loai_yeu_cau == "nhap_kho" and detail.data.trang_thai == "nhap"
    assert etag == generate_yeu_cau_etag(detail.data)
    assert api.history[-1].du_lieu_truoc["loai_yeu_cau"] == "xuat_giao"
    assert api.history[-1].du_lieu_sau["loai_yeu_cau"] == "nhap_kho"
    assert_stock_untouched(api)


# UC-24 AC-2: Cả năm trường thiếu hoặc null đều 422, giữ nguyên bản ghi và lịch sử (D4)
@pytest.mark.parametrize("field", list(PATCH_BODY))
@pytest.mark.parametrize("null", [False, True])
async def test_patch_missing_or_null_field_preserves_draft(api, field, null):
    created = await create(api)
    before, history = api.stored[1], list(api.history)
    body = dict(PATCH_BODY)
    if null:
        body[field] = None
    else:
        del body[field]
    response = await api.client.patch(
        f"{URL}/1", json=body, headers={"If-Match": created.headers["etag"]},
    )
    assert response.status_code == 422
    assert any(detail["field"] == field for detail in response.json()["error"]["details"])
    api.repo.update.assert_not_awaited()
    assert_unchanged(api, before, history)


# UC-24 A1: PATCH chỉ số lượng hoặc có trường lạ bị từ chối, không cập nhật (D4)
@pytest.mark.parametrize("body", [{"so_luong": 15}, {**PATCH_BODY, "trang_thai": "da_gui"}])
async def test_partial_or_extra_patch_is_rejected(api, body):
    created = await create(api)
    before, history = api.stored[1], list(api.history)
    response = await api.client.patch(
        f"{URL}/1", json=body, headers={"If-Match": created.headers["etag"]},
    )
    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    expected = set(PATCH_BODY) - {"so_luong"} if len(body) == 1 else {"trang_thai"}
    assert fields == expected
    api.repo.update.assert_not_awaited()
    assert_unchanged(api, before, history)


# UC-24 A1: Chỉ chọn thành phẩm và nhân viên đang hoạt động khi sửa (R2)
@pytest.mark.parametrize("changes,status,code", [
    ({"mat_hang_id": 3}, 409, "mat_hang_ngung_hoat_dong"),
    ({"mat_hang_id": 2}, 422, "du_lieu_khong_hop_le"),
    ({"nhan_vien_duoc_giao_id": 21}, 409, "nguoi_duoc_giao_khong_hop_le"),
])
async def test_patch_invalid_product_or_assignee_preserves_draft(api, changes, status, code):
    created = await create(api)
    before, history = api.stored[1], list(api.history)
    response = await patch(api, created, **changes)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    api.repo.update.assert_not_awaited()
    assert_unchanged(api, before, history)


# UC-24 AC-3: Xóa Nháp 204, audit nhap sang null, không còn kiểm phụ thuộc (A2)
async def test_delete_draft_records_snapshot_without_dependency_check(api):
    created = await create(api)
    before = YeuCauRead.model_validate(created.json()["data"])
    response = await api.client.delete(f"{URL}/1", headers={"If-Match": created.headers["etag"]})
    assert response.status_code == 204 and response.content == b""
    assert api.stored == {} and api.pending == {}
    assert (await api.client.get(f"{URL}/1")).status_code == 404
    assert [entry.thao_tac for entry in api.history] == ["tao", "xoa_nhap"]
    entry = api.history[1]
    assert (entry.trang_thai_truoc, entry.trang_thai_sau) == ("nhap", None)
    assert entry.du_lieu_truoc == before.model_dump(mode="json") and entry.du_lieu_sau == {}
    assert entry.nhan_vien_id == 10 and entry.doi_tuong_id == 1
    assert entry.loai_doi_tuong == "yeu_cau_san_xuat" and entry.created_at.tzinfo is not None
    assert not hasattr(YeuCauSanXuatRepository, "has_dependencies")
    assert not hasattr(SqlAlchemyYeuCauSanXuatRepository, "has_dependencies")
    api.repo.delete.assert_awaited_once_with(1)
    assert_stock_untouched(api)


# UC-24 AC-4: Nháp đã sửa gửi bằng ETag mới, chốt BOM hiện hành, NV thấy, tồn/giữ không đổi
async def test_send_edited_draft_freezes_bom_and_employee_can_see(api):
    created = await create(api)
    edited = await patch(api, created, so_luong=15)
    assert edited.status_code == 200
    api.boms[1] = {"id": 103, "phien_ban": 3}
    sent = await send(api, edited)
    assert sent.status_code == 200, sent.text
    after = api.stored[1]
    assert after.trang_thai == "da_gui" and after.so_luong == 15 and after.bom_id == 103
    assert after.gui_at is not None and after.phien_ban == 3
    assert after.so_luong_dung_thanh_pham is None and after.so_luong_can_san_xuat is None
    assert after.kiem_tra_lan_dau_at is None
    assert [entry.thao_tac for entry in api.history] == ["tao", "sua", "gui"]
    assert (api.history[-1].trang_thai_truoc, api.history[-1].trang_thai_sau) == ("nhap", "da_gui")
    headers = {"x-role": "nhan_vien", "x-actor": "20"}
    listing = await api.client.get(URL, headers=headers)
    assert listing.status_code == 200 and listing.json()["data"] == [sent.json()["data"]]
    detail = await api.client.get(f"{URL}/1", headers=headers)
    assert detail.status_code == 200 and detail.json()["data"] == sent.json()["data"]
    assert_stock_untouched(api)


# UC-24 AC-5: Nhân viên A bị khóa thì gửi lỗi, đổi sang NV hoạt động rồi gửi được (A4)
async def test_locked_assignee_can_be_replaced_before_resending(api):
    created = await create(api)
    before, history = api.stored[1], list(api.history)
    api.employees[20].trang_thai = "bi_khoa"
    rejected = await send(api, created)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "nguoi_duoc_giao_khong_hop_le"
    assert "bị khóa" in rejected.json()["error"]["message"]
    assert_unchanged(api, before, history)
    edited = await patch(api, created, nhan_vien_duoc_giao_id=22)
    assert edited.status_code == 200
    sent = await send(api, edited)
    assert sent.status_code == 200
    assert api.stored[1].trang_thai == "da_gui" and api.stored[1].nhan_vien_duoc_giao_id == 22
    visible = await api.client.get(URL, headers={"x-role": "nhan_vien", "x-actor": "22"})
    assert visible.status_code == 200 and [row["id"] for row in visible.json()["data"]] == [1]
    assert [entry.thao_tac for entry in api.history] == ["tao", "sua", "gui"]
    assert_stock_untouched(api)


# UC-24 AC-6: Kids Fun ngừng sau tạo thì gửi lỗi, vẫn xóa nháp được (A4)
async def test_deactivated_kids_fun_cannot_send_but_can_delete(api):
    api.products[3] = api.products[3].model_copy(update={"is_active": True})
    created = await create(api, mat_hang_id=3)
    before, history = api.stored[1], list(api.history)
    api.products[3] = api.products[3].model_copy(update={"is_active": False})
    rejected = await send(api, created)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert "ngừng hoạt động" in rejected.json()["error"]["message"]
    assert_unchanged(api, before, history)
    deleted = await api.client.delete(f"{URL}/1", headers={"If-Match": created.headers["etag"]})
    assert deleted.status_code == 204 and api.stored == {}
    assert [entry.thao_tac for entry in api.history] == ["tao", "xoa_nhap"]
    api.repo.bom_dang_dung.assert_not_awaited()
    assert_stock_untouched(api)


# UC-24 AC-7: Đã gửi không sửa bất kỳ trường nào và không xóa, giữ nguyên dữ liệu/lịch sử
@pytest.mark.parametrize("changes", [
    {"nhan_vien_duoc_giao_id": 22}, {"so_luong": 15}, {"mat_hang_id": 3},
    {"loai_yeu_cau": "nhap_kho"}, {"han_hoan_thanh": "2027-01-01"}, None,
])
async def test_sent_request_rejects_each_field_edit_and_deletion(api, changes):
    sent = await send(api, await create(api))
    assert sent.status_code == 200
    before, history = api.stored[1], list(api.history)
    api.repo.update.reset_mock()
    if changes is None:
        response = await api.client.delete(f"{URL}/1", headers={"If-Match": sent.headers["etag"]})
    else:
        response = await patch(api, sent, **changes)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    api.repo.update.assert_not_awaited()
    api.repo.delete.assert_not_awaited()
    assert_unchanged(api, before, history)


# UC-24 A5: Sửa/xóa/gửi với ETag cũ hoặc thiếu If-Match không ghi thêm dữ liệu/lịch sử (R9)
@pytest.mark.parametrize("action", ["patch", "delete", "send"])
@pytest.mark.parametrize("stale", [True, False])
async def test_stale_or_missing_etag_preserves_latest_draft(api, action, stale):
    created = await create(api)
    edited = await patch(api, created, so_luong=15)
    assert edited.status_code == 200 and edited.headers["etag"] != created.headers["etag"]
    before, history = api.stored[1], list(api.history)
    headers = {"If-Match": created.headers["etag"]} if stale else {}
    api.repo.update.reset_mock()
    if action == "patch":
        response = await api.client.patch(f"{URL}/1", json=PATCH_BODY, headers=headers)
    elif action == "delete":
        response = await api.client.delete(f"{URL}/1", headers=headers)
    else:
        response = await api.client.post(f"{URL}/1/gui", json={}, headers=headers)
    assert response.status_code == (412 if stale else 428)
    assert response.json()["error"]["code"] == ("du_lieu_da_thay_doi" if stale else "thieu_if_match")
    api.repo.update.assert_not_awaited()
    api.repo.delete.assert_not_awaited()
    assert_unchanged(api, before, history)


# UC-24 A1: NV không có quyền sửa/xóa Nháp qua API hoặc gọi service trực tiếp
@pytest.mark.parametrize("action", ["patch", "delete"])
async def test_employee_cannot_edit_or_delete_draft(api, action):
    created = await create(api)
    before, history = api.stored[1], list(api.history)
    etag = created.headers["etag"]
    headers = {"If-Match": etag, "x-role": "nhan_vien", "x-actor": "20"}
    if action == "patch":
        response = await api.client.patch(f"{URL}/1", json=PATCH_BODY, headers=headers)
        with pytest.raises(ForbiddenException):
            await api.service.patch_entry(1, YeuCauPatch(**PATCH_BODY), EMPLOYEE, etag, "uc24")
    else:
        response = await api.client.delete(f"{URL}/1", headers=headers)
        with pytest.raises(ForbiddenException):
            await api.service.delete_entry(1, EMPLOYEE, etag)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    api.repo.update.assert_not_awaited()
    api.repo.delete.assert_not_awaited()
    assert_unchanged(api, before, history)


# UC-24 A1: Audit lỗi khi sửa/xóa phải rollback toàn bộ, Nháp và lịch sử cũ vẫn còn
@pytest.mark.parametrize("action", ["patch", "delete"])
async def test_audit_failure_rolls_back_patch_or_delete(api, action):
    created = await create(api)
    before, history = api.stored[1], list(api.history)
    append = api.audit.append.side_effect

    async def fail_after_append(entry):
        await append(entry)
        raise RuntimeError("audit unavailable")

    api.audit.append.side_effect = fail_after_append
    if action == "patch":
        response = await patch(api, created, so_luong=15)
        api.repo.update.assert_awaited_once()
    else:
        response = await api.client.delete(f"{URL}/1", headers={"If-Match": created.headers["etag"]})
        api.repo.delete.assert_awaited_once_with(1)
    assert response.status_code == 500
    api.session.rollback.assert_awaited_once()
    assert api.session.commit.await_count == 1
    assert_unchanged(api, before, history)
