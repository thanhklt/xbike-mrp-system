"""UC-32 service and ASGI contracts with transactional in-memory repositories."""

from copy import deepcopy
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.errors import ForbiddenException
from app.modules.inventory.ports import InventoryProductionWriter
from app.modules.san_xuat.schemas import ChungTuRead
from app.modules.san_xuat.service.chung_tu_hoan_thanh_sx import generate_chung_tu_etag
from tests import test_uc30_chung_tu_hoan_thanh as uc30

completion_api = uc30.api
URL = uc30.URL
REASON = "Số lượng thực tế chưa đạt"


@pytest.fixture
def api(completion_api):
    completion_api.data["completion"] = ChungTuRead(
        id=12, ma_phieu="HTSX-202611-000012", yeu_cau_san_xuat_id=1,
        so_luong_hoan_thanh=7, nhan_vien_id=20, trang_thai="cho_duyet",
        finish_time=uc30.NOW, created_at=uc30.NOW, updated_at=uc30.NOW,
        phien_ban=2, nguoi_xu_ly_id=None, xu_ly_at=None, ly_do_tu_choi=None,
    )
    completion_api.data["stock"].update({2: 86, 9: 79})
    completion_api.data["held"].update({2: 0, 9: 0})
    completion_api.inventory = AsyncMock(spec=InventoryProductionWriter)
    completion_api.service.inventory = completion_api.inventory
    return completion_api


async def reject(api, **headers):
    return await api.client.post(f"{URL}/12/tu_choi", json={"ly_do": f"  {REASON}  "}, headers={
        "x-role": "quan_ly", "x-user": "10",
        "If-Match": generate_chung_tu_etag(api.data["completion"]), **headers,
    })


def assert_no_writes(api, before):
    assert api.data == before
    api.repo.update.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    assert api.inventory.mock_calls == []
    api.session.commit.assert_not_awaited()


@pytest.mark.parametrize("payload", [{}, {"ly_do": ""}, {"ly_do": " \t\n "}])
# UC-32 AC-1: Thiếu, rỗng hoặc chỉ khoảng trắng bị 422; giữ Chờ duyệt và không lịch sử
async def test_reason_is_required_without_any_write(api, payload):
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/12/tu_choi", json=payload, headers={
        "x-role": "quan_ly", "If-Match": generate_chung_tu_etag(before["completion"]),
    })
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    assert response.json()["error"]["details"][0]["field"] == "ly_do"
    assert_no_writes(api, before)
    api.repo.get_for_update.assert_not_awaited()


@pytest.mark.parametrize("kind", ["xuat_giao", "nhap_kho"])
# UC-32 AC-2: Từ chối giữ nguyên tồn thành phẩm, linh kiện, giữ hàng, sổ kho và yêu cầu
async def test_reject_changes_only_completion_and_audit(api, kind):
    api.data["request"] = api.data["request"].model_copy(update={"loai_yeu_cau": kind})
    before = deepcopy(api.data)
    response = await reject(api)
    assert response.status_code == 200, response.text
    after = api.data["completion"]
    assert after == before["completion"].model_copy(update={
        "trang_thai": "tu_choi", "ly_do_tu_choi": REASON, "nguoi_xu_ly_id": 10,
        "xu_ly_at": uc30.CONFIRMED_AT, "updated_at": uc30.CONFIRMED_AT, "phien_ban": 3,
    })
    assert response.json()["data"] == after.model_dump(mode="json")
    assert set(response.json()) == {"data", "meta"}
    assert response.json()["meta"]["request_id"]
    assert response.headers["etag"] == generate_chung_tu_etag(after)
    assert response.headers["etag"] != generate_chung_tu_etag(before["completion"])
    for key in ("stock", "held", "holds", "ledger", "request"):
        assert api.data[key] == before[key]
    assert api.inventory.mock_calls == []
    api.repo.lock_product.assert_not_awaited()
    api.repo.hold_production.assert_not_awaited()
    api.requests.update.assert_not_awaited()
    assert api.events == ["lock_request", "lock_completion"]
    api.repo.update.assert_awaited_once_with(12, {
        "trang_thai": "tu_choi", "ly_do_tu_choi": REASON,
        "nguoi_xu_ly_id": 10, "xu_ly_at": uc30.CONFIRMED_AT,
    })
    api.session.commit.assert_awaited_once()
    api.session.rollback.assert_not_awaited()


# UC-32 Main 4: Đúng một lịch sử từ chối có lý do, người xử lý và snapshot trước/sau
async def test_rejection_history_has_reason_actor_and_exact_transition(api):
    before = api.data["completion"].model_dump(mode="json")
    assert (await reject(api)).status_code == 200
    api.audit.append.assert_awaited_once()
    assert len(api.data["history"]) == 1
    entry = api.data["history"][0]
    assert entry.model_dump() == {
        "nhan_vien_id": 10, "loai_doi_tuong": "chung_tu_hoan_thanh_san_xuat",
        "doi_tuong_id": 12, "thao_tac": "tu_choi", "ly_do": REASON,
        "trang_thai_truoc": "cho_duyet", "trang_thai_sau": "tu_choi",
        "du_lieu_truoc": before,
        "du_lieu_sau": api.data["completion"].model_dump(mode="json"),
    }


# UC-32 AC-3: NV thấy lý do, gửi lại trực tiếp sang Chờ duyệt và không có endpoint về nháp
async def test_employee_reads_reason_and_resends_without_return_to_draft(api):
    before = deepcopy(api.data)
    assert (await reject(api)).status_code == 200
    response = await api.client.get(f"{URL}/12")
    assert response.status_code == 200
    assert response.json()["data"]["trang_thai"] == "tu_choi"
    assert response.json()["data"]["ly_do_tu_choi"] == REASON
    for method in ("GET", "POST", "PATCH", "DELETE"):
        missing = await api.client.request(method, f"{URL}/12/ve_nhap", json={})
        assert missing.status_code == 404
    assert api.data["completion"].trang_thai == "tu_choi"
    resent = await api.client.post(f"{URL}/12/gui", json={}, headers={
        "If-Match": response.headers["etag"],
    })
    assert resent.status_code == 200, resent.text
    document = resent.json()["data"]
    assert document["trang_thai"] == "cho_duyet" and document["phien_ban"] == 4
    assert document["ly_do_tu_choi"] is document["nguoi_xu_ly_id"] is document["xu_ly_at"] is None
    assert document["finish_time"] == uc30.CONFIRMED_AT.isoformat().replace("+00:00", "Z")
    assert [(entry.thao_tac, entry.trang_thai_truoc, entry.trang_thai_sau)
            for entry in api.data["history"]] == [
        ("tu_choi", "cho_duyet", "tu_choi"), ("gui_lai", "tu_choi", "cho_duyet"),
    ]
    assert api.data["history"][0].ly_do == REASON
    for key in ("stock", "held", "holds", "ledger", "request"):
        assert api.data[key] == before[key]


@pytest.mark.parametrize("status", ["da_duyet", "tu_choi"])
# UC-32 A2: Chứng từ ngoài Chờ duyệt bị 409 Chứng từ đã thay đổi, không ghi dữ liệu
# UC-33 D4: Tách Nháp khỏi nhóm 409, Nháp có kiểm thử 404 riêng
async def test_changed_document_state_is_conflict(api, status):
    api.data["completion"] = api.data["completion"].model_copy(update={"trang_thai": status})
    before = deepcopy(api.data)
    response = await reject(api)
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Chứng từ đã thay đổi"
    assert_no_writes(api, before)
    api.session.rollback.assert_awaited_once()


@pytest.mark.parametrize("etag", [None, "", '"old"', "current"])
# UC-33 D4: Từ chối Nháp trả 404 sau khóa trước If-Match, giữ nguyên mọi dữ liệu
async def test_draft_rejection_is_hidden_before_if_match(api, etag, monkeypatch):
    api.data["completion"] = api.data["completion"].model_copy(update={"trang_thai": "nhap"})
    before = deepcopy(api.data)
    if etag == "current":
        etag = generate_chung_tu_etag(before["completion"])
    monkeypatch.setattr(uc30.completion_service, "generate_chung_tu_etag", Mock(side_effect=AssertionError("Must not check ETag")))
    headers = {"x-role": "quan_ly"}
    if etag is not None:
        headers["If-Match"] = etag
    response = await api.client.post(f"{URL}/12/tu_choi", json={"ly_do": REASON}, headers=headers)
    assert response.status_code == 404
    assert api.events == ["lock_request", "lock_completion"]
    assert_no_writes(api, before)
    api.session.rollback.assert_awaited_once()


@pytest.mark.parametrize("etag,expected", [(None, 428), (" ", 428), ('"old"', 412)])
# UC-32 A2: Thiếu If-Match bị 428; ETag cũ bị 412, không ghi dữ liệu
async def test_reject_requires_current_completion_etag(api, etag, expected):
    before = deepcopy(api.data)
    headers = {"x-role": "quan_ly"}
    if etag is not None:
        headers["If-Match"] = etag
    response = await api.client.post(f"{URL}/12/tu_choi", json={"ly_do": REASON}, headers=headers)
    assert response.status_code == expected
    if expected == 412:
        assert response.json()["error"]["message"] == "Chứng từ đã thay đổi"
    assert_no_writes(api, before)
    api.session.rollback.assert_awaited_once()


# UC-32 A2: QLK thứ hai không thể từ chối lại bằng ETag cũ hoặc mới
async def test_second_manager_cannot_reject_processed_document(api):
    old = generate_chung_tu_etag(api.data["completion"])
    assert (await reject(api)).status_code == 200
    rejected = deepcopy(api.data)
    for etag, expected in [(old, 412), (generate_chung_tu_etag(api.data["completion"]), 409)]:
        response = await reject(api, **{"x-user": "11", "If-Match": etag})
        assert response.status_code == expected
        assert response.json()["error"]["message"] == "Chứng từ đã thay đổi"
        assert api.data == rejected
    assert api.repo.update.await_count == api.audit.append.await_count == 1


@pytest.mark.parametrize("status", ["hoan_thanh", "da_huy"])
# UC-32 R2: Không đòi yêu cầu còn Đang thực hiện vì từ chối không thay đổi kho
async def test_rejection_does_not_require_active_request(api, status):
    api.data["request"] = api.data["request"].model_copy(update={"trang_thai": status})
    before = api.data["request"].model_copy(deep=True)
    assert (await reject(api)).status_code == 200
    assert api.data["completion"].trang_thai == "tu_choi"
    assert api.data["request"] == before
    assert api.inventory.mock_calls == []


# UC-32 Main 4: NV bị 403 ở cả router và service, không ghi dữ liệu
async def test_employee_is_forbidden_in_api_and_service(api):
    before = deepcopy(api.data)
    response = await reject(api, **{"x-role": "nhan_vien", "x-user": "20"})
    assert response.status_code == 403
    with pytest.raises(ForbiddenException):
        await api.service.tu_choi(12, REASON, uc30.EMPLOYEE,
                                 generate_chung_tu_etag(before["completion"]), "test")
    assert_no_writes(api, before)
    api.requests.get_for_update.assert_not_awaited()


# UC-32 Main 4: Audit lỗi sau cập nhật phải rollback; chứng từ vẫn Chờ duyệt, không lịch sử
async def test_audit_failure_rolls_back_rejection(api):
    before = deepcopy(api.data)
    append = api.audit.append.side_effect

    async def fail_after_append(entry):
        await append(entry)
        raise RuntimeError("audit failed")

    api.audit.append.side_effect = fail_after_append
    response = await reject(api)
    assert response.status_code == 500
    api.repo.update.assert_awaited_once()
    api.audit.append.assert_awaited_once()
    api.session.rollback.assert_awaited_once()
    api.session.commit.assert_not_awaited()
    assert api.data == before
    assert api.data["completion"].trang_thai == "cho_duyet"
    assert api.data["history"] == []
    assert api.inventory.mock_calls == []
