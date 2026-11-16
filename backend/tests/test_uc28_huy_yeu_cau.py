"""UC-28: stateful ASGI/service ports and compiled repository SQL; no database."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenException, UnauthorizedException
from app.core.exceptions import register_exception_handlers
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_current_user_payload, get_yeu_cau_san_xuat_service
from app.modules.audit.ports import AuditWriter
from app.modules.phieu_xuat.ports import PhieuXuatRepository, PhieuXuatSnapshot
from app.modules.phieu_xuat.repository import SqlAlchemyPhieuXuatRepository
from app.modules.phieu_xuat.service import PhieuXuatService
from app.modules.san_xuat.ports import YeuCauSanXuatRepository
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.router import yeu_cau_sx_router
from app.modules.san_xuat.schemas import HangTraLine
from app.modules.san_xuat.service.yeu_cau_san_xuat import (
    YeuCauSanXuatService,
    generate_yeu_cau_etag,
)
from tests.test_uc26_kiem_tra_giu_hang import request_record

URL = "/api/v1/yeu_cau_san_xuat"
MANAGER = {"sub": "10", "roles": ["quan_ly"]}
NOW = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)


def hold(id_, item_id, kind, quantity, request_id=1, state="dang_giu"):
    return {
        "id": id_, "yeu_cau_san_xuat_id": request_id, "mat_hang_id": item_id,
        "loai_giu": kind, "so_luong": quantity, "trang_thai": state,
        "ket_thuc_at": None if state == "dang_giu" else NOW,
    }


def issue(id_, kind, state, request_id=1):
    return {
        "id": id_, "ma_phieu_xuat": f"PX-202611-{id_:06d}", "loai_phieu": kind,
        "trang_thai": state, "yeu_cau_san_xuat_id": request_id,
        "nguoi_xu_ly_id": None, "xu_ly_at": None, "ly_do_tu_choi": None,
        "phien_ban": 1,
        "chi_tiet": [{"id": id_ * 10, "mat_hang_id": 2, "so_luong": 10}],
    }


@pytest.fixture
async def api():
    data = {
        "requests": {1: request_record(trang_thai="dang_thuc_hien",
                                      so_luong_dung_thanh_pham=3, so_luong_can_san_xuat=7,
                                      kiem_tra_lan_dau_at=NOW)},
        "stock": {2: 10, 5: 20}, "held": {2: 10, 5: 7},
        "holds": [hold(1, 2, "linh_kien", 10), hold(2, 5, "thanh_pham_co_san", 3),
                  hold(3, 5, "thanh_pham_san_xuat", 2),
                  hold(4, 5, "thanh_pham_co_san", 2, request_id=2),
                  hold(5, 2, "linh_kien", 4, state="da_tra"),
                  hold(6, 2, "linh_kien", 1, state="da_xuat")],
        "issues": {1: issue(1, "xuat_linh_kien", "cho_duyet"),
                   2: issue(2, "xuat_thanh_pham", "nhap"),
                   3: issue(3, "xuat_linh_kien", "tu_choi", request_id=2)},
        "history": [],
    }
    pending = None
    events = []
    repo = AsyncMock(spec=YeuCauSanXuatRepository)
    issues_repo = AsyncMock(spec=PhieuXuatRepository)
    audit, session = AsyncMock(spec=AuditWriter), AsyncMock(spec=AsyncSession)

    def current():
        return data if pending is None else pending

    async def lock_request(id_):
        nonlocal pending
        assert pending is None
        pending = deepcopy(data)
        events.append(("request_lock", id_))
        return current()["requests"].get(id_)

    def active(id_):
        return sorted([row for row in current()["holds"]
                       if row["yeu_cau_san_xuat_id"] == id_ and row["trang_thai"] == "dang_giu"],
                      key=lambda row: (row["mat_hang_id"], row["id"]))

    async def read_holds(id_, *, lock):
        if lock:
            events.append(("hold_lock", id_))
        return [HangTraLine(**{key: row[key] for key in
                              ("id", "mat_hang_id", "loai_giu", "so_luong")},
                            ma_mat_hang=f'MH-{row["mat_hang_id"]:06d}',
                            ten_mat_hang="Khung" if row["mat_hang_id"] == 2 else "Xe",
                            don_vi_tinh="cái" if row["mat_hang_id"] == 2 else "xe")
                for row in active(id_)]

    async def release(id_):
        events.append(("item_lock", sorted({row["mat_hang_id"] for row in active(id_)})))
        rows = await read_holds(id_, lock=True)
        for row in active(id_):
            current()["held"][row["mat_hang_id"]] -= row["so_luong"]
            row.update(trang_thai="da_tra", ket_thuc_at=datetime.now(timezone.utc))
        return rows

    def source_issues(id_):
        return sorted([row for row in current()["issues"].values()
                       if row["yeu_cau_san_xuat_id"] == id_], key=lambda row: row["id"])

    async def read_issues(id_):
        return [{key: row[key] for key in ("id", "ma_phieu_xuat", "loai_phieu", "trang_thai")}
                for row in source_issues(id_)]

    async def lock_issues(id_):
        events.append(("issue_lock", id_))
        return [PhieuXuatSnapshot(row["id"], row["trang_thai"], deepcopy(row))
                for row in source_issues(id_)]

    async def delete_draft(id_):
        del current()["issues"][id_]

    async def reject(id_, actor_id, at):
        row = current()["issues"][id_]
        row.update(trang_thai="tu_choi", nguoi_xu_ly_id=actor_id, xu_ly_at=at.isoformat(),
                   ly_do_tu_choi="Yêu cầu đã hủy", phien_ban=row["phien_ban"] + 1)
        return PhieuXuatSnapshot(id_, "tu_choi", deepcopy(row))

    async def update(id_, changes):
        before = current()["requests"][id_]
        after = before.model_copy(update={**changes, "phien_ban": before.phien_ban + 1,
                                          "updated_at": datetime.now(timezone.utc)})
        current()["requests"][id_] = after
        return after

    async def append(entry):
        current()["history"].append(entry.model_copy(deep=True))

    async def rollback():
        nonlocal pending
        pending = None

    async def commit():
        nonlocal pending
        assert pending is not None
        data.clear()
        data.update(pending)
        pending = None

    repo.get_by_id.side_effect = lambda id_: current()["requests"].get(id_)
    repo.get_for_update.side_effect = lock_request
    repo.giu_hang_dang_giu.side_effect = read_holds
    repo.tra_giu_hang.side_effect = release
    repo.update.side_effect = update
    issues_repo.phieu_cua_yeu_cau.side_effect = read_issues
    issues_repo.lock_by_sources.side_effect = lock_issues
    issues_repo.delete_draft.side_effect = delete_draft
    issues_repo.reject.side_effect = reject
    audit.append.side_effect = append
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    transaction = SqlAlchemyTransaction(session)
    issues = PhieuXuatService(issues_repo, audit, transaction, Mock())
    service = YeuCauSanXuatService(repo, audit, transaction, Mock(), Mock(), issues)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(yeu_cau_sx_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "quan_ly")
        if role == "anonymous":
            raise UnauthorizedException()
        return {"sub": "20" if role == "nhan_vien" else "10", "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_yeu_cau_san_xuat_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False),
                           base_url="http://test") as client:
        yield SimpleNamespace(data=data, repo=repo, issues_repo=issues_repo, audit=audit,
                              session=session, service=service, client=client, events=events)


async def cancel(api, **options):
    return await api.client.post(f"{URL}/1/huy", json={"ly_do": "  Không còn nhu cầu  "},
                                 headers={"If-Match": generate_yeu_cau_etag(api.data["requests"][1])},
                                 **options)


def unchanged(api, before):
    assert api.data == before
    api.repo.update.assert_not_awaited()
    api.repo.tra_giu_hang.assert_not_awaited()
    api.issues_repo.delete_draft.assert_not_awaited()
    api.issues_repo.reject.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.commit.assert_not_awaited()


# UC-28 AC-1: Trả mọi loại giữ đang giữ, tăng còn dùng được, tồn thực tế không đổi
async def test_cancel_releases_all_active_hold_kinds_without_changing_stock(api):
    started = datetime.now(timezone.utc)
    before = deepcopy(api.data)
    assert before["stock"][2] - before["held"][2] == 0
    response = await cancel(api)
    assert response.status_code == 200, response.text
    assert api.data["held"] == {2: 0, 5: 2}
    assert api.data["stock"][2] - api.data["held"][2] == 10
    assert api.data["stock"] == before["stock"]
    for row in api.data["holds"][:3]:
        assert row["trang_thai"] == "da_tra"
        assert started <= row["ket_thuc_at"] <= datetime.now(timezone.utc)
    assert api.data["holds"][3:] == before["holds"][3:]
    assert response.headers["etag"] == generate_yeu_cau_etag(api.data["requests"][1])
    assert response.headers["etag"] != generate_yeu_cau_etag(before["requests"][1])
    api.session.commit.assert_awaited_once()


# UC-28 AC-2: Phiếu đã duyệt của bất kỳ loại nào chặn hủy, không có ghi dữ liệu
# UC-28 A2: Kiểm lại R2 khi xác nhận dù xem trước từng cho phép
@pytest.mark.parametrize("kind", ["xuat_linh_kien", "xuat_thanh_pham"])
async def test_approved_issue_blocks_cancellation_including_after_preview(api, kind):
    preview = await api.client.get(f"{URL}/1/huy")
    assert preview.status_code == 200 and preview.json()["data"]["duoc_huy"] is True
    api.data["issues"][1].update(trang_thai="da_duyet", loai_phieu=kind)
    before = deepcopy(api.data)
    response = await cancel(api)
    assert response.status_code == 409
    unchanged(api, before)
    assert api.events == [("request_lock", 1), ("issue_lock", 1)]
    api.session.rollback.assert_awaited_once()


# UC-28 AC-3: Phiếu chờ duyệt bị từ chối, có người/thời điểm và lịch sử lý do chuẩn
async def test_pending_issue_is_rejected_with_processor_time_and_history(api):
    started = datetime.now(timezone.utc)
    response = await cancel(api)
    assert response.status_code == 200
    row = api.data["issues"][1]
    assert row["trang_thai"] == "tu_choi" and row["ly_do_tu_choi"] == "Yêu cầu đã hủy"
    assert row["nguoi_xu_ly_id"] == 10
    assert started <= datetime.fromisoformat(row["xu_ly_at"]) <= datetime.now(timezone.utc)
    assert row["phien_ban"] == 2
    entry = next(h for h in api.data["history"] if h.loai_doi_tuong == "phieu_xuat" and h.doi_tuong_id == 1)
    assert (entry.thao_tac, entry.trang_thai_truoc, entry.trang_thai_sau) == ("tu_choi", "cho_duyet", "tu_choi")
    assert entry.ly_do == "Yêu cầu đã hủy" and entry.nhan_vien_id == 10
    assert entry.du_lieu_sau == row


# UC-28 AC-4: Xóa phiếu nháp và chi tiết, giữ snapshot trước trong lịch sử
async def test_draft_issue_and_lines_are_deleted_with_history(api):
    before = deepcopy(api.data["issues"])
    assert (await cancel(api)).status_code == 200
    assert 2 not in api.data["issues"]
    assert api.data["issues"][3] == before[3]
    entry = next(h for h in api.data["history"] if h.loai_doi_tuong == "phieu_xuat" and h.doi_tuong_id == 2)
    assert entry.thao_tac == "xoa_nhap" and entry.ly_do == "Yêu cầu đã hủy"
    assert entry.du_lieu_truoc == before[2] and entry.du_lieu_sau == {}
    assert entry.du_lieu_truoc["chi_tiet"] == [{"id": 20, "mat_hang_id": 2, "so_luong": 10}]
    api.issues_repo.delete_draft.assert_awaited_once_with(2)


# UC-28 AC-5: Thiếu, rỗng hoặc toàn khoảng trắng trả 422 và không ghi
# UC-28 A1: Bắt buộc lý do hủy
@pytest.mark.parametrize("body", [{}, {"ly_do": ""}, {"ly_do": " \t\n "}])
async def test_reason_is_required_and_whitespace_is_rejected(api, body):
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/1/huy", json=body,
                                     headers={"If-Match": generate_yeu_cau_etag(before["requests"][1])})
    assert response.status_code == 422
    unchanged(api, before)
    assert api.events == []


# UC-28 AC-6: Sau hủy không sửa/xóa/gửi/kiểm tra/hủy lại được
async def test_cancelled_request_rejects_all_existing_mutations_and_checks(api):
    assert (await cancel(api)).status_code == 200
    before = deepcopy(api.data)
    body = {"loai_yeu_cau": "xuat_giao", "mat_hang_id": 5, "so_luong": 10,
            "han_hoan_thanh": "2026-12-01", "nhan_vien_duoc_giao_id": 20}
    for method, path, payload, role in [
        ("PATCH", "", body, "quan_ly"), ("DELETE", "", None, "quan_ly"),
        ("POST", "/gui", {}, "quan_ly"), ("GET", "/kiem_tra", None, "nhan_vien"),
        ("POST", "/kiem_tra", {}, "nhan_vien"), ("POST", "/huy", {"ly_do": "Hủy lại"}, "quan_ly"),
    ]:
        response = await api.client.request(method, f"{URL}/1{path}", json=payload, headers={
            "If-Match": generate_yeu_cau_etag(before["requests"][1]), "x-role": role,
        })
        assert response.status_code == 409, (method, path, response.text)
        assert api.data == before
    assert api.data["requests"][1].trang_thai == "da_huy"


# UC-28 AC-7: Nhân viên không có quyền GET hoặc POST hủy
@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_employee_cannot_preview_or_cancel(api, method):
    before = deepcopy(api.data)
    response = await api.client.request(method, f"{URL}/1/huy", json={"ly_do": "Hủy"},
                                        headers={"x-role": "nhan_vien"})
    assert response.status_code == 403
    unchanged(api, before)
    assert api.events == []
    with pytest.raises(ForbiddenException):
        if method == "GET":
            await api.service.xem_truoc_huy(1, {"sub": "20", "roles": ["nhan_vien"]}, "test")
        else:
            await api.service.huy(1, "Hủy", {"sub": "20", "roles": ["nhan_vien"]}, None, "test")


# UC-28 A4: ETag thiếu/cũ trả 428/412, không khóa phiếu hoặc ghi
@pytest.mark.parametrize("etag,status", [(None, 428), ('"stale"', 412)])
async def test_missing_or_stale_etag_prevents_issue_locks_and_writes(api, etag, status):
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/1/huy", json={"ly_do": "Hủy"},
                                     headers={} if etag is None else {"If-Match": etag})
    assert response.status_code == status
    unchanged(api, before)
    assert api.events == [("request_lock", 1)]


# UC-28 A5: Nháp chỉ xóa; hoàn thành và đã hủy không được hủy
# UC-28 D1: Chỉ ba trạng thái đã duyệt được hủy
@pytest.mark.parametrize("state", ["nhap", "hoan_thanh", "da_huy"])
async def test_ineligible_request_states_return_conflict(api, state):
    api.data["requests"][1] = request_record(trang_thai=state)
    before = deepcopy(api.data)
    response = await cancel(api)
    assert response.status_code == 409
    unchanged(api, before)
    api.issues_repo.lock_by_sources.assert_not_awaited()


# UC-28 D3: Lịch sử yêu cầu giữ lý do nhập, trạng thái trước/sau và tác động v4
@pytest.mark.parametrize("state", ["da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien"])
async def test_service_records_cancellation_metadata_and_exact_effects(api, state):
    started = datetime.now(timezone.utc)
    api.data["requests"][1] = api.data["requests"][1].model_copy(update={"trang_thai": state})
    result, etag = await api.service.huy(1, "  Không còn nhu cầu  ", MANAGER,
                                       generate_yeu_cau_etag(api.data["requests"][1]), "service")
    after = result.data
    assert after.trang_thai == "da_huy"
    assert started <= after.huy_at <= datetime.now(timezone.utc)
    assert after.nguoi_huy_id == 10 and after.ly_do_huy == "Không còn nhu cầu"
    assert etag == generate_yeu_cau_etag(after)
    entry = api.data["history"][-1]
    assert (entry.loai_doi_tuong, entry.thao_tac, entry.doi_tuong_id) == ("yeu_cau_san_xuat", "huy", 1)
    assert (entry.trang_thai_truoc, entry.trang_thai_sau, entry.ly_do) == (state, "da_huy", "Không còn nhu cầu")
    assert entry.du_lieu_sau["hang_tra"] == [
        {"id": 1, "mat_hang_id": 2, "ma_mat_hang": "MH-000002", "ten_mat_hang": "Khung", "don_vi_tinh": "cái", "loai_giu": "linh_kien", "so_luong": 10},
        {"id": 2, "mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Xe", "don_vi_tinh": "xe", "loai_giu": "thanh_pham_co_san", "so_luong": 3},
        {"id": 3, "mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Xe", "don_vi_tinh": "xe", "loai_giu": "thanh_pham_san_xuat", "so_luong": 2},
    ]
    assert entry.du_lieu_sau["phieu_xuat"] == [
        {"ma_phieu_xuat": "PX-202611-000001", "xu_ly": "tu_choi"},
        {"ma_phieu_xuat": "PX-202611-000002", "xu_ly": "bo"},
    ]
    assert entry.du_lieu_sau["huy_at"] == after.model_dump(mode="json")["huy_at"]
    assert entry.du_lieu_truoc["trang_thai"] == state
    assert api.events[:4] == [("request_lock", 1), ("issue_lock", 1),
                              ("item_lock", [2, 5]), ("hold_lock", 1)]


# UC-28 D4: GET chỉ đọc và trả đúng hàng, phiếu bị ảnh hưởng, lý do không hủy
@pytest.mark.parametrize("approved", [False, True])
async def test_preview_is_read_only_and_describes_exact_effects(api, approved):
    if approved:
        api.data["issues"][1]["trang_thai"] = "da_duyet"
    before = deepcopy(api.data)
    response = await api.client.get(f"{URL}/1/huy")
    assert response.status_code == 200
    preview = response.json()["data"]
    assert preview["duoc_huy"] is not approved
    assert preview["ly_do_khong_huy"] == (
        "Yêu cầu đã có phiếu xuất được duyệt, không thể hủy." if approved else None)
    assert preview["hang_tra"] == [
        {"id": 1, "mat_hang_id": 2, "ma_mat_hang": "MH-000002", "ten_mat_hang": "Khung", "don_vi_tinh": "cái", "loai_giu": "linh_kien", "so_luong": 10},
        {"id": 2, "mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Xe", "don_vi_tinh": "xe", "loai_giu": "thanh_pham_co_san", "so_luong": 3},
        {"id": 3, "mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Xe", "don_vi_tinh": "xe", "loai_giu": "thanh_pham_san_xuat", "so_luong": 2},
    ]
    expected = [{"id": 2, "ma_phieu_xuat": "PX-202611-000002", "loai_phieu": "xuat_thanh_pham", "trang_thai": "nhap", "xu_ly": "bo"}]
    if not approved:
        expected.insert(0, {"id": 1, "ma_phieu_xuat": "PX-202611-000001", "loai_phieu": "xuat_linh_kien", "trang_thai": "cho_duyet", "xu_ly": "tu_choi"})
    assert preview["phieu_xuat"] == expected
    assert api.events == []
    api.repo.get_for_update.assert_not_awaited()
    api.issues_repo.lock_by_sources.assert_not_awaited()
    assert all(c == call(1, lock=False) for c in api.repo.giu_hang_dang_giu.await_args_list)
    unchanged(api, before)


# UC-28 D4: Xem trước trạng thái không đủ điều kiện vẫn chỉ đọc và nêu lý do
@pytest.mark.parametrize("state", ["nhap", "hoan_thanh", "da_huy"])
async def test_preview_explains_ineligible_request_state_without_locking(api, state):
    api.data["requests"][1] = request_record(trang_thai=state)
    before = deepcopy(api.data)
    response = await api.client.get(f"{URL}/1/huy")
    assert response.status_code == 200
    assert response.json()["data"]["duoc_huy"] is False
    assert response.json()["data"]["ly_do_khong_huy"] == (
        "Chỉ hủy yêu cầu Đã gửi, Chờ bổ sung linh kiện hoặc Đang thực hiện.")
    assert api.events == []
    unchanged(api, before)


# UC-28 D1: Yêu cầu đã gửi chưa có giữ hàng hoặc phiếu vẫn hủy được
async def test_sent_request_without_holds_or_issues_can_be_cancelled(api):
    api.data["requests"][1] = request_record()
    api.data["holds"] = []
    api.data["held"] = {2: 0, 5: 0}
    api.data["issues"] = {}
    response = await api.client.get(f"{URL}/1/huy")
    assert response.status_code == 200
    assert response.json()["data"] == {
        "duoc_huy": True, "ly_do_khong_huy": None, "hang_tra": [], "phieu_xuat": [],
    }
    before_stock = deepcopy(api.data["stock"])
    assert (await cancel(api)).status_code == 200
    assert api.data["requests"][1].trang_thai == "da_huy"
    assert api.data["stock"] == before_stock and api.data["held"] == {2: 0, 5: 0}
    assert api.data["history"][-1].du_lieu_sau["hang_tra"] == []
    assert api.data["history"][-1].du_lieu_sau["phieu_xuat"] == []


# UC-28 D3: Lỗi lịch sử ở phiếu hoặc yêu cầu rollback toàn bộ các đối tượng
@pytest.mark.parametrize("fail_kind", ["phieu_xuat", "yeu_cau_san_xuat"])
async def test_audit_failure_rolls_back_request_holds_issues_and_history(api, fail_kind):
    before = deepcopy(api.data)
    append = api.audit.append.side_effect

    async def fail(entry):
        if entry.loai_doi_tuong == fail_kind:
            raise RuntimeError("audit unavailable")
        await append(entry)

    api.audit.append.side_effect = fail
    response = await cancel(api)
    assert response.status_code == 500
    assert api.data == before
    api.repo.tra_giu_hang.assert_awaited_once_with(1)
    api.issues_repo.reject.assert_awaited_once()
    api.session.rollback.assert_awaited_once()
    api.session.commit.assert_not_awaited()


def sql(statement):
    return str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


# UC-28 A4: Repository thật khóa yêu cầu/phiếu FOR UPDATE, xem trước phiếu không khóa
async def test_repository_request_and_issue_locks_and_read_only_issue_query():
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    session.scalars.return_value = Mock(all=Mock(return_value=[]))
    session.execute.return_value = Mock(mappings=Mock(return_value=[]))
    requests = SqlAlchemyYeuCauSanXuatRepository(session)
    issues = SqlAlchemyPhieuXuatRepository(session)
    assert await requests.get_for_update(1) is None
    request_sql = sql(session.scalar.call_args.args[0])
    assert 'FROM "YeuCauSanXuat"' in request_sql and request_sql.endswith("FOR UPDATE")
    assert await issues.lock_by_sources(1) == []
    issue_sql = sql(session.scalars.call_args.args[0])
    assert 'WHERE "PhieuXuat".yeu_cau_san_xuat_id = 1' in issue_sql
    assert issue_sql.endswith('ORDER BY "PhieuXuat".id FOR UPDATE')
    assert await issues.phieu_cua_yeu_cau(1) == []
    preview_sql = sql(session.execute.call_args.args[0])
    assert "FOR UPDATE" not in preview_sql and "FOR SHARE" not in preview_sql
    assert '"PhieuXuat".ma_phieu_xuat' in preview_sql


# UC-28 AC-1: Repository thật chỉ trừ tổng giữ, khóa MatHang trước GiuHang theo id
# UC-28 A4: SQL trả giữ hàng có FOR UPDATE và không khóa qua JOIN sai thứ tự
async def test_repository_releases_holds_under_ordered_locks_without_stock_update():
    started = datetime.now(timezone.utc)
    rows = [
        {"id": 2, "mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Xe", "don_vi_tinh": "xe", "loai_giu": "thanh_pham_co_san", "so_luong": 3},
        {"id": 3, "mat_hang_id": 5, "ma_mat_hang": "MH-000005", "ten_mat_hang": "Xe", "don_vi_tinh": "xe", "loai_giu": "thanh_pham_san_xuat", "so_luong": 2},
    ]
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock(mappings=Mock(return_value=rows))
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    assert [row.model_dump() for row in await repo.tra_giu_hang(1)] == rows
    queries = [c.args[0] for c in session.execute.call_args_list]
    assert len(queries) == 4
    item_sql, hold_sql, item_update, hold_update = map(sql, queries)
    assert 'FROM "MatHang"' in item_sql and item_sql.endswith('ORDER BY "MatHang".id FOR UPDATE')
    assert '"GiuHang".yeu_cau_san_xuat_id = 1' in item_sql
    assert '"GiuHang".trang_thai = \'dang_giu\'' in item_sql
    assert hold_sql.endswith('ORDER BY "GiuHang".mat_hang_id, "GiuHang".id FOR UPDATE OF "GiuHang"')
    assert '"GiuHang".trang_thai = \'dang_giu\'' in hold_sql
    assert 'SET so_luong_dang_giu=("MatHang".so_luong_dang_giu - 5)' in item_update
    assert "so_luong_ton" not in item_update
    assert 'WHERE "GiuHang".id IN (2, 3)' in hold_update
    params = queries[3].compile().params
    assert params["trang_thai"] == "da_tra"
    assert started <= params["ket_thuc_at"] <= datetime.now(timezone.utc)
    session.flush.assert_awaited_once()


# UC-28 AC-4: Repository phiếu thật xóa chi tiết trước header
async def test_repository_deletes_draft_lines_before_header():
    session = AsyncMock(spec=AsyncSession)
    await SqlAlchemyPhieuXuatRepository(session).delete_draft(2)
    queries = [sql(c.args[0]) for c in session.execute.call_args_list]
    assert queries == ['DELETE FROM "ChiTietPhieuXuat" WHERE "ChiTietPhieuXuat".phieu_xuat_id = 2',
                       'DELETE FROM "PhieuXuat" WHERE "PhieuXuat".id = 2']


# UC-28 D4: SQL xem trước giữ hàng không khóa, không cập nhật hoặc flush
async def test_repository_preview_holds_does_not_lock_or_write():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock(mappings=Mock(return_value=[]))
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    assert await repo.giu_hang_dang_giu(1, lock=False) == []
    query = sql(session.execute.call_args.args[0])
    assert query.startswith("SELECT ")
    assert "FOR UPDATE" not in query and "FOR SHARE" not in query
    assert '"GiuHang".trang_thai = \'dang_giu\'' in query
    assert '"GiuHang".yeu_cau_san_xuat_id = 1' in query
    session.execute.assert_awaited_once()
    session.flush.assert_not_awaited()
