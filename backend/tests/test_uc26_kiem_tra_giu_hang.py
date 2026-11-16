"""UC-26: stateful ports and ASGI; compiled SQL, without a database connection."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenException, UnauthorizedException
from app.core.exceptions import register_exception_handlers
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_current_user_payload, get_yeu_cau_san_xuat_service
from app.modules.audit.ports import AuditWriter
from app.modules.mat_hang.models import MatHang
from app.modules.san_xuat.models import GiuHang, NhuCauLinhKien
from app.modules.san_xuat.ports import HangKhaDung, YeuCauSanXuatRepository
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.router import yeu_cau_sx_router
from app.modules.san_xuat.schemas import YeuCauRead
from app.modules.san_xuat.service.yeu_cau_san_xuat import (
    YeuCauSanXuatService,
    generate_yeu_cau_etag,
    tinh_ket_qua_kiem_tra,
)

URL = "/api/v1/yeu_cau_san_xuat"
EMPLOYEE = {"sub": "20", "roles": ["nhan_vien"]}
NOW = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)


def request_record(id_=1, **changes):
    return YeuCauRead(
        id=id_, ma_yeu_cau_san_xuat=f"YCSX-202611-{id_:06d}",
        **{
            "loai_yeu_cau": "xuat_giao", "mat_hang_id": 5, "so_luong": 10,
            "han_hoan_thanh": date(2026, 12, 1), "nhan_vien_id": 10,
            "nhan_vien_duoc_giao_id": 20, "trang_thai": "da_gui", "bom_id": 101,
            "created_at": NOW, "updated_at": NOW, "gui_at": NOW, "completed_at": None,
            "so_luong_dung_thanh_pham": None, "so_luong_can_san_xuat": None,
            "kiem_tra_lan_dau_at": None, "started_at": None, "huy_at": None,
            "nguoi_huy_id": None, "ly_do_huy": None, "phien_ban": 1, **changes,
        },
    )


@pytest.fixture
async def api():
    stored, pending = {1: request_record(), 2: request_record(2)}, {}
    stock, held, pending_held = {5: 3, 2: 100, 9: 100}, {5: 0, 2: 0, 9: 0}, {}
    needs, pending_needs, holds, pending_holds, history, pending_history = {}, {}, [], [], [], []
    boms = {101: {9: 2, 2: 1}, 102: {2: 8}}
    events = []
    repo = AsyncMock(spec=YeuCauSanXuatRepository)
    audit, session = AsyncMock(spec=AuditWriter), AsyncMock(spec=AsyncSession)

    def read(id_):
        return pending.get(id_, stored.get(id_))

    async def lock_request(id_):
        events.append(("request_lock", id_))
        return read(id_)

    async def availability(ids, *, lock):
        if lock:
            events.append(("item_lock", list(ids)))
        events.append(("available_read", list(ids)))
        return {id_: HangKhaDung(
            f"MH-{id_:06d}", {5: "Xe", 2: "Khung", 9: "Bánh"}[id_],
            "xe" if id_ == 5 else "cái", stock[id_] - held[id_] - pending_held.get(id_, 0),
        ) for id_ in ids}

    async def write_needs(id_, quantities):
        assert id_ not in needs and id_ not in pending_needs
        pending_needs[id_] = dict(quantities)

    async def reserve(id_, reservations):
        for row in reservations:
            assert not any(old["yeu_cau_san_xuat_id"] == id_
                           and old["mat_hang_id"] == row["mat_hang_id"]
                           and old["loai_giu"] == row["loai_giu"] for old in holds + pending_holds)
            item_id = row["mat_hang_id"]
            pending_held[item_id] = pending_held.get(item_id, 0) + row["so_luong"]
            assert held[item_id] + pending_held[item_id] <= stock[item_id]
            pending_holds.append({"yeu_cau_san_xuat_id": id_, **row})

    async def update(id_, changes):
        before = read(id_)
        pending[id_] = before.model_copy(update={
            **changes, "phien_ban": before.phien_ban + 1, "updated_at": datetime.now(timezone.utc),
        })
        return pending[id_]

    async def append(entry):
        pending_history.append(entry.model_copy(deep=True))

    async def rollback():
        pending.clear()
        pending_held.clear()
        pending_needs.clear()
        pending_holds.clear()
        pending_history.clear()

    async def commit():
        stored.update(pending)
        needs.update(pending_needs)
        for id_, n in pending_held.items():
            held[id_] += n
        holds.extend(pending_holds)
        history.extend(pending_history)
        await rollback()

    repo.get_by_id.side_effect = read
    repo.get_for_update.side_effect = lock_request
    repo.dinh_muc.side_effect = lambda id_: dict(boms[id_])
    repo.nhu_cau.side_effect = lambda id_: dict(needs[id_])
    repo.kha_dung.side_effect = availability
    repo.ghi_nhu_cau.side_effect = write_needs
    repo.giu_hang.side_effect = reserve
    repo.update.side_effect = update
    audit.append.side_effect = append
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    service = YeuCauSanXuatService(repo, audit, SqlAlchemyTransaction(session), Mock(), Mock(), Mock())
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(yeu_cau_sx_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "nhan_vien")
        if role == "anonymous":
            raise UnauthorizedException()
        return {"sub": request.headers.get("x-actor", "20"), "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_yeu_cau_san_xuat_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False),
                           base_url="http://test") as client:
        yield SimpleNamespace(
            client=client, service=service, repo=repo, audit=audit, session=session,
            stored=stored, stock=stock, held=held, needs=needs, holds=holds, history=history,
            pending=pending, pending_held=pending_held, pending_needs=pending_needs,
            pending_holds=pending_holds, pending_history=pending_history, boms=boms, events=events,
        )


async def check(api, id_=1, **options):
    response = await api.client.post(f"{URL}/{id_}/kiem_tra", json={}, headers={
        "If-Match": generate_yeu_cau_etag(api.stored[id_]), **options,
    })
    assert response.status_code == 200, response.text
    return response


def snapshot(api):
    return deepcopy((api.stored, api.stock, api.held, api.needs, api.holds, api.history))


def assert_no_writes(api):
    api.repo.update.assert_not_awaited()
    api.repo.giu_hang.assert_not_awaited()
    api.repo.ghi_nhu_cau.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    assert not api.pending and not api.pending_holds and not api.pending_held
    assert not api.pending_needs and not api.pending_history


# UC-26 AC-1: Dùng 3 thành phẩm, sản xuất 7, chốt và giữ đúng số lượng
async def test_first_check_uses_stock_and_reserves_remaining_requirements(api):
    old_etag = generate_yeu_cau_etag(api.stored[1])
    response = await check(api)
    data = response.json()["data"]
    assert data["yeu_cau"]["so_luong_dung_thanh_pham"] == 3
    assert data["yeu_cau"]["so_luong_can_san_xuat"] == 7
    assert data["yeu_cau"]["kiem_tra_lan_dau_at"] is not None
    assert data["yeu_cau"]["trang_thai"] == "dang_thuc_hien"
    assert data["ket_qua"]["giu_thanh_pham"] == 3 and data["ket_qua"]["lan_dau"] is True
    assert api.needs == {1: {2: 7, 9: 14}}
    assert api.holds == [
        {"yeu_cau_san_xuat_id": 1, "mat_hang_id": 5, "loai_giu": "thanh_pham_co_san", "so_luong": 3},
        {"yeu_cau_san_xuat_id": 1, "mat_hang_id": 2, "loai_giu": "linh_kien", "so_luong": 7},
        {"yeu_cau_san_xuat_id": 1, "mat_hang_id": 9, "loai_giu": "linh_kien", "so_luong": 14},
    ]
    assert api.held == {5: 3, 2: 7, 9: 14} and api.stock == {5: 3, 2: 100, 9: 100}
    assert response.headers["etag"] == generate_yeu_cau_etag(api.stored[1]) != old_etag
    assert data["yeu_cau"]["phien_ban"] == 2
    assert (await api.client.get(f"{URL}/1")).headers["etag"] == response.headers["etag"]


# UC-26 AC-2: Thành phẩm đã giữ cho A không tính cho B
async def test_second_request_cannot_reuse_reserved_finished_stock(api):
    await check(api)
    api.stored[2] = api.stored[2].model_copy(update={"so_luong": 3})
    data = (await check(api, 2)).json()["data"]
    assert data["ket_qua"]["so_luong_dung_thanh_pham"] == 0
    assert data["ket_qua"]["so_luong_can_san_xuat"] == 3
    assert api.held[5] == 3
    assert not [row for row in api.holds if row["yeu_cau_san_xuat_id"] == 2 and row["loai_giu"] == "thanh_pham_co_san"]


# UC-26 AC-3: Giữ linh kiện theo thứ tự, B thiếu toàn bộ phần A đã giữ
async def test_components_are_reserved_in_check_order(api):
    api.stock.update({5: 0, 2: 10})
    api.boms[101] = {2: 1}
    first = (await check(api)).json()["data"]
    second = (await check(api, 2)).json()["data"]
    assert first["yeu_cau"]["trang_thai"] == "dang_thuc_hien"
    assert second["yeu_cau"]["trang_thai"] == "cho_bo_sung_linh_kien"
    assert second["ket_qua"]["linh_kien"][0]["so_luong_thieu"] == 10
    assert api.holds == [{"yeu_cau_san_xuat_id": 1, "mat_hang_id": 2, "loai_giu": "linh_kien", "so_luong": 10}]
    assert api.held[2] == 10 and api.stock[2] == 10


# UC-26 AC-4: Hai bản xem trước đủ; xác nhận tuần tự tính lại sau khóa theo id
# UC-26 A4: Chỉ một yêu cầu giữ phần hàng tranh chấp
async def test_confirmation_recomputes_contended_stock_under_ordered_locks(api):
    api.stock.update({5: 0, 2: 10})
    api.boms[101] = {9: 1, 2: 1}
    api.stored[2] = api.stored[2].model_copy(update={"nhan_vien_duoc_giao_id": 22})
    for id_ in (1, 2):
        response = await api.client.get(f"{URL}/{id_}/kiem_tra", headers={"x-actor": "20" if id_ == 1 else "22"})
        assert response.status_code == 200 and response.json()["data"]["du_linh_kien"] is True
    api.events.clear()
    results = [(await check(api, id_, **{"x-actor": "20" if id_ == 1 else "22"})).json()["data"]["ket_qua"] for id_ in (1, 2)]
    assert [r["du_linh_kien"] for r in results] == [True, False]
    assert api.events == [
        ("request_lock", 1), ("item_lock", [2, 5, 9]), ("available_read", [2, 5, 9]),
        ("request_lock", 2), ("item_lock", [2, 5, 9]), ("available_read", [2, 5, 9]),
    ]
    assert {r["yeu_cau_san_xuat_id"] for r in api.holds} == {1}
    assert api.held[2] == 10


# UC-26 AC-1: Xác nhận tính lại thành phẩm còn dùng được, không dùng số từ bản xem trước
async def test_confirmation_recomputes_finished_stock_after_preview(api):
    response = await api.client.get(f"{URL}/1/kiem_tra")
    assert response.status_code == 200
    assert response.json()["data"]["so_luong_dung_thanh_pham"] == 3
    api.stored[2] = api.stored[2].model_copy(update={"so_luong": 2})
    await check(api, 2)
    result = (await check(api)).json()["data"]["ket_qua"]
    assert result["so_luong_dung_thanh_pham"] == 1
    assert result["so_luong_can_san_xuat"] == 9
    assert api.needs[1] == {2: 9, 9: 18}
    assert api.held[5] == 3
    assert api.holds[1] == {"yeu_cau_san_xuat_id": 1, "mat_hang_id": 5, "loai_giu": "thanh_pham_co_san", "so_luong": 1}


# UC-26 AC-5: Thiếu một loại không giữ loại đủ; giữ thành phẩm, đủ sáu dữ liệu báo thiếu
# UC-26 A2: Chờ bổ sung, giữ thành phẩm nhưng không giữ linh kiện
async def test_shortage_holds_no_components_and_returns_all_shortage_fields(api):
    api.stock[2] = 4
    data = (await check(api)).json()["data"]
    assert data["yeu_cau"]["trang_thai"] == "cho_bo_sung_linh_kien"
    assert data["ket_qua"]["linh_kien"] == [
        {"mat_hang_id": 2, "ma_mat_hang": "MH-000002", "ten_mat_hang": "Khung", "don_vi_tinh": "cái", "so_luong_can": 7, "so_luong_con_dung": 4, "so_luong_thieu": 3},
        {"mat_hang_id": 9, "ma_mat_hang": "MH-000009", "ten_mat_hang": "Bánh", "don_vi_tinh": "cái", "so_luong_can": 14, "so_luong_con_dung": 100, "so_luong_thieu": 0},
    ]
    assert api.needs[1] == {2: 7, 9: 14}
    assert api.held == {5: 3, 2: 0, 9: 0}
    assert api.holds == [{"yeu_cau_san_xuat_id": 1, "mat_hang_id": 5, "loai_giu": "thanh_pham_co_san", "so_luong": 3}]


# UC-26 AC-6: Đọc bom_id phiên bản 1 đã chốt, bỏ qua phiên bản 2 đang dùng
async def test_first_check_reads_frozen_bom_instead_of_current_version(api):
    api.repo.bom_dang_dung.return_value = 102
    result, _ = await api.service.kiem_tra(1, EMPLOYEE, generate_yeu_cau_etag(api.stored[1]), "frozen")
    assert {line.mat_hang_id: line.so_luong_can for line in result.data.ket_qua.linh_kien} == {2: 7, 9: 14}
    api.repo.dinh_muc.assert_awaited_once_with(101)
    api.repo.bom_dang_dung.assert_not_awaited()
    assert api.needs[1] == {2: 7, 9: 14} != {2: 56}


# UC-26 AC-7: Kiểm tra lại giữ nhu cầu đã chốt, không sửa số lượng hoặc thời điểm chốt
# UC-26 A3: Đủ sau bổ sung chuyển Đang thực hiện
async def test_recheck_uses_saved_requirements_and_preserves_first_check_values(api):
    api.stock[2] = 4
    await check(api)
    before = api.stored[1]
    first_holds = deepcopy(api.holds)
    api.stock.update({5: 50, 2: 20})
    api.boms[101] = {2: 99}
    api.repo.dinh_muc.reset_mock()
    api.repo.ghi_nhu_cau.reset_mock()
    data = (await check(api)).json()["data"]
    assert data["ket_qua"]["lan_dau"] is False and data["ket_qua"]["giu_thanh_pham"] == 0
    assert data["yeu_cau"]["trang_thai"] == "dang_thuc_hien"
    for field in ("so_luong_dung_thanh_pham", "so_luong_can_san_xuat", "kiem_tra_lan_dau_at"):
        assert getattr(api.stored[1], field) == getattr(before, field)
    assert api.needs == {1: {2: 7, 9: 14}}
    assert api.holds[:1] == first_holds and len(api.holds) == 3
    assert api.held == {5: 3, 2: 7, 9: 14}
    api.repo.nhu_cau.assert_awaited_once_with(1)
    api.repo.dinh_muc.assert_not_awaited()
    api.repo.ghi_nhu_cau.assert_not_awaited()
    assert [(h.trang_thai_truoc, h.trang_thai_sau) for h in api.history] == [
        ("da_gui", "cho_bo_sung_linh_kien"), ("cho_bo_sung_linh_kien", "dang_thuc_hien"),
    ]


# UC-26 D3: Kiểm tra lại vẫn thiếu không ghi gì và giữ nguyên ETag
async def test_recheck_still_short_changes_nothing_and_writes_no_history(api):
    api.stock[2] = 4
    await check(api)
    before = snapshot(api)
    etag = generate_yeu_cau_etag(api.stored[1])
    for mock in (api.repo.update, api.repo.giu_hang, api.repo.ghi_nhu_cau, api.audit.append):
        mock.reset_mock()
    response = await check(api)
    assert response.headers["etag"] == etag
    assert response.json()["data"]["ket_qua"]["linh_kien"][0]["so_luong_thieu"] == 3
    assert response.json()["data"]["ket_qua"]["lan_dau"] is False
    assert snapshot(api) == before
    assert_no_writes(api)


# UC-26 AC-8: Xem trước chỉ đọc, không khóa hoặc ghi khi đóng xác nhận
# UC-26 A5: GET không thay đổi yêu cầu, nhu cầu, giữ hàng và lịch sử
async def test_preview_is_read_only_without_locks_or_audit(api):
    before = snapshot(api)
    response = await api.client.get(f"{URL}/1/kiem_tra")
    assert response.status_code == 200
    assert response.json()["data"]["so_luong_can_san_xuat"] == 7
    api.repo.kha_dung.assert_awaited_once_with([2, 5, 9], lock=False)
    api.repo.get_for_update.assert_not_awaited()
    api.session.commit.assert_not_awaited()
    assert api.events == [("available_read", [2, 5, 9])]
    assert snapshot(api) == before
    assert_no_writes(api)


# UC-26 AC-9: Nhập kho sản xuất đủ 5, không dùng hoặc giữ 3 thành phẩm sẵn có
# UC-26 A7: Nhu cầu nhập kho tính cho toàn bộ số yêu cầu
async def test_stock_replenishment_does_not_use_or_reserve_finished_products(api):
    api.stored[1] = request_record(loai_yeu_cau="nhap_kho", so_luong=5)
    result = (await check(api)).json()["data"]["ket_qua"]
    assert result["so_luong_dung_thanh_pham"] == result["giu_thanh_pham"] == 0
    assert result["so_luong_can_san_xuat"] == 5
    assert api.needs[1] == {2: 5, 9: 10}
    assert api.held[5] == 0 and api.stock[5] == 3
    assert {row["loai_giu"] for row in api.holds} == {"linh_kien"}


# UC-26 A1: Đủ thành phẩm giữ đúng yêu cầu, không có nhu cầu linh kiện
async def test_sufficient_finished_products_skip_component_requirements(api):
    api.stock[5] = 15
    result = (await check(api)).json()["data"]
    assert result["ket_qua"]["so_luong_can_san_xuat"] == 0
    assert result["ket_qua"]["linh_kien"] == [] and result["ket_qua"]["du_linh_kien"] is True
    assert result["yeu_cau"]["trang_thai"] == "dang_thuc_hien"
    assert api.holds == [{"yeu_cau_san_xuat_id": 1, "mat_hang_id": 5, "loai_giu": "thanh_pham_co_san", "so_luong": 10}]
    assert not api.needs and api.held == {5: 10, 2: 0, 9: 0}
    api.repo.ghi_nhu_cau.assert_not_awaited()


# UC-26 D4: Một lịch sử có trạng thái trước/sau, chi tiết giữ và danh sách thiếu R12
@pytest.mark.parametrize("short", [False, True])
async def test_check_history_contains_exact_transition_holds_and_shortages(api, short):
    if short:
        api.stock[2] = 4
    data = (await check(api)).json()["data"]["ket_qua"]
    assert len(api.history) == 1
    entry = api.history[0]
    assert (entry.thao_tac, entry.nhan_vien_id, entry.loai_doi_tuong, entry.doi_tuong_id) == ("kiem_tra", 20, "yeu_cau_san_xuat", 1)
    assert (entry.trang_thai_truoc, entry.trang_thai_sau) == ("da_gui", data["trang_thai_du_kien"])
    assert entry.du_lieu_sau == {
        "lan_dau": True, "so_luong_dung_thanh_pham": 3, "so_luong_can_san_xuat": 7,
        "giu_hang": [{k: v for k, v in row.items() if k != "yeu_cau_san_xuat_id"} for row in api.holds],
        "thieu": [row for row in data["linh_kien"] if row["so_luong_thieu"]],
    }


# UC-26 A6: Thiếu If-Match trả 428, cũ/weak/* trả 412, không giữ hoặc ghi
@pytest.mark.parametrize("etag,status", [(None, 428), ("", 428), ('"old"', 412), ("*", 412), ('W/"old"', 412)])
async def test_confirmation_rejects_missing_or_stale_etag_without_writes(api, etag, status):
    before = snapshot(api)
    response = await api.client.post(f"{URL}/1/kiem_tra", json={}, headers={} if etag is None else {"If-Match": etag})
    assert response.status_code == status
    assert snapshot(api) == before
    api.repo.kha_dung.assert_not_awaited()
    assert_no_writes(api)


# UC-26 A6: Trạng thái ngoài Đã gửi/Chờ bổ sung bị 409 với ETag đúng
@pytest.mark.parametrize("state", ["nhap", "dang_thuc_hien", "da_huy", "hoan_thanh"])
async def test_ineligible_states_are_rejected_without_writes(api, state):
    # Nháp của NV ẩn theo UC-25; policy trạng thái riêng vẫn từ chối Nháp.
    api.stored[1] = request_record(trang_thai=state)
    before = snapshot(api)
    for method in ("get", "post"):
        response = await api.client.request(method, f"{URL}/1/kiem_tra",
                                           **({"json": {}, "headers": {"If-Match": generate_yeu_cau_etag(api.stored[1])}} if method == "post" else {}))
        assert response.status_code == (404 if state == "nhap" else 409)
    assert snapshot(api) == before
    assert_no_writes(api)


# UC-26 A6: Yêu cầu bị hủy sau xem trước làm ETag cũ trả 412
async def test_request_changed_after_preview_is_rejected(api):
    old = generate_yeu_cau_etag(api.stored[1])
    assert (await api.client.get(f"{URL}/1/kiem_tra")).status_code == 200
    api.stored[1] = api.stored[1].model_copy(update={"trang_thai": "da_huy", "phien_ban": 2})
    before = snapshot(api)
    response = await api.client.post(f"{URL}/1/kiem_tra", json={}, headers={"If-Match": old})
    assert response.status_code == 412 and snapshot(api) == before
    assert_no_writes(api)


# UC-26 D1: Chỉ NV được giao, QLK và NV khác bị 403 ở ASGI và service
@pytest.mark.parametrize("role,actor_id,status", [("quan_ly", 10, 403), ("nhan_vien", 22, 403), ("quan_tri_vien", 10, 403), ("anonymous", 20, 401)])
async def test_only_assigned_employee_can_preview_and_confirm(api, role, actor_id, status):
    before = snapshot(api)
    headers = {"x-role": role, "x-actor": str(actor_id), "If-Match": generate_yeu_cau_etag(api.stored[1])}
    for method in ("get", "post"):
        response = await api.client.request(method, f"{URL}/1/kiem_tra", headers=headers,
                                           **({"json": {}} if method == "post" else {}))
        assert response.status_code == status
    if role != "anonymous":
        actor = {"sub": str(actor_id), "roles": [role]}
        with pytest.raises(ForbiddenException):
            await api.service.xem_truoc_kiem_tra(1, actor, "forbidden")
        with pytest.raises(ForbiddenException):
            await api.service.kiem_tra(1, actor, headers["If-Match"], "forbidden")
    assert snapshot(api) == before
    assert_no_writes(api)


# UC-26 D1: Body rỗng bắt buộc, không cho token, trường lạ hoặc query
@pytest.mark.parametrize("body,query", [(None, ""), ({"token": "x"}, ""), ({"so_luong": 1}, ""), ({}, "?lock=true")])
async def test_confirmation_validates_empty_body_and_query_before_writing(api, body, query):
    response = await api.client.post(f"{URL}/1/kiem_tra{query}", json=body,
                                     headers={"If-Match": generate_yeu_cau_etag(api.stored[1])})
    assert response.status_code == 422
    assert_no_writes(api)


# UC-26 D2: Audit lỗi rollback nhu cầu, giữ hàng, số đang giữ và trạng thái cùng transaction
async def test_audit_failure_rolls_back_every_reservation_and_request_change(api):
    before = snapshot(api)
    api.audit.append.side_effect = RuntimeError("audit failed")
    response = await api.client.post(f"{URL}/1/kiem_tra", json={},
                                     headers={"If-Match": generate_yeu_cau_etag(api.stored[1])})
    assert response.status_code == 500
    api.repo.giu_hang.assert_awaited_once()
    api.repo.ghi_nhu_cau.assert_awaited_once()
    api.repo.update.assert_awaited_once()
    api.session.rollback.assert_awaited_once()
    api.session.commit.assert_not_awaited()
    assert snapshot(api) == before
    assert not api.pending and not api.pending_held and not api.pending_holds
    assert not api.pending_needs and not api.pending_history


def sql(statement):
    return " ".join(str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})).split())


# UC-26 AC-4: SQL thật khóa MatHang theo id tăng dần, đọc cột sinh còn dùng được
@pytest.mark.parametrize("lock", [True, False])
async def test_repository_availability_sql_locks_in_id_order(lock):
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = [SimpleNamespace(id=2, ma_mat_hang="MH-000002", ten_mat_hang="Khung", don_vi_tinh="cái", so_luong_con_dung=4)]
    result = await SqlAlchemyYeuCauSanXuatRepository(session).kha_dung([9, 5, 2], lock=lock)
    statement = sql(session.execute.call_args.args[0])
    assert 'FROM "MatHang" WHERE "MatHang".id IN (9, 5, 2) ORDER BY "MatHang".id' in statement
    assert ('FOR UPDATE' in statement) is lock
    if lock:
        assert statement.endswith('ORDER BY "MatHang".id FOR UPDATE')
    assert '"MatHang".so_luong_con_dung' in statement and "SUM(" not in statement
    assert result == {2: HangKhaDung("MH-000002", "Khung", "cái", 4)}


# UC-26 AC-6: SQL đọc ChiTietBom theo bom_id trực tiếp, không đọc BOM hiện hành
async def test_repository_reads_exact_frozen_bom_and_saved_requirements():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock()
    session.execute.return_value.all.return_value = [(2, 7)]
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    assert await repo.dinh_muc(101) == {2: 7}
    statement = sql(session.execute.call_args.args[0])
    assert 'FROM "ChiTietBom" WHERE "ChiTietBom".bom_id = 101' in statement
    assert "is_active" not in statement and "start_time" not in statement and 'FROM "Bom"' not in statement
    assert await repo.nhu_cau(1) == {2: 7}
    assert 'FROM "NhuCauLinhKien" WHERE "NhuCauLinhKien".yeu_cau_san_xuat_id = 1' in sql(session.execute.call_args.args[0])


# UC-26 D2: Repository ghi nhu cầu, giữ hàng và tăng đang giữ, không trừ tồn hoặc commit
async def test_repository_writes_holds_and_increments_reserved_balance_atomically():
    session = AsyncMock(spec=AsyncSession)
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    await repo.ghi_nhu_cau(1, {2: 7, 9: 14})
    rows = session.add_all.call_args.args[0]
    assert [(r.yeu_cau_san_xuat_id, r.mat_hang_id, r.so_luong_can) for r in rows] == [(1, 2, 7), (1, 9, 14)]
    assert all(isinstance(r, NhuCauLinhKien) for r in rows)
    await repo.giu_hang(1, [{"mat_hang_id": 2, "loai_giu": "linh_kien", "so_luong": 7}])
    hold = session.add.call_args.args[0]
    assert isinstance(hold, GiuHang)
    assert (hold.yeu_cau_san_xuat_id, hold.mat_hang_id, hold.loai_giu, hold.so_luong) == (1, 2, "linh_kien", 7)
    assert sql(session.execute.call_args.args[0]) == 'UPDATE "MatHang" SET so_luong_dang_giu=("MatHang".so_luong_dang_giu + 7) WHERE "MatHang".id = 2'
    assert session.flush.await_count == 2
    session.commit.assert_not_awaited()


# UC-26 D2: ORM mới khớp cột, FK, ràng buộc và index bootstrap
def test_reservation_orm_matches_bootstrap_contract():
    assert set(NhuCauLinhKien.__table__.columns.keys()) == {"id", "yeu_cau_san_xuat_id", "mat_hang_id", "so_luong_can"}
    assert {c.name for c in GiuHang.__table__.constraints if isinstance(c, CheckConstraint)} == {
        "ck_giu_hang_loai", "ck_giu_hang_trang_thai", "ck_giu_hang_so_luong",
        "ck_giu_hang_ket_thuc", "ck_giu_hang_da_xuat", "ck_giu_hang_nguon_sx",
    }
    assert {(i.name, tuple(c.name for c in i.columns), i.unique) for i in GiuHang.__table__.indexes} == {
        ("uq_giu_hang", ("yeu_cau_san_xuat_id", "mat_hang_id", "loai_giu"), True),
        ("ix_giu_hang_dang_giu", ("mat_hang_id",), False),
    }
    partial = next(i for i in GiuHang.__table__.indexes if i.name == "ix_giu_hang_dang_giu")
    assert str(partial.dialect_options["postgresql"]["where"]) == "trang_thai = 'dang_giu'"
    for model in (GiuHang, NhuCauLinhKien):
        assert all(fk.deferrable and fk.initially == "IMMEDIATE" for fk in model.__table__.foreign_keys)
    assert str(MatHang.__table__.c.so_luong_dang_giu.server_default.arg) == "0"
    assert MatHang.__table__.c.so_luong_dang_giu.nullable is False
    assert str(MatHang.__table__.c.so_luong_con_dung.computed.sqltext) == "so_luong_ton - so_luong_dang_giu"
    assert MatHang.__table__.c.so_luong_con_dung.computed.persisted is True


# UC-26 AC-1: Hàm thuần dùng còn dùng được và không sửa các đầu vào
def test_pure_calculation_uses_available_stock_without_mutating_inputs():
    request = request_record()
    quantities = {2: 1}
    available = {5: HangKhaDung("MH-000005", "Xe", "xe", 3), 2: HangKhaDung("MH-000002", "Khung", "cái", 4)}
    before = deepcopy((request, quantities, available))
    result = tinh_ket_qua_kiem_tra(request, quantities, available)
    assert (result.so_luong_dung_thanh_pham, result.so_luong_can_san_xuat) == (3, 7)
    assert result.linh_kien[0].so_luong_thieu == 3 and result.du_linh_kien is False
    assert (request, quantities, available) == before
    result = tinh_ket_qua_kiem_tra(request, quantities, {**available, 5: replace(available[5], so_luong_con_dung=20)})
    assert result.so_luong_dung_thanh_pham == 10 and result.so_luong_can_san_xuat == 0
    assert result.linh_kien == []
