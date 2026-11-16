"""UC-31: HTTP/service transactions and production posting SQL without a database."""

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenException, InvalidWorkflowState, UnauthorizedException
from app.core.exceptions import register_exception_handlers
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import (
    get_chung_tu_hoan_thanh_service,
    get_current_user_payload,
)
from app.modules.audit.ports import AuditWriter
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.san_xuat.models import ChungTuHoanThanhSx
from app.modules.san_xuat.ports import ChungTuHoanThanhRepository, YeuCauSanXuatRepository
from app.modules.san_xuat.repository.chung_tu_hoan_thanh_sx import (
    SqlAlchemyChungTuHoanThanhRepository,
)
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.router import chung_tu_hoan_thanh_router
from app.modules.san_xuat.schemas import ChungTuRead
from app.modules.san_xuat.service import chung_tu_hoan_thanh_sx as completion_service
from app.modules.san_xuat.service.chung_tu_hoan_thanh_sx import (
    ChungTuHoanThanhService,
    generate_chung_tu_etag,
)
from tests.test_uc26_kiem_tra_giu_hang import NOW, request_record

URL = "/api/v1/chung_tu_hoan_thanh_sx"
AT = datetime(2026, 11, 17, 2, tzinfo=timezone.utc)
MANAGER = {"sub": "10", "roles": ["quan_ly"]}


@pytest.fixture
async def api(monkeypatch):
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return AT.astimezone(tz)

    monkeypatch.setattr(completion_service, "datetime", FixedClock)
    data = {
        "request": request_record(
            trang_thai="dang_thuc_hien", started_at=NOW, so_luong_can_san_xuat=7,
            so_luong_dung_thanh_pham=3, kiem_tra_lan_dau_at=NOW,
        ),
        "completion": ChungTuRead(
            id=12, ma_phieu="HTSX-202611-000012", yeu_cau_san_xuat_id=1,
            so_luong_hoan_thanh=7, nhan_vien_id=20, trang_thai="cho_duyet",
            finish_time=NOW, created_at=NOW, updated_at=NOW, phien_ban=2,
            nguoi_xu_ly_id=None, xu_ly_at=None, ly_do_tu_choi=None,
        ),
        "stock": {5: 13, 2: 93, 9: 86}, "held": {5: 3, 2: 0, 9: 0},
        "stock_at": {5: NOW, 2: NOW, 9: NOW},
        "holds": [{"yeu_cau_san_xuat_id": 1, "mat_hang_id": 5,
                   "loai_giu": "thanh_pham_co_san", "so_luong": 3, "trang_thai": "dang_giu"}],
        "ledger": [{"id": 90, "mat_hang_id": 2, "so_luong_bien_dong": -7}], "history": [],
    }
    pending = None
    events = []
    repo = AsyncMock(spec=ChungTuHoanThanhRepository)
    requests = AsyncMock(spec=YeuCauSanXuatRepository)
    session, audit = AsyncMock(spec=AsyncSession), AsyncMock(spec=AuditWriter)

    def current():
        return pending if pending is not None else data

    async def lock_request(id_):
        nonlocal pending
        assert pending is None
        pending = deepcopy(data)
        events.append("request_lock")
        return pending["request"] if id_ == 1 else None

    async def lock_completion(id_):
        assert events[-1] == "request_lock"
        events.append("completion_lock")
        return current()["completion"] if id_ == 12 else None

    async def lock_product(id_):
        assert events[-1] == "completion_lock" and id_ == 5
        events.append("product_lock")

    async def approve(id_, version, actor, at):
        assert events[-1] == "product_lock" and id_ == 12
        before = pending["completion"]
        assert version == before.phien_ban and before.trang_thai == "cho_duyet"
        pending["completion"] = before.model_copy(update={
            "trang_thai": "da_duyet", "nguoi_xu_ly_id": actor, "xu_ly_at": at,
            "updated_at": at, "phien_ban": version + 1,
        })
        events.append("approve")
        return pending["completion"]

    async def scalar(statement, params):
        sql = " ".join(str(statement).split())
        assert pending is not None and pending["completion"].trang_thai == "da_duyet"
        if sql.startswith('UPDATE "MatHang"'):
            assert events[-1] == "approve"
            pending["stock"][params["id"]] += params["quantity"]
            pending["held"][params["id"]] += params["held"]
            pending["stock_at"][params["id"]] = params["at"]
            events.append("stock")
            return pending["stock"][params["id"]]
        assert sql.startswith('INSERT INTO "GiaoDichKho"') and events[-1] == "stock"
        assert "'nhap_san_pham_san_xuat'" in sql
        assert not any(row.get("chung_tu_hoan_thanh_sx_id") == params["source"] for row in pending["ledger"])
        pending["ledger"].append({
            "id": 91, "mat_hang_id": params["item"], "loai_giao_dich": "nhap_san_pham_san_xuat",
            "so_luong_bien_dong": params["quantity"], "so_luong_ton_sau": params["stock"],
            "chung_tu_hoan_thanh_sx_id": params["source"], "nhan_vien_id": params["actor"],
            "posted_at": params["time"],
        })
        events.append("ledger")
        return 91

    async def hold(request, item, quantity, source, at):
        assert events[-1] == "ledger"
        pending["holds"].append({
            "yeu_cau_san_xuat_id": request, "mat_hang_id": item, "so_luong": quantity,
            "loai_giu": "thanh_pham_san_xuat", "trang_thai": "dang_giu",
            "chung_tu_hoan_thanh_sx_id": source, "created_at": at,
        })
        events.append("hold")

    async def update_request(id_, changes):
        assert id_ == 1 and events[-1] == "ledger"
        before = pending["request"]
        pending["request"] = before.model_copy(update={
            **changes, "phien_ban": before.phien_ban + 1, "updated_at": AT,
        })
        events.append("complete_request")
        return pending["request"]

    async def append(entry):
        pending["history"].append(entry.model_copy(deep=True))

    async def commit():
        nonlocal pending
        assert pending is not None
        data.clear()
        data.update(pending)
        pending = None

    async def rollback():
        nonlocal pending
        pending = None

    repo.get_by_id.side_effect = lambda id_: current()["completion"] if id_ == 12 else None
    repo.get_for_update.side_effect = lock_completion
    repo.lock_product.side_effect, repo.approve.side_effect = lock_product, approve
    repo.hold_production.side_effect = hold
    requests.get_for_update.side_effect, requests.update.side_effect = lock_request, update_request
    audit.append.side_effect, session.scalar.side_effect = append, scalar
    session.commit.side_effect, session.rollback.side_effect = commit, rollback
    service = ChungTuHoanThanhService(
        repo, requests, audit, SqlAlchemyTransaction(session),
        inventory=SqlAlchemyInventoryRepository(session),
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(chung_tu_hoan_thanh_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "quan_ly")
        if role == "anonymous":
            raise UnauthorizedException()
        return {"sub": request.headers.get("x-user", "10"), "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_chung_tu_hoan_thanh_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        yield SimpleNamespace(data=data, repo=repo, requests=requests, session=session,
                              audit=audit, service=service, events=events, client=client)


async def approve(api, **headers):
    return await api.client.post(f"{URL}/12/duyet", json={}, headers={
        "If-Match": generate_chung_tu_etag(api.data["completion"]), **headers,
    })


def warehouse_request(api):
    api.data["request"] = api.data["request"].model_copy(update={
        "loai_yeu_cau": "nhap_kho", "so_luong": 3, "so_luong_can_san_xuat": 3,
        "so_luong_dung_thanh_pham": 0,
    })
    api.data["completion"] = api.data["completion"].model_copy(update={"so_luong_hoan_thanh": 3})
    api.data["holds"][0]["yeu_cau_san_xuat_id"] = 2


# UC-31 AC-1: Cộng đúng 7, giữ đúng nguồn, sổ kho và chứng từ mới, yêu cầu không đổi
async def test_ac1_delivery_receives_seven_and_holds_for_same_request(api):
    before = deepcopy(api.data)
    response = await approve(api)
    assert response.status_code == 200, response.text
    after = api.data["completion"]
    assert after.trang_thai == "da_duyet" and after.phien_ban == 3
    assert after.nguoi_xu_ly_id == 10 and after.xu_ly_at == after.updated_at == AT
    assert after.finish_time == NOW and after.nhan_vien_id == 20
    assert response.json()["data"] == after.model_dump(mode="json")
    assert set(response.json()) == {"data", "meta"} and response.json()["meta"]["request_id"]
    assert response.headers["etag"] == generate_chung_tu_etag(after)
    assert response.headers["etag"] != generate_chung_tu_etag(before["completion"])
    assert api.data["stock"][5] == 20 and api.data["held"][5] == 10
    assert api.data["stock"][5] - api.data["held"][5] == 10
    assert api.data["stock_at"][5] == AT
    assert api.data["ledger"] == before["ledger"] + [{
        "id": 91, "mat_hang_id": 5, "loai_giao_dich": "nhap_san_pham_san_xuat",
        "so_luong_bien_dong": 7, "so_luong_ton_sau": 20,
        "chung_tu_hoan_thanh_sx_id": 12, "nhan_vien_id": 10, "posted_at": AT,
    }]
    assert api.data["holds"] == before["holds"] + [{
        "yeu_cau_san_xuat_id": 1, "mat_hang_id": 5, "so_luong": 7,
        "loai_giu": "thanh_pham_san_xuat", "trang_thai": "dang_giu",
        "chung_tu_hoan_thanh_sx_id": 12, "created_at": AT,
    }]
    assert api.data["request"] == before["request"]
    assert api.events == ["request_lock", "completion_lock", "product_lock", "approve", "stock", "ledger", "hold"]
    api.session.commit.assert_awaited_once()


# UC-31 AC-4: Nhập kho 3 xe tăng còn dùng được 3, không giữ và yêu cầu Hoàn thành
async def test_ac4_warehouse_receives_three_without_hold_and_completes_request(api):
    warehouse_request(api)
    before = deepcopy(api.data)
    assert (await approve(api)).status_code == 200
    assert api.data["stock"][5] == 16 and api.data["held"][5] == 3
    assert api.data["stock"][5] - api.data["held"][5] == 13
    assert api.data["holds"] == before["holds"]
    api.repo.hold_production.assert_not_awaited()
    assert api.data["completion"].trang_thai == "da_duyet"
    assert api.data["request"].trang_thai == "hoan_thanh"
    assert api.data["request"].completed_at == AT
    assert api.data["request"].phien_ban == before["request"].phien_ban + 1
    assert api.data["ledger"][-1]["so_luong_bien_dong"] == 3
    assert api.data["ledger"][-1]["so_luong_ton_sau"] == 16
    assert api.events == ["request_lock", "completion_lock", "product_lock", "approve", "stock", "ledger", "complete_request"]


# UC-31 AC-1: R3 tồn, giữ và sổ kho linh kiện không thay đổi ở cả hai loại yêu cầu
@pytest.mark.parametrize("warehouse", [False, True])
async def test_components_stock_reservations_and_movements_are_unchanged(api, warehouse):
    if warehouse:
        warehouse_request(api)
    before = deepcopy(api.data)
    assert (await approve(api)).status_code == 200
    for item_id in (2, 9):
        assert api.data["stock"][item_id] == before["stock"][item_id]
        assert api.data["held"][item_id] == before["held"][item_id]
        assert api.data["stock_at"][item_id] == before["stock_at"][item_id]
        for key in ("holds", "ledger"):
            assert [x for x in api.data[key] if x["mat_hang_id"] == item_id] == [
                x for x in before[key] if x["mat_hang_id"] == item_id
            ]


# UC-31 AC-2: A2 người sau dùng ETag cũ bị 412, mới bị 409, không cộng lần hai
@pytest.mark.parametrize("warehouse", [False, True])
async def test_ac2_second_manager_cannot_post_twice(api, warehouse):
    if warehouse:
        warehouse_request(api)
    old = generate_chung_tu_etag(api.data["completion"])
    assert (await approve(api)).status_code == 200
    posted = deepcopy(api.data)
    for headers, expected in [({"If-Match": old}, 412), ({}, 409)]:
        response = await approve(api, **{"x-user": "11", **headers})
        assert response.status_code == expected
        assert response.json()["error"]["message"] == "Chứng từ đã thay đổi"
        assert api.data == posted
    assert len(api.data["ledger"]) == 2
    api.repo.approve.assert_awaited_once()
    api.session.commit.assert_awaited_once()
    assert api.session.rollback.await_count == 2


# UC-31 AC-3: R5 NV, Admin và chưa đăng nhập bị từ chối trước mọi ghi
@pytest.mark.parametrize("role,status", [("nhan_vien", 403), ("quan_tri_vien", 403), ("anonymous", 401)])
async def test_ac3_http_rejects_non_managers(api, role, status):
    before = deepcopy(api.data)
    assert (await approve(api, **{"x-role": role})).status_code == status
    assert api.data == before
    api.repo.get_by_id.assert_not_awaited()
    api.session.scalar.assert_not_awaited()
    api.session.commit.assert_not_awaited()


# UC-31 AC-3: Service trực tiếp cũng kiểm quyền, không dựa riêng router
@pytest.mark.parametrize("roles", [["nhan_vien"], ["quan_tri_vien"], []])
async def test_ac3_service_rejects_non_managers(api, roles):
    before = deepcopy(api.data)
    with pytest.raises(ForbiddenException):
        await api.service.duyet(12, {"sub": "20", "roles": roles}, generate_chung_tu_etag(before["completion"]), "test")
    assert api.data == before
    api.requests.get_for_update.assert_not_awaited()


# UC-31 D1: Nháp, từ chối, đã duyệt hoặc yêu cầu đã kết thúc đều 409 và không ghi
@pytest.mark.parametrize("document,request_state", [
    ("nhap", "dang_thuc_hien"), ("tu_choi", "dang_thuc_hien"),
    ("da_duyet", "dang_thuc_hien"), ("cho_duyet", "da_huy"),
    ("cho_duyet", "hoan_thanh"), ("cho_duyet", "da_gui"),
])
async def test_invalid_workflow_returns_document_changed(api, document, request_state):
    api.data["completion"] = api.data["completion"].model_copy(update={"trang_thai": document})
    api.data["request"] = api.data["request"].model_copy(update={"trang_thai": request_state})
    before = deepcopy(api.data)
    response = await approve(api)
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Chứng từ đã thay đổi"
    assert api.data == before
    api.repo.lock_product.assert_not_awaited()
    api.repo.approve.assert_not_awaited()


# UC-31 D1: If-Match bắt buộc và phải là strong ETag hiện hành của chứng từ
@pytest.mark.parametrize("etag,status", [(None, 428), ("", 428), ('"old"', 412), ('W/"old"', 412), ("*", 412)])
async def test_approval_requires_current_document_if_match(api, etag, status):
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/12/duyet", json={}, headers={} if etag is None else {"If-Match": etag})
    assert response.status_code == status
    assert response.json()["error"]["code"] == ("thieu_if_match" if status == 428 else "du_lieu_da_thay_doi")
    assert api.data == before
    api.session.scalar.assert_not_awaited()


# UC-31 D1: Body chỉ {}, query lạ, tài nguyên thiếu và ID sai không được ghi
@pytest.mark.parametrize("path,body,status", [
    ("12/duyet", {"so_luong_hoan_thanh": 9}, 422), ("12/duyet?force=true", {}, 422),
    ("0/duyet", {}, 422), ("13/duyet", {}, 404), (f"{2**31}/duyet", {}, 404),
])
async def test_http_input_and_missing_document(api, path, body, status):
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/{path}", json=body)
    assert response.status_code == status
    assert api.data == before
    api.repo.approve.assert_not_awaited()


# UC-31 D3: Audit duyệt đủ số nhập/ledger/giữ; chỉ nhập kho có audit hoàn tất yêu cầu
@pytest.mark.parametrize("warehouse", [False, True])
async def test_approval_audit_and_optional_request_completion_audit(api, warehouse):
    if warehouse:
        warehouse_request(api)
    before = deepcopy(api.data)
    await api.service.duyet(12, MANAGER, generate_chung_tu_etag(before["completion"]), "direct")
    history = api.data["history"]
    assert len(history) == (2 if warehouse else 1)
    document = history[-1]
    assert (document.nhan_vien_id, document.loai_doi_tuong, document.doi_tuong_id, document.thao_tac) == (
        10, "chung_tu_hoan_thanh_san_xuat", 12, "duyet",
    )
    assert (document.trang_thai_truoc, document.trang_thai_sau) == ("cho_duyet", "da_duyet")
    assert document.du_lieu_truoc == before["completion"].model_dump(mode="json")
    assert document.du_lieu_sau == {
        **api.data["completion"].model_dump(mode="json"), "so_luong_nhap": 3 if warehouse else 7,
        "giao_dich_kho_id": 91, "so_luong_ton_sau": 16 if warehouse else 20, "giu_hang": not warehouse,
    }
    if warehouse:
        entry = history[0]
        assert (entry.nhan_vien_id, entry.loai_doi_tuong, entry.doi_tuong_id, entry.thao_tac) == (
            10, "yeu_cau_san_xuat", 1, "hoan_tat",
        )
        assert (entry.trang_thai_truoc, entry.trang_thai_sau) == ("dang_thuc_hien", "hoan_thanh")
        assert entry.du_lieu_truoc == before["request"].model_dump(mode="json")
        assert entry.du_lieu_sau == api.data["request"].model_dump(mode="json")


# UC-31 D2: Audit hoặc commit lỗi rollback tồn/ledger/giữ/chứng từ/yêu cầu và lịch sử
@pytest.mark.parametrize("warehouse", [False, True])
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_failure_rolls_back_every_write(api, warehouse, failure):
    if warehouse:
        warehouse_request(api)
    before = deepcopy(api.data)
    if failure == "audit":
        async def fail(entry):
            raise RuntimeError("audit failed")
        api.audit.append.side_effect = fail
    else:
        api.session.commit.side_effect = RuntimeError("commit failed")
    response = await approve(api)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    assert api.data == before
    api.repo.approve.assert_awaited_once()
    assert api.session.scalar.await_count == 2
    assert ("complete_request" if warehouse else "hold") in api.events
    api.session.rollback.assert_awaited_once()


# UC-31 D3: Audit chứng từ lỗi sau audit hoàn tất yêu cầu vẫn rollback cả lịch sử đã ghi
async def test_second_audit_failure_rolls_back_request_history_and_all_stock_writes(api):
    warehouse_request(api)
    before = deepcopy(api.data)
    append = api.audit.append.side_effect
    count = 0

    async def fail_second(entry):
        nonlocal count
        count += 1
        await append(entry)
        if count == 2:
            raise RuntimeError("completion audit failed")

    api.audit.append.side_effect = fail_second
    with pytest.raises(RuntimeError, match="completion audit failed"):
        await api.service.duyet(12, MANAGER, generate_chung_tu_etag(before["completion"]), "test")
    assert count == 2 and api.data == before
    assert [call.args[0].thao_tac for call in api.audit.append.await_args_list] == ["hoan_tat", "duyet"]
    api.session.rollback.assert_awaited_once()
    api.session.commit.assert_not_awaited()


# UC-31 AC-2: SQL khóa yêu cầu/chứng từ FOR UPDATE, refresh và MatHang là khóa thứ ba
async def test_sql_request_document_and_product_locks():
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repo = SqlAlchemyChungTuHoanThanhRepository(session)
    assert await SqlAlchemyYeuCauSanXuatRepository(session).get_for_update(1) is None
    assert await repo.get_for_update(12) is None
    for invocation, table, id_ in zip(session.scalar.call_args_list, ["YeuCauSanXuat", "ChungTuHoanThanhSx"], [1, 12], strict=True):
        query = invocation.args[0]
        sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        assert f'FROM "{table}"' in sql and f'"{table}".id = {id_}' in sql
        assert sql.endswith("FOR UPDATE")
        assert query.get_execution_options()["populate_existing"] is True
    session.scalar.return_value = 5
    await repo.lock_product(5)
    statement, params = session.scalar.call_args.args
    assert str(statement) == 'SELECT id FROM "MatHang" WHERE id=:id FOR UPDATE'
    assert params == {"id": 5}


# UC-31 D2: SQL duyệt WHERE trạng thái + phiên bản, người xử lý/thời điểm và flush trước sổ
async def test_sql_approve_is_conditional_and_flushes():
    session = AsyncMock(spec=AsyncSession)
    repo = SqlAlchemyChungTuHoanThanhRepository(session)
    record = ChungTuHoanThanhSx(
        id=12, ma_phieu="HTSX-202611-000012", yeu_cau_san_xuat_id=1,
        so_luong_hoan_thanh=7, nhan_vien_id=20, trang_thai="da_duyet",
        finish_time=NOW, created_at=NOW, updated_at=AT, phien_ban=3,
        nguoi_xu_ly_id=10, xu_ly_at=AT,
    )
    session.scalar.return_value = record
    after = await repo.approve(12, 2, 10, AT)
    query = session.scalar.call_args.args[0]
    compiled = query.compile(dialect=postgresql.dialect())
    sql, params = str(compiled), compiled.params
    assert 'UPDATE "ChungTuHoanThanhSx" SET' in sql
    assert '"ChungTuHoanThanhSx".id = %(id_1)s' in sql
    assert '"ChungTuHoanThanhSx".trang_thai = %(trang_thai_1)s' in sql
    assert '"ChungTuHoanThanhSx".phien_ban = %(phien_ban_2)s' in sql
    assert params == {"trang_thai": "da_duyet", "updated_at": AT, "nguoi_xu_ly_id": 10,
                      "xu_ly_at": AT, "phien_ban_1": 1, "id_1": 12,
                      "trang_thai_1": "cho_duyet", "phien_ban_2": 2}
    assert after == ChungTuRead.model_validate(record)
    session.flush.assert_awaited_once()
    session.scalar.return_value = None
    with pytest.raises(InvalidWorkflowState, match="Chứng từ đã thay đổi"):
        await repo.approve(12, 2, 10, AT)


# UC-31 D2: SQL nhập dương có tồn sau, nguồn duy nhất, người duyệt và thời điểm; không commit
@pytest.mark.parametrize("hold", [False, True])
async def test_sql_receive_production_contract(hold):
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [20, 91]
    assert await SqlAlchemyInventoryRepository(session).receive_production(5, 7, 12, 10, AT, hold=hold) == (91, 20)
    update, insert = session.scalar.call_args_list
    assert " ".join(str(update.args[0]).split()) == (
        'UPDATE "MatHang" SET so_luong_ton=so_luong_ton+:quantity, '
        'so_luong_dang_giu=so_luong_dang_giu+:held, ton_kho_updated_at=:at WHERE id=:id RETURNING so_luong_ton'
    )
    assert update.args[1] == {"id": 5, "quantity": 7, "held": 7 if hold else 0, "at": AT}
    assert " ".join(str(insert.args[0]).split()) == (
        'INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich, so_luong_bien_dong,so_luong_ton_sau,'
        'chung_tu_hoan_thanh_sx_id, nhan_vien_id,posted_at) VALUES (:item,\'nhap_san_pham_san_xuat\', '
        ':quantity,:stock,:source,:actor,:time) RETURNING id'
    )
    assert insert.args[1] == {"item": 5, "quantity": 7, "stock": 20, "source": 12, "actor": 10, "time": AT}
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


# UC-31 D2: SQL giữ thành phẩm gắn chứng từ đúng nguồn và không kết thúc giữ
async def test_sql_hold_production_source_and_active_state():
    session = AsyncMock(spec=AsyncSession)
    await SqlAlchemyChungTuHoanThanhRepository(session).hold_production(1, 5, 7, 12, AT)
    statement, params = session.execute.call_args.args
    assert " ".join(str(statement).split()) == (
        'INSERT INTO "GiuHang" (yeu_cau_san_xuat_id,mat_hang_id,loai_giu, '
        'so_luong,trang_thai,chung_tu_hoan_thanh_sx_id,created_at) '
        "VALUES (:request,:item,'thanh_pham_san_xuat',:quantity,'dang_giu',:source,:at)"
    )
    assert params == {"request": 1, "item": 5, "quantity": 7, "source": 12, "at": AT}
    session.commit.assert_not_awaited()


# UC-31 D1: Ứng dụng thật đăng ký POST duyệt và DI dùng chung session cho inventory/transaction
def test_application_approval_route_and_inventory_wiring():
    from app.main import app

    assert set(app.openapi()["paths"][f"{URL}/{{id}}/duyet"]) == {"post"}
    session = Mock(spec=AsyncSession)
    service = get_chung_tu_hoan_thanh_service(session)
    assert service.inventory.session is session
    assert service.repository.session is session
    assert service.requests.session is session
    assert service.transaction.session is session
