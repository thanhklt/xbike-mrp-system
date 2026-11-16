"""UC-20 acceptance tests through ASGI with fake repositories, without PostgreSQL."""

from copy import deepcopy

import pytest

from app.modules.phieu_nhap.ports import ReceiptPart

URL = "/api/v1/phieu_nhap"


async def create_draft(api, payload=None):
    response = await api.client.post(URL, json=payload if payload is not None else api.payload)
    assert response.status_code == 201, response.text
    return response


# UC-20 AC-1: Lưu nháp không đổi tồn
async def test_ac1_draft_never_calls_inventory(receipt_api):
    api = receipt_api
    before = deepcopy(api.data)
    response = await create_draft(api)
    assert response.json()["data"]["trang_thai"] == "nhap"
    assert api.data["stock"] == before["stock"]
    assert api.data["ledger"] == before["ledger"]
    assert api.inventory.mock_calls == [] and api.sql_calls == []
    assert api.data["audit"][-1]["thao_tac"] == "tao"


# UC-20 AC-2: Chỉ chọn linh kiện
async def test_ac2_finished_product_is_dependency_conflict(receipt_api):
    api = receipt_api
    api.payload["chi_tiet"][0]["mat_hang_id"] = 3
    before = deepcopy(api.data)
    response = await api.client.post(URL, json=api.payload)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "phu_thuoc_khong_hop_le"
    assert api.data == before
    api.repo.add_draft.assert_not_awaited()


@pytest.mark.parametrize("method", ["post", "patch"])
# UC-20 AC-3: Linh kiện lặp
async def test_ac3_duplicate_lines_are_rejected(receipt_api, method):
    api = receipt_api
    created = await create_draft(api)
    api.payload["chi_tiet"].append(api.payload["chi_tiet"][0].copy())
    before = deepcopy(api.data)
    response = await api.client.request(
        method, URL if method == "post" else created.headers["location"],
        json=api.payload, headers={"If-Match": created.headers["etag"]},
    )
    assert response.status_code == 422, response.text
    assert api.data == before


@pytest.mark.parametrize("method", ["patch", "delete"])
# UC-20 AC-4: Phiếu đã hoàn tất không sửa, xóa được
async def test_ac4_completed_receipt_is_immutable(receipt_api, method):
    api = receipt_api
    created = await create_draft(api)
    path = created.headers["location"]
    completed = await api.client.post(
        path + "/hoan_tat", json={}, headers={"If-Match": created.headers["etag"]},
    )
    assert completed.status_code == 200, completed.text
    before = deepcopy(api.data)
    response = await api.client.request(
        method, path, headers={"If-Match": completed.headers["etag"]},
        **({"json": {"ghi_chu": "Changed"}} if method == "patch" else {}),
    )
    assert response.status_code == 409, response.text
    assert api.data == before
    api.repo.patch_draft.assert_not_awaited()
    api.repo.delete_draft.assert_not_awaited()


# UC-20 AC-5: Ghi lịch sử xóa nháp với người thực hiện và thời điểm
async def test_ac5_delete_audits_actor_time_and_draft_state(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    response = await api.client.delete(
        created.headers["location"], headers={"If-Match": created.headers["etag"]},
    )
    assert response.status_code == 204, response.text
    assert api.data["receipts"] == {}
    entry = api.data["audit"][-1]
    assert entry["thao_tac"] == "xoa_nhap" and entry["nhan_vien_id"] == 10
    assert entry["trang_thai_truoc"] == "nhap" and entry["trang_thai_sau"] is None
    assert entry["created_at"].tzinfo is not None
    # UC-44: nha_cung_cap là thông tin NCC hiện tại, không phải snapshot nên audit không lưu.
    assert entry["du_lieu_truoc"] == {
        key: value for key, value in created.json()["data"].items() if key != "nha_cung_cap"
    }
    assert entry["du_lieu_sau"] is None
    assert api.inventory.mock_calls == []


# UC-20 R6: Review 4, đảo thứ tự dòng không sửa phiếu hay ghi audit
async def test_reordered_lines_preserve_version_etag_and_audit(receipt_api):
    api = receipt_api
    api.payload["chi_tiet"].append({"mat_hang_id": 2, "so_luong": 3, "don_gia_thuc": 200})
    created = await create_draft(api)
    before = deepcopy(api.data)
    response = await api.client.patch(
        created.headers["location"], headers={"If-Match": created.headers["etag"]},
        json={"chi_tiet": list(reversed(api.payload["chi_tiet"]))},
    )
    assert response.status_code == 200, response.text
    assert response.headers["etag"] == created.headers["etag"]
    assert response.json()["data"]["phien_ban"] == 1
    assert response.json()["data"] == created.json()["data"]
    assert api.data == before
    api.repo.patch_draft.assert_not_awaited()
    assert api.audit.append.await_count == 1
    assert api.repo.lock_parts.await_count == 1


# UC-20 R2: Review 5, sửa ghi chú với dòng cũ không kiểm lại linh kiện đã ngừng
async def test_note_change_with_unchanged_inactive_component_succeeds(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    api.data["parts"][1] = ReceiptPart(1, "linh_kien", False)
    response = await api.client.patch(
        created.headers["location"], headers={"If-Match": created.headers["etag"]},
        json={"ghi_chu": "New note", "chi_tiet": api.payload["chi_tiet"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["ghi_chu"] == "New note"
    assert response.json()["data"]["phien_ban"] == 2
    assert response.json()["data"]["chi_tiet"] == created.json()["data"]["chi_tiet"]
    assert api.repo.lock_parts.await_count == 1
    assert api.repo.patch_draft.call_args.args[2] is None
    assert api.data["audit"][-1]["thao_tac"] == "sua"


@pytest.mark.parametrize("operation", ["create", "patch", "complete"])
# UC-20 R2: Review 9, mặt hàng thiếu có cùng lỗi phụ thuộc 409 ở nháp và hoàn tất
async def test_missing_item_has_consistent_dependency_error(receipt_api, operation):
    api = receipt_api
    created = await create_draft(api)
    del api.data["parts"][1]
    before = deepcopy(api.data)
    headers = {"If-Match": created.headers["etag"]}
    if operation == "create":
        response = await api.client.post(URL, json=api.payload)
    elif operation == "patch":
        api.payload["chi_tiet"][0]["so_luong"] = 51
        response = await api.client.patch(created.headers["location"], json=api.payload, headers=headers)
    else:
        response = await api.client.post(created.headers["location"] + "/hoan_tat", json={}, headers=headers)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "phu_thuoc_khong_hop_le"
    assert api.data == before
    api.inventory.receive_receipt.assert_not_awaited()


@pytest.mark.parametrize("corrupt", ["tong_gia", "tong_tien"])
# UC-20 R1: Review 4, so sánh cả tổng dòng và tổng phiếu khi đảo thứ tự
async def test_reordered_lines_repair_inconsistent_amounts(receipt_api, corrupt):
    api = receipt_api
    api.payload["chi_tiet"].append({"mat_hang_id": 2, "so_luong": 3, "don_gia_thuc": 200})
    created = await create_draft(api)
    record = api.data["receipts"][created.json()["data"]["id"]]
    if corrupt == "tong_gia":
        record = record.model_copy(update={"chi_tiet": [
            record.chi_tiet[0].model_copy(update={"tong_gia": 0}), record.chi_tiet[1],
        ]})
    else:
        record = record.model_copy(update={"tong_tien": 0})
    api.data["receipts"][record.id] = record
    tag = api.service.detail_response(record, "")[1]
    response = await api.client.patch(
        created.headers["location"], headers={"If-Match": tag},
        json={"chi_tiet": list(reversed(api.payload["chi_tiet"]))},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["tong_tien"] == 5600
    assert all(line["tong_gia"] == line["so_luong"] * line["don_gia_thuc"]
               for line in response.json()["data"]["chi_tiet"])
    api.repo.patch_draft.assert_awaited_once()
    assert api.repo.lock_parts.await_count == (2 if corrupt == "tong_gia" else 1)
    assert (api.repo.patch_draft.call_args.args[2] is None) == (corrupt == "tong_tien")


# UC-20 R2: Review 5, thay đổi dòng vẫn phải kiểm lại linh kiện đang hoạt động
async def test_changed_line_revalidates_inactive_component(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    api.data["parts"][1] = ReceiptPart(1, "linh_kien", False)
    before = deepcopy(api.data)
    response = await api.client.patch(
        created.headers["location"], headers={"If-Match": created.headers["etag"]},
        json={"chi_tiet": [{"mat_hang_id": 1, "so_luong": 51, "don_gia_thuc": 100}]},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "phu_thuoc_khong_hop_le"
    assert api.data == before
    api.repo.patch_draft.assert_not_awaited()
