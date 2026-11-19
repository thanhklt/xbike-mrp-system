"""UC-23: stateful service/ASGI contracts, without an application database."""

import re
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

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
from app.modules.mat_hang.ports import MatHangRepository
from app.modules.mat_hang.schemas import MatHangRead
from app.modules.mat_hang.service import MatHangAvailabilityService
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.service import NhanVienService
from app.modules.san_xuat.models import YeuCauSanXuat
from app.modules.san_xuat.ports import ProductionIssues, YeuCauSanXuatRepository
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.router import yeu_cau_sx_router
from app.modules.san_xuat.schemas import YeuCauCreate, YeuCauListQuery, YeuCauRead
from app.modules.san_xuat.service import YeuCauSanXuatService, generate_yeu_cau_etag
from app.shared.records import RecordPage

URL = "/api/v1/yeu_cau_san_xuat"
MANAGER = {"sub": "10", "roles": ["quan_ly"]}
EMPLOYEE = {"sub": "20", "roles": ["nhan_vien"]}
BODY = {
    "mat_hang_id": 1,
    "so_luong": 10,
    "han_hoan_thanh": "2026-12-01",
    "nhan_vien_duoc_giao_id": 20,
}


@pytest.fixture
async def api():
    stored, pending, history, pending_history = {}, {}, [], []
    inventory, reservations = {1: 50, 2: 90, 3: 7}, {1: 4, 2: 12, 3: 0}
    products = {
        id_: MatHangRead(
            id=id_, ma_mat_hang=f"MH-{id_:06d}", ten_mat_hang=name, sku=f"sku-{id_}",
            loai_mat_hang=kind, don_vi_tinh="xe" if kind == "thanh_pham" else "cai",
            mau_sac=None, mo_ta=None, don_gia=100, is_active=active,
            so_luong_ton=inventory[id_], so_luong_dang_giu=reservations[id_],
            so_luong_con_dung=inventory[id_] - reservations[id_], ton_kho_updated_at=None,
        )
        for id_, name, kind, active in [
            (1, "Mountain Pro", "thanh_pham", True),
            (2, "Bánh xe", "linh_kien", True),
            (3, "Kids Fun", "thanh_pham", False),
        ]
    }
    employees = {
        20: SimpleNamespace(id=20, ho_ten="Nhân viên A", trang_thai="hoat_dong", ma_vai_tro="nhan_vien"),
        21: SimpleNamespace(id=21, ho_ten="Nhân viên B", trang_thai="bi_khoa", ma_vai_tro="nhan_vien"),
        22: SimpleNamespace(id=22, ho_ten="Nhân viên C", trang_thai="hoat_dong", ma_vai_tro="nhan_vien"),
        10: SimpleNamespace(id=10, ho_ten="Quản lý", trang_thai="hoat_dong", ma_vai_tro="quan_ly"),
    }
    boms = {1: {"id": 102, "phien_ban": 2}, 3: {"id": 301, "phien_ban": 1}}
    repo = AsyncMock(spec=YeuCauSanXuatRepository)
    repo.work_statuses.return_value = {}
    repo.creator_identity.side_effect = lambda employee_id: (
        employees[employee_id].ho_ten, f"NV-{employee_id:06d}",
    )
    audit, session = AsyncMock(spec=AuditWriter), AsyncMock(spec=AsyncSession)
    item_repo = AsyncMock(spec=MatHangRepository)
    item_repo.inventory = inventory
    item_repo.reservations = reservations
    employee_repo = AsyncMock(spec=NhanVienRepository)
    issues = AsyncMock(spec=ProductionIssues)

    def read(id_):
        return pending.get(id_, stored.get(id_))

    async def add(payload, actor_id):
        id_ = len(stored) + 1
        now = datetime.now(timezone.utc)
        pending[id_] = YeuCauRead(
            id=id_, ma_yeu_cau_san_xuat=f"YCSX-202611-{id_:06d}",
            **payload.model_dump(), nhan_vien_id=actor_id, trang_thai="nhap",
            created_at=now, updated_at=now, completed_at=None, bom_id=None, gui_at=None,
            so_luong_dung_thanh_pham=None, so_luong_can_san_xuat=None,
            kiem_tra_lan_dau_at=None, started_at=None, huy_at=None, nguoi_huy_id=None,
            ly_do_huy=None, phien_ban=1,
        )
        return pending[id_]

    async def update(id_, changes):
        before = read(id_)
        pending[id_] = before.model_copy(update={
            **changes, "updated_at": datetime.now(timezone.utc), "phien_ban": before.phien_ban + 1,
        })
        return pending[id_]

    async def listing(params, actor_id):
        rows = [
            row for row in stored.values()
            if actor_id is None or (row.nhan_vien_duoc_giao_id == actor_id and row.trang_thai != "nhap")
        ]
        for name in ("trang_thai", "mat_hang_id", "nhan_vien_duoc_giao_id"):
            value = getattr(params, name)
            if value is not None:
                rows = [row for row in rows if getattr(row, name) == value]
        offset = (params.page - 1) * params.page_size
        return RecordPage(rows[offset:offset + params.page_size], len(rows))

    async def append(entry):
        pending_history.append(SimpleNamespace(**entry.model_dump(), created_at=datetime.now(timezone.utc)))

    async def commit():
        stored.update(pending)
        history.extend(pending_history)
        pending.clear()
        pending_history.clear()

    async def rollback():
        pending.clear()
        pending_history.clear()

    repo.get_by_id.side_effect = read
    repo.get_for_update.side_effect = read
    repo.add.side_effect = add
    repo.update.side_effect = update
    repo.list_entries.side_effect = listing
    repo.bom_dang_dung.side_effect = lambda id_: boms[id_]["id"]
    item_repo.lock_items.side_effect = lambda ids: [products[id_] for id_ in sorted(ids) if id_ in products]
    employee_repo.get_for_share.side_effect = employees.get
    audit.append.side_effect = append
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    transaction = SqlAlchemyTransaction(session)
    service = YeuCauSanXuatService(
        repo, audit, transaction, MatHangAvailabilityService(item_repo),
        NhanVienService(employee_repo, audit, transaction), issues,
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(yeu_cau_sx_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "quan_ly")
        if role == "anonymous":
            raise UnauthorizedException()
        return {"sub": request.headers.get("x-actor", "10"), "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_yeu_cau_san_xuat_service] = lambda: service
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test",
    ) as client:
        yield SimpleNamespace(
            client=client, service=service, repo=repo, audit=audit, session=session,
            stored=stored, pending=pending, history=history, pending_history=pending_history,
            products=products, employees=employees, boms=boms, item_repo=item_repo,
            employee_repo=employee_repo, issues=issues, inventory=inventory, reservations=reservations,
        )


async def create(api, **changes):
    response = await api.client.post(URL, json={**BODY, **changes})
    assert response.status_code == 201, response.text
    return response


async def send(api, created, **options):
    return await api.client.post(
        f"{URL}/{created.json()['data']['id']}/gui", json={},
        headers={"If-Match": created.headers["etag"], **options},
    )


def assert_stock_untouched(api):
    assert api.item_repo.inventory == api.inventory == {1: 50, 2: 90, 3: 7}
    assert api.item_repo.reservations == api.reservations == {1: 4, 2: 12, 3: 0}
    assert {id_: product.so_luong_ton for id_, product in api.products.items()} == api.inventory
    api.item_repo.update.assert_not_awaited()
    api.item_repo.read_items.assert_not_awaited()
    api.issues.co_phieu_da_ghi_so.assert_not_awaited()
    api.issues.huy_phieu_chua_ghi_so.assert_not_awaited()


# UC-23 AC-1: Tạo Nháp rồi gửi, nhân viên A thấy, tồn và giữ không đổi
async def test_create_send_and_assignee_visibility_without_stock_changes(api):
    created = await create(api)
    draft = created.json()["data"]
    assert draft["trang_thai"] == "nhap" and draft["bom_id"] is None and draft["gui_at"] is None
    assert draft["loai_yeu_cau"] == "xuat_giao" and draft["han_hoan_thanh"] == BODY["han_hoan_thanh"]
    assert draft["mat_hang_id"] == 1 and draft["so_luong"] == 10 and draft["nhan_vien_duoc_giao_id"] == 20
    assert created.headers["location"] == f"{URL}/1"
    assert created.headers["etag"] == generate_yeu_cau_etag(YeuCauRead.model_validate(draft))
    response = await send(api, created)
    assert response.status_code == 200, response.text
    sent = response.json()["data"]
    assert sent["trang_thai"] == "da_gui" and sent["gui_at"] is not None
    assert sent["phien_ban"] == 2 and response.headers["etag"] != created.headers["etag"]
    assert response.headers["etag"] == (await api.client.get(f"{URL}/1")).headers["etag"]
    assert sent["so_luong_dung_thanh_pham"] is None and sent["so_luong_can_san_xuat"] is None
    assert sent["kiem_tra_lan_dau_at"] is None and "lenh_san_xuat_ids" not in sent
    visible = await api.client.get(URL, headers={"x-role": "nhan_vien", "x-actor": "20"})
    assert visible.status_code == 200 and [row["id"] for row in visible.json()["data"]] == [1]
    other = await api.client.get(URL, headers={"x-role": "nhan_vien", "x-actor": "22"})
    assert other.status_code == 200 and other.json()["data"] == []
    api.item_repo.lock_items.assert_has_awaits([call({1}), call({1})])
    api.employee_repo.get_for_share.assert_has_awaits([call(20), call(20)])
    assert_stock_untouched(api)


# UC-23 AC-2: Thiếu hoặc null hạn/nhân viên bị từ chối, không tạo và không audit (A1)
@pytest.mark.parametrize("field", ["han_hoan_thanh", "nhan_vien_duoc_giao_id"])
@pytest.mark.parametrize("null", [False, True])
async def test_missing_required_field_creates_nothing(api, field, null):
    body = dict(BODY)
    if null:
        body[field] = None
    else:
        body.pop(field)
    response = await api.client.post(URL, json=body)
    assert response.status_code == 422
    assert any(detail["field"] == field for detail in response.json()["error"]["details"])
    assert not api.stored and not api.history and not api.pending
    api.repo.add.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-23 A1: Sai kiểu/ngày/loại/số lượng hoặc trường lạ không tạo dữ liệu
@pytest.mark.parametrize("changes", [
    {"han_hoan_thanh": "invalid"}, {"han_hoan_thanh": "2026-02-30"},
    {"loai_yeu_cau": "other"}, {"loai_yeu_cau": None}, {"so_luong": 0},
    {"so_luong": 2**31}, {"mat_hang_id": "1"}, {"nhan_vien_duoc_giao_id": "20"},
    {"ke_hoach_token": "old"},
])
async def test_invalid_create_body_is_rejected_without_writes(api, changes):
    response = await api.client.post(URL, json={**BODY, **changes})
    assert response.status_code == 422
    assert not api.stored and not api.history
    api.repo.add.assert_not_awaited()


# UC-23 AC-3: Đóng xác nhận giữ Nháp; nhân viên không thấy trong danh sách/chi tiết (A2)
async def test_unsent_draft_is_hidden_from_employee(api):
    await create(api)
    for actor in (20, 22):
        headers = {"x-role": "nhan_vien", "x-actor": str(actor)}
        for params in ({}, {"trang_thai": "nhap"}):
            response = await api.client.get(URL, headers=headers, params=params)
            assert response.status_code == 200
            assert response.json()["data"] == [] and response.json()["meta"]["total"] == 0
        assert (await api.client.get(f"{URL}/1", headers=headers)).status_code == 404
    assert api.stored[1].trang_thai == "nhap" and api.stored[1].bom_id is None
    assert [entry.thao_tac for entry in api.history] == ["tao"]
    api.repo.bom_dang_dung.assert_not_awaited()
    assert_stock_untouched(api)


# UC-23 AC-4: Chốt đúng id công thức đang dùng phiên bản 2 tại lúc gửi
async def test_send_freezes_current_bom_version_two(api):
    api.boms[1] = {"id": 101, "phien_ban": 1}
    created = await create(api)
    api.boms[1] = {"id": 102, "phien_ban": 2}
    response = await send(api, created)
    assert response.status_code == 200
    assert response.json()["data"]["bom_id"] == 102 == api.stored[1].bom_id
    api.repo.bom_dang_dung.assert_awaited_once_with(1)


# UC-23 AC-5: Linh kiện không được làm thành phẩm của yêu cầu
async def test_component_cannot_be_requested_as_finished_product(api):
    response = await api.client.post(URL, json={**BODY, "mat_hang_id": 2})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    assert "thành phẩm" in response.json()["error"]["message"]
    assert not api.stored and not api.history


# UC-23 AC-6: Thành phẩm Kids Fun đã ngừng không tạo được yêu cầu
async def test_inactive_product_cannot_create_request(api):
    response = await api.client.post(URL, json={**BODY, "mat_hang_id": 3})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "mat_hang_ngung_hoat_dong"
    assert not api.stored and not api.history


# UC-23 AC-7: Nhân viên bị khóa hoặc sai vai trò không được nhận yêu cầu mới
@pytest.mark.parametrize("employee_id", [21, 10])
async def test_locked_or_non_employee_assignee_cannot_create(api, employee_id):
    response = await api.client.post(URL, json={**BODY, "nhan_vien_duoc_giao_id": employee_id})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "nguoi_duoc_giao_khong_hop_le"
    assert not api.stored and not api.history


# UC-23 AC-8: Thành phẩm ngừng trong khi xác nhận bị từ chối và giữ nguyên Nháp (A3)
async def test_product_deactivated_before_confirmation_preserves_draft(api):
    created = await create(api)
    before = api.stored[1]
    api.products[1] = api.products[1].model_copy(update={"is_active": False})
    response = await send(api, created)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert "ngừng hoạt động" in response.json()["error"]["message"]
    assert api.stored[1] == before and api.stored[1].bom_id is None
    assert [entry.thao_tac for entry in api.history] == ["tao"]
    api.repo.bom_dang_dung.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    assert_stock_untouched(api)


# UC-23 A3: Nhân viên bị khóa trong khi xác nhận bị từ chối, không ghi gửi
async def test_assignee_locked_before_confirmation_preserves_draft(api):
    created = await create(api)
    before = api.stored[1]
    api.employees[20].trang_thai = "bi_khoa"
    response = await send(api, created)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "nguoi_duoc_giao_khong_hop_le"
    assert "bị khóa" in response.json()["error"]["message"]
    assert api.stored[1] == before and api.stored[1].gui_at is None
    assert [entry.thao_tac for entry in api.history] == ["tao"]
    api.repo.bom_dang_dung.assert_not_awaited()
    assert_stock_untouched(api)


# UC-23 AC-9: Đúng hai lịch sử tạo/gửi có người, thời điểm, đối tượng và trạng thái trước/sau
async def test_creation_and_sending_audit_have_actor_time_and_states(api):
    created = await create(api)
    assert (await send(api, created)).status_code == 200
    assert len(api.history) == 2
    assert [(entry.thao_tac, entry.trang_thai_truoc, entry.trang_thai_sau) for entry in api.history] == [
        ("tao", None, "nhap"), ("gui", "nhap", "da_gui"),
    ]
    for entry in api.history:
        assert entry.nhan_vien_id == 10
        assert entry.loai_doi_tuong == "yeu_cau_san_xuat" and entry.doi_tuong_id == 1
        assert entry.created_at.tzinfo is not None
        assert entry.du_lieu_sau["trang_thai"] == entry.trang_thai_sau
    assert api.history[0].du_lieu_truoc is None
    assert api.history[1].du_lieu_truoc["trang_thai"] == "nhap"
    assert api.history[0].created_at <= api.history[1].created_at


# UC-23 AC-10: Yêu cầu nhập kho 3 xe giữ loại, nhân viên thấy và tồn/giữ không đổi
async def test_stock_request_three_bikes_sends_without_stock_changes(api):
    created = await create(api, loai_yeu_cau="nhap_kho", so_luong=3)
    response = await send(api, created)
    assert response.status_code == 200
    data = response.json()["data"]
    assert (data["trang_thai"], data["loai_yeu_cau"], data["so_luong"]) == ("da_gui", "nhap_kho", 3)
    visible = await api.client.get(URL, headers={"x-role": "nhan_vien", "x-actor": "20"})
    assert visible.status_code == 200 and [row["id"] for row in visible.json()["data"]] == [1]
    assert_stock_untouched(api)


# UC-23 AC-1: D4 cho phép hạn quá khứ ở cả tạo và gửi
async def test_past_due_date_can_create_and_send(api):
    created = await create(api, han_hoan_thanh="2000-01-01")
    response = await send(api, created)
    assert response.status_code == 200
    assert response.json()["data"]["han_hoan_thanh"] == "2000-01-01"
    assert response.json()["data"]["trang_thai"] == "da_gui"


# UC-23 AC-1: Chỉ QLK được tạo/gửi, cả router và service kiểm quyền
@pytest.mark.parametrize("role,status", [("nhan_vien", 403), ("quan_tri_vien", 403), ("anonymous", 401)])
async def test_only_manager_can_create_and_send(api, role, status):
    created = await create(api)
    before = api.stored[1]
    headers = {"x-role": role, "x-actor": "20"}
    assert (await api.client.post(URL, json=BODY, headers=headers)).status_code == status
    assert (await send(api, created, **headers)).status_code == status
    assert api.stored[1] == before and len(api.history) == 1
    with pytest.raises(ForbiddenException):
        await api.service.create_entry(YeuCauCreate(**BODY), EMPLOYEE, "service-create")
    with pytest.raises(ForbiddenException):
        await api.service.gui(1, EMPLOYEE, created.headers["etag"], "service-send")


# UC-23 AC-1: Gửi phải có If-Match hiện hành; thiếu 428, cũ/weak/* 412
@pytest.mark.parametrize("etag,status", [(None, 428), ("", 428), ('"old"', 412), ('W/"old"', 412), ("*", 412)])
async def test_send_requires_current_etag(api, etag, status):
    await create(api)
    before = api.stored[1]
    response = await api.client.post(f"{URL}/1/gui", json={}, headers={} if etag is None else {"If-Match": etag})
    assert response.status_code == status
    assert response.json()["error"]["code"] == ("thieu_if_match" if status == 428 else "du_lieu_da_thay_doi")
    assert api.stored[1] == before and len(api.history) == 1


# UC-23 AC-1: Không gửi lại yêu cầu đã gửi; body gửi không nhận token/trường lạ
async def test_sent_request_and_legacy_send_body_are_rejected(api):
    created = await create(api)
    bad_body = await api.client.post(f"{URL}/1/gui", json={"ke_hoach_token": "legacy"}, headers={"If-Match": created.headers["etag"]})
    assert bad_body.status_code == 422 and api.stored[1].trang_thai == "nhap"
    sent = await send(api, created)
    assert sent.status_code == 200
    response = await api.client.post(f"{URL}/1/gui", json={}, headers={"If-Match": sent.headers["etag"]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert api.stored[1].phien_ban == 2 and len(api.history) == 2


# UC-23 AC-1: D1 gỡ cả hai endpoint tính/xem kế hoạch
@pytest.mark.parametrize("method,path", [("post", "tinh_ke_hoach"), ("get", "ke_hoach")])
async def test_legacy_planning_routes_are_removed(api, method, path):
    response = await api.client.request(method, f"{URL}/1/{path}")
    assert response.status_code == 404


# UC-23 AC-9: Audit gửi lỗi rollback trạng thái, BOM, thời điểm và phiên bản
async def test_send_audit_failure_rolls_back_all_changes(api):
    created = await create(api)
    before = api.stored[1]
    api.audit.append.side_effect = RuntimeError("audit unavailable")
    response = await send(api, created)
    assert response.status_code == 500
    assert api.stored[1] == before and api.stored[1].bom_id is None
    assert api.stored[1].gui_at is None and api.stored[1].phien_ban == 1
    assert len(api.history) == 1 and not api.pending and not api.pending_history
    api.session.rollback.assert_awaited_once()
    api.repo.update.assert_awaited_once()
    assert_stock_untouched(api)


# UC-23 AC-1: Service trực tiếp tạo/gửi trả cùng hợp đồng và phiên bản
async def test_service_create_send_and_list_contract(api):
    draft, etag = await api.service.create_entry(YeuCauCreate(**BODY), MANAGER, "direct-create")
    assert draft.data.trang_thai == "nhap" and draft.data.han_hoan_thanh == date(2026, 12, 1)
    sent, new_etag = await api.service.gui(draft.data.id, MANAGER, etag, "direct-send")
    assert sent.data.trang_thai == "da_gui" and sent.data.phien_ban == 2
    assert sent.meta.request_id == "direct-send" and new_etag != etag
    listing = await api.service.list_entries(YeuCauListQuery(), EMPLOYEE, "direct-list")
    assert [row.id for row in listing.data] == [draft.data.id] and listing.meta.total == 1


# UC-23 AC-4: Repository chỉ lấy BOM active đúng thành phẩm và khóa FOR SHARE, scalar_one
async def test_repository_locks_active_bom_for_correct_product():
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.scalar_one.return_value = 102
    session.execute.return_value = result
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    assert await repo.bom_dang_dung(1) == 102
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert 'SELECT "Bom".id' in sql
    assert '"Bom".mat_hang_id = 1' in sql and '"Bom".is_active IS true' in sql
    assert sql.endswith("FOR SHARE")
    result.scalar_one.assert_called_once_with()


# UC-23 AC-3: Repository loại Nháp trước COUNT/phân trang danh sách nhân viên (D5)
async def test_repository_employee_scope_excludes_drafts_before_paging():
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 0
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    page = await repo.list_entries(YeuCauListQuery(trang_thai="nhap"), 20)
    sql = str(session.scalar.call_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert '"YeuCauSanXuat".nhan_vien_duoc_giao_id = 20' in sql
    assert '"YeuCauSanXuat".trang_thai != \'nhap\'' in sql
    assert '"YeuCauSanXuat".trang_thai = \'nhap\'' in sql
    assert page.total == 0 and page.items == []


# UC-23 AC-1: Repository tăng phien_ban/updated_at mỗi update, không truy vấn lệnh (D1, D6)
async def test_repository_updates_version_without_loading_orders(api):
    await create(api)
    record = YeuCauSanXuat(**api.stored[1].model_dump())
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = record
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    old_time = record.updated_at
    first = await repo.update(1, {"so_luong": 11})
    second = await repo.update(1, {"so_luong": 11})
    assert (first.phien_ban, second.phien_ban) == (2, 3)
    assert first.updated_at >= old_time and second.updated_at >= first.updated_at
    assert first.so_luong == 11 and generate_yeu_cau_etag(first) != generate_yeu_cau_etag(second)
    session.execute.assert_not_awaited()
    session.scalars.assert_not_awaited()


# UC-23 A1: Mặt hàng hoặc nhân viên không tồn tại trả 404, không tạo yêu cầu/audit
@pytest.mark.parametrize("field", ["mat_hang_id", "nhan_vien_duoc_giao_id"])
async def test_missing_product_or_employee_creates_nothing(api, field):
    response = await api.client.post(URL, json={**BODY, field: 999})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "khong_tim_thay"
    assert not api.stored and not api.history
    api.repo.add.assert_not_awaited()


# UC-23 AC-1: ORM yêu cầu khớp cột/kiểu/null/default/khóa/ràng buộc/index của bootstrap v4
def test_request_orm_matches_v4_bootstrap_without_database():
    ddl = (Path(__file__).resolve().parents[2] / "infra/postgres/init.sql").read_text(encoding="utf-8")
    table_ddl = ddl.split('CREATE TABLE "YeuCauSanXuat" (', 1)[1].split('CREATE TABLE "NhuCauLinhKien"', 1)[0]
    definitions = dict(re.findall(r'^\s+"(\w+)" (.+)', table_ddl, re.MULTILINE))
    table = YeuCauSanXuat.__table__
    assert set(table.columns.keys()) == set(definitions)
    for name, definition in definitions.items():
        column = table.columns[name]
        kind = definition.split()[0].lower().rstrip(",")
        orm_type = str(column.type.compile(dialect=postgresql.dialect())).lower()
        assert orm_type == {"int": "integer", "timestamptz": "timestamp with time zone"}.get(kind, kind)
        assert column.nullable == ("NOT NULL" not in definition and "PRIMARY KEY" not in definition)
        assert column.primary_key == ("PRIMARY KEY" in definition)
        assert bool(column.unique) == ("UNIQUE" in definition)
        if name == "id":
            assert column.identity is not None and column.identity.always is False
        elif "DEFAULT" in definition:
            expected = definition.split("DEFAULT", 1)[1].strip().rstrip(",")
            if expected.startswith("(") and expected.endswith(")"):
                expected = expected[1:-1]
            assert str(column.server_default.arg) == expected
        else:
            assert column.server_default is None

    checks = {}
    for match in re.finditer(r'CONSTRAINT "(\w+)" CHECK \(', table_ddl):
        depth, end = 1, match.end()
        while depth:
            depth += (table_ddl[end] == "(") - (table_ddl[end] == ")")
            end += 1
        name = match[1].replace("ck_ycsx_trang_thai", "ck_yeu_cau_san_xuat_trang_thai")
        checks[name] = re.sub(r"\s+", "", table_ddl[match.end():end - 1])
    assert {
        constraint.name: re.sub(r"\s+", "", str(constraint.sqltext))
        for constraint in table.constraints if isinstance(constraint, CheckConstraint)
    } == checks
    foreign_keys = re.findall(
        r'ALTER TABLE "YeuCauSanXuat" ADD FOREIGN KEY \("(\w+)"\) REFERENCES "(\w+)" \("(\w+)"\) DEFERRABLE INITIALLY IMMEDIATE;', ddl,
    )
    assert {(fk.parent.name, fk.target_fullname, fk.deferrable, fk.initially) for fk in table.foreign_keys} == {
        (column, f"{target}.{key}", True, "IMMEDIATE") for column, target, key in foreign_keys
    }
    expected_indexes = re.findall(r'CREATE INDEX (\w+) ON "YeuCauSanXuat" \(([^)]+)\)', ddl)
    assert {index.name: list(index.columns.keys()) for index in table.indexes} == {
        name: columns.split(", ") for name, columns in expected_indexes
    }
