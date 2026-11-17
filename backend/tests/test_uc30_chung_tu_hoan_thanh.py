"""UC-30: stateful transactions and HTTP contracts, without PostgreSQL."""

import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
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
from app.dependencies import get_chung_tu_hoan_thanh_service, get_current_user_payload
from app.modules.audit.ports import AuditWriter
from app.modules.san_xuat.models import ChungTuHoanThanhSx
from app.modules.san_xuat.ports import ChungTuHoanThanhRepository, YeuCauSanXuatRepository
from app.modules.san_xuat.repository.chung_tu_hoan_thanh_sx import (
    SqlAlchemyChungTuHoanThanhRepository,
)
from app.modules.san_xuat.router import chung_tu_hoan_thanh_router, yeu_cau_sx_router
from app.modules.san_xuat.schemas import ChungTuCreate, ChungTuRead
from app.modules.san_xuat.service import chung_tu_hoan_thanh_sx as completion_service
from app.modules.san_xuat.service.chung_tu_hoan_thanh_sx import (
    ChungTuHoanThanhService,
    generate_chung_tu_etag,
)
from tests.test_uc26_kiem_tra_giu_hang import NOW, request_record

URL = "/api/v1/chung_tu_hoan_thanh_sx"
BY_REQUEST = "/api/v1/yeu_cau_san_xuat/1/chung_tu_hoan_thanh"
CONFIRMED_AT = datetime(2026, 11, 17, 2, 0, tzinfo=timezone.utc)
EMPLOYEE = {"sub": "20", "roles": ["nhan_vien"]}


@pytest.fixture
async def api(monkeypatch):
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return CONFIRMED_AT.astimezone(tz)

    monkeypatch.setattr(completion_service, "datetime", FixedClock)
    data = {
        "request": request_record(
            trang_thai="dang_thuc_hien", started_at=NOW,
            so_luong_can_san_xuat=7, so_luong_dung_thanh_pham=3,
            kiem_tra_lan_dau_at=NOW,
        ),
        "completion": None, "history": [],
        "stock": {5: 93}, "held": {5: 3},
        "holds": [{"mat_hang_id": 5, "so_luong": 3, "trang_thai": "dang_giu"}],
        "ledger": [{"mat_hang_id": 2, "so_luong_bien_dong": -7}],
    }
    pending = None
    events = []
    requests = AsyncMock(spec=YeuCauSanXuatRepository)
    repo = AsyncMock(spec=ChungTuHoanThanhRepository)
    audit, session = AsyncMock(spec=AuditWriter), AsyncMock(spec=AsyncSession)

    def current():
        return pending if pending is not None else data

    async def lock_request(id_):
        nonlocal pending
        assert pending is None
        pending = deepcopy(data)
        events.append("lock_request")
        return pending["request"] if id_ == 1 else None

    async def lock_completion(id_):
        assert pending is not None
        events.append("lock_completion")
        record = current()["completion"]
        return record if record and id_ == record.id else None

    async def add(request_id, quantity, actor_id):
        assert pending is not None and pending["completion"] is None
        pending["completion"] = ChungTuRead(
            id=12, ma_phieu="HTSX-202611-000012", yeu_cau_san_xuat_id=request_id,
            so_luong_hoan_thanh=quantity, nhan_vien_id=actor_id, trang_thai="nhap",
            finish_time=None, created_at=NOW, updated_at=NOW, nguoi_xu_ly_id=None,
            xu_ly_at=None, ly_do_tu_choi=None, phien_ban=1,
        )
        return pending["completion"]

    async def update(id_, changes):
        assert pending is not None and pending["completion"].id == id_
        before = pending["completion"]
        pending["completion"] = before.model_copy(update={
            **changes, "updated_at": CONFIRMED_AT, "phien_ban": before.phien_ban + 1,
        })
        return pending["completion"]

    async def append(entry):
        current()["history"].append(entry.model_copy(deep=True))

    async def commit():
        nonlocal pending
        assert pending is not None
        data.clear()
        data.update(pending)
        pending = None

    async def rollback():
        nonlocal pending
        pending = None

    def by_id(id_):
        record = current()["completion"]
        return record if record and record.id == id_ else None

    requests.get_for_update.side_effect = lock_request
    requests.get_by_id.side_effect = lambda id_: current()["request"] if id_ == 1 else None
    repo.get_by_id.side_effect = by_id
    repo.get_by_request.side_effect = lambda id_: current()["completion"] if id_ == 1 else None
    repo.get_for_update.side_effect, repo.add.side_effect = lock_completion, add
    repo.update.side_effect, audit.append.side_effect = update, append
    session.commit.side_effect, session.rollback.side_effect = commit, rollback
    service = ChungTuHoanThanhService(repo, requests, audit, SqlAlchemyTransaction(session))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(chung_tu_hoan_thanh_router, prefix="/api/v1")
    app.include_router(yeu_cau_sx_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "nhan_vien")
        if role == "anonymous":
            raise UnauthorizedException()
        return {"sub": request.headers.get("x-user", "20"), "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_chung_tu_hoan_thanh_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False),
                           base_url="http://test") as client:
        yield SimpleNamespace(data=data, repo=repo, requests=requests, audit=audit, session=session,
                              service=service, client=client, events=events)


async def create(api, **kwargs):
    return await api.client.post(URL, json={"yeu_cau_san_xuat_id": 1}, **kwargs)


async def send(api, **kwargs):
    return await api.client.post(f"{URL}/12/gui", json={}, headers={
        "If-Match": generate_chung_tu_etag(api.data["completion"]), **kwargs,
    })


def assert_unchanged(api, before):
    assert api.data == before
    api.repo.update.assert_not_awaited()
    api.audit.append.assert_not_awaited()


def reset_writes(api):
    api.repo.reset_mock()
    api.requests.reset_mock()
    api.audit.reset_mock()
    api.session.reset_mock()
    api.events.clear()


# UC-30 AC-1: Số lượng đúng 7 từ yêu cầu, Nháp chưa có thời điểm, ETag và Location chính xác
@pytest.mark.parametrize("kind", ["xuat_giao", "nhap_kho"])
async def test_create_fixed_quantity_draft(api, kind):
    api.data["request"] = api.data["request"].model_copy(update={"loai_yeu_cau": kind})
    response = await create(api)
    assert response.status_code == 201, response.text
    record = api.data["completion"]
    assert record.so_luong_hoan_thanh == 7
    assert record.finish_time is None and record.trang_thai == "nhap"
    assert record.phien_ban == 1 and record.nhan_vien_id == 20
    assert response.json()["data"] == record.model_dump(mode="json")
    assert set(response.json()) == {"data", "meta"}
    assert response.json()["meta"]["request_id"]
    assert response.headers["etag"] == generate_chung_tu_etag(record)
    assert response.headers["location"] == f"{URL}/12"
    api.repo.add.assert_awaited_once_with(1, 7, 20)
    assert api.requests.mock_calls == [call.get_for_update(1)]
    api.session.commit.assert_awaited_once()


# UC-30 AC-1: Không cho nhập/sửa số lượng; AC-2: Không cho nhập thời điểm; D1: input nghiêm ngặt
@pytest.mark.parametrize("extra", [
    {"so_luong_hoan_thanh": 8}, {"finish_time": "2026-11-16T08:00:00Z"},
    {"trang_thai": "cho_duyet"}, {"nhan_vien_id": 21},
])
async def test_create_rejects_server_owned_fields(api, extra):
    before = deepcopy(api.data)
    response = await api.client.post(URL, json={"yeu_cau_san_xuat_id": 1, **extra})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    assert response.json()["error"]["details"][0]["field"] == next(iter(extra))
    api.repo.add.assert_not_awaited()
    assert_unchanged(api, before)


# UC-30 AC-2: Gửi ghi đúng giờ xác nhận cố định và trả ETag mới, tăng phiên bản một lần
async def test_send_records_confirmation_time(api):
    draft = await create(api)
    response = await send(api)
    assert response.status_code == 200, response.text
    record = api.data["completion"]
    assert record.finish_time == CONFIRMED_AT
    assert record.trang_thai == "cho_duyet" and record.phien_ban == 2
    assert response.json()["data"] == record.model_dump(mode="json")
    assert response.headers["etag"] == generate_chung_tu_etag(record)
    assert response.headers["etag"] != draft.headers["etag"]


# UC-30 AC-2: Body gửi phải rỗng, không thể ghi đè thời điểm hoặc số lượng
@pytest.mark.parametrize("body", [{"finish_time": "2026-11-01T00:00:00Z"}, {"so_luong_hoan_thanh": 9}])
async def test_send_rejects_server_owned_fields(api, body):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/12/gui", json=body, headers={
        "If-Match": generate_chung_tu_etag(api.data["completion"]),
    })
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == next(iter(body))
    assert_unchanged(api, before)


# UC-30 AC-3: Gửi chỉ cập nhật chứng từ, không đọc/ghi tồn, giữ hàng hoặc giao dịch kho
async def test_send_leaves_stock_holds_and_ledger_untouched(api):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    assert (await send(api)).status_code == 200
    assert api.data["completion"].trang_thai == "cho_duyet"
    for key in ("request", "stock", "held", "holds", "ledger"):
        assert api.data[key] == before[key]
    assert api.requests.mock_calls == [call.get_for_update(1)]
    assert api.repo.mock_calls == [
        call.get_by_id(12), call.get_for_update(12), call.update(12, {
            "trang_thai": "cho_duyet", "finish_time": CONFIRMED_AT,
            "nguoi_xu_ly_id": None, "xu_ly_at": None, "ly_do_tu_choi": None,
        }),
    ]
    assert api.events == ["lock_request", "lock_completion"]


# UC-30 AC-4: A1 từ chối chứng từ thứ hai, nêu chính xác id hiện có và không tạo thêm
async def test_duplicate_completion_conflicts_with_existing_id(api):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    response = await create(api)
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Yêu cầu đã có chứng từ hoàn thành #12"
    api.repo.add.assert_not_awaited()
    assert_unchanged(api, before)
    api.session.commit.assert_not_awaited()


# UC-30 AC-5: A3 gửi lại trực tiếp, thời điểm mới và xóa toàn bộ thông tin từ chối cũ
async def test_resend_replaces_time_clears_rejection_and_audits(api):
    await create(api)
    old = api.data["completion"].model_copy(update={
        "trang_thai": "tu_choi", "finish_time": NOW, "nguoi_xu_ly_id": 10,
        "xu_ly_at": NOW, "ly_do_tu_choi": "Kiểm tra lại", "phien_ban": 3,
    })
    api.data["completion"] = old
    reset_writes(api)
    response = await send(api)
    assert response.status_code == 200
    after = api.data["completion"]
    assert after.finish_time == CONFIRMED_AT and after.finish_time != old.finish_time
    assert after.trang_thai == "cho_duyet" and after.phien_ban == 4
    assert after.nguoi_xu_ly_id is after.xu_ly_at is after.ly_do_tu_choi is None
    assert after.so_luong_hoan_thanh == old.so_luong_hoan_thanh == 7
    entry = api.data["history"][-1]
    assert (entry.thao_tac, entry.trang_thai_truoc, entry.trang_thai_sau, entry.nhan_vien_id) == (
        "gui_lai", "tu_choi", "cho_duyet", 20,
    )
    assert entry.du_lieu_truoc == old.model_dump(mode="json")
    assert entry.du_lieu_sau == after.model_dump(mode="json")
    assert entry.du_lieu_truoc["ly_do_tu_choi"] == "Kiểm tra lại"


# UC-30 A2: Chỉ đọc và không gọi gửi thì Nháp giữ nguyên, không ghi thời điểm hay lịch sử
async def test_read_without_confirmation_preserves_draft(api):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    for path in (f"{URL}/12", BY_REQUEST):
        response = await api.client.get(path)
        assert response.status_code == 200
        assert response.json()["data"]["finish_time"] is None
        assert response.json()["data"]["trang_thai"] == "nhap"
    assert_unchanged(api, before)
    api.session.commit.assert_not_awaited()


# UC-30 D2: R6 lịch sử tạo và gửi có đủ trạng thái, người thực hiện và snapshot
async def test_create_and_send_audit_full_snapshots(api):
    draft = await create(api)
    sent = await send(api)
    assert sent.status_code == 200
    assert len(api.data["history"]) == 2
    for entry, action, prior, after in zip(
        api.data["history"], ["tao", "gui"], [None, draft.json()["data"]],
        [draft.json()["data"], sent.json()["data"]], strict=True,
    ):
        assert (entry.nhan_vien_id, entry.loai_doi_tuong, entry.doi_tuong_id, entry.thao_tac) == (
            20, "chung_tu_hoan_thanh_san_xuat", 12, action,
        )
        assert entry.trang_thai_truoc == (prior["trang_thai"] if prior else None)
        assert entry.trang_thai_sau == after["trang_thai"]
        assert entry.du_lieu_truoc == prior and entry.du_lieu_sau == after


# UC-30 D2: Không lập nếu chưa bắt đầu, sai trạng thái hoặc số cần sản xuất không dương
@pytest.mark.parametrize("changes", [
    {"started_at": None}, {"trang_thai": "nhap"}, {"trang_thai": "da_gui"},
    {"trang_thai": "cho_bo_sung_linh_kien"}, {"trang_thai": "hoan_thanh"},
    {"trang_thai": "da_huy"}, {"so_luong_can_san_xuat": 0},
    {"so_luong_can_san_xuat": None}, {"so_luong_can_san_xuat": -1},
])
async def test_create_requires_started_active_positive_request(api, changes):
    api.data["request"] = api.data["request"].model_copy(update=changes)
    before = deepcopy(api.data)
    response = await create(api)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    api.repo.add.assert_not_awaited()
    assert_unchanged(api, before)


# UC-30 D2: Chỉ gửi Nháp/Bị từ chối khi yêu cầu vẫn Đang thực hiện
@pytest.mark.parametrize("completion_state,request_state", [
    ("cho_duyet", "dang_thuc_hien"), ("da_duyet", "dang_thuc_hien"),
    ("nhap", "da_huy"), ("tu_choi", "hoan_thanh"), ("nhap", "da_gui"),
])
async def test_send_rejects_invalid_document_or_request_state(api, completion_state, request_state):
    await create(api)
    api.data["completion"] = api.data["completion"].model_copy(update={"trang_thai": completion_state})
    api.data["request"] = api.data["request"].model_copy(update={"trang_thai": request_state})
    reset_writes(api)
    before = deepcopy(api.data)
    response = await send(api)
    assert response.status_code == 409
    assert_unchanged(api, before)


# UC-30 D3: QLK không lập/gửi, NV khác không lập/xem/gửi; xác thực bắt buộc
@pytest.mark.parametrize("headers,status", [
    ({"x-role": "quan_ly"}, 403), ({"x-user": "21"}, 403),
    ({"x-role": "quan_tri_vien"}, 403), ({"x-role": "anonymous"}, 401),
])
async def test_write_permissions(api, headers, status):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    for response in (await create(api, headers=headers), await send(api, **headers)):
        assert response.status_code == status
        assert response.json()["error"]["code"] == ("chua_xac_thuc" if status == 401 else "khong_co_quyen")
    api.repo.add.assert_not_awaited()
    assert_unchanged(api, before)


# UC-30 D3: QLK/NV được giao xem được qua cả hai GET; NV khác bị 403
# UC-33 D4: QLK đọc Nháp nhận 404 hoặc null không ETag; NV vẫn đọc được Nháp
@pytest.mark.parametrize("headers,status", [({}, 200), ({"x-role": "quan_ly"}, 404), ({"x-user": "21"}, 403)])
async def test_read_permissions_and_etag(api, headers, status):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    for path in (f"{URL}/12", BY_REQUEST):
        response = await api.client.get(path, headers=headers)
        expected_status = 200 if status == 404 and path == BY_REQUEST else status
        assert response.status_code == expected_status
        if status == 404:
            assert "etag" not in response.headers
            if path == BY_REQUEST:
                assert response.json()["data"] is None
        if status == 200:
            assert response.json()["data"] == before["completion"].model_dump(mode="json")
            assert response.headers["etag"] == generate_chung_tu_etag(before["completion"])
    assert_unchanged(api, before)


# UC-33 D4: QLK vẫn đọc Chờ duyệt qua hai GET với snapshot và ETag chính xác
async def test_manager_reads_submitted_completion_with_etag(api):
    await create(api)
    await send(api)
    reset_writes(api)
    before = deepcopy(api.data)
    for path in (f"{URL}/12", BY_REQUEST):
        response = await api.client.get(path, headers={"x-role": "quan_ly"})
        assert response.status_code == 200
        assert response.json()["data"] == before["completion"].model_dump(mode="json")
        assert response.headers["etag"] == generate_chung_tu_etag(before["completion"])
    assert_unchanged(api, before)
    api.session.commit.assert_not_awaited()


# UC-30 D3: Gọi trực tiếp service vẫn kiểm quyền, không phụ thuộc router
@pytest.mark.parametrize("actor", [{"sub": "10", "roles": ["quan_ly"]}, {"sub": "21", "roles": ["nhan_vien"]}])
async def test_service_enforces_write_permissions(api, actor):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    with pytest.raises(ForbiddenException):
        await api.service.tao(ChungTuCreate(yeu_cau_san_xuat_id=1), actor, "test")
    with pytest.raises(ForbiddenException):
        await api.service.gui(12, actor, generate_chung_tu_etag(before["completion"]), "test")
    assert_unchanged(api, before)


# UC-30 D1: Chưa có chứng từ trả data null, không có ETag và không ghi
async def test_request_without_completion_returns_null(api):
    before = deepcopy(api.data)
    response = await api.client.get(BY_REQUEST)
    assert response.status_code == 200
    assert response.json()["data"] is None
    assert response.json()["meta"]["request_id"]
    assert "etag" not in response.headers
    assert_unchanged(api, before)
    api.session.commit.assert_not_awaited()


# UC-30 D1: Thiếu hoặc vượt INT32 trả 404, id không dương trả 422, không đụng database
@pytest.mark.parametrize("id_,status", [(2, 404), (2**31, 404), (0, 422), (-1, 422)])
async def test_missing_resources_and_invalid_ids(api, id_, status):
    for response in (
        await api.client.get(f"{URL}/{id_}"),
        await api.client.post(f"{URL}/{id_}/gui", json={}),
        await api.client.get(BY_REQUEST.replace("/1/", f"/{id_}/")),
        await api.client.post(URL, json={"yeu_cau_san_xuat_id": id_}),
    ):
        assert response.status_code == status
    api.repo.add.assert_not_awaited()
    api.repo.update.assert_not_awaited()


# UC-30 D1: Query không được hỗ trợ bị 422 ở cả bốn endpoint
async def test_rejects_unsupported_query(api):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    for response in (
        await api.client.post(URL + "?force=true", json={"yeu_cau_san_xuat_id": 1}),
        await api.client.get(f"{URL}/12?force=true"),
        await api.client.post(f"{URL}/12/gui?force=true", json={}),
        await api.client.get(BY_REQUEST + "?force=true"),
    ):
        assert response.status_code == 422
    assert_unchanged(api, before)


# UC-30 D2: If-Match bắt buộc là ETag hiện hành, từ chối thiếu/cũ/weak/wildcard
@pytest.mark.parametrize("etag,status", [(None, 428), ("", 428), ('"old"', 412), ('W/"old"', 412), ("*", 412)])
async def test_send_requires_current_if_match(api, etag, status):
    await create(api)
    reset_writes(api)
    before = deepcopy(api.data)
    response = await api.client.post(f"{URL}/12/gui", json={}, headers={} if etag is None else {"If-Match": etag})
    assert response.status_code == status
    assert response.json()["error"]["code"] == ("thieu_if_match" if status == 428 else "du_lieu_da_thay_doi")
    assert_unchanged(api, before)


# UC-30 D2: ETag là hash toàn bản ghi, thay đổi số lượng mà giữ phiên bản vẫn bị 412
async def test_etag_hash_detects_changed_snapshot(api):
    draft = await create(api)
    api.data["completion"] = api.data["completion"].model_copy(update={"so_luong_hoan_thanh": 8})
    reset_writes(api)
    before = deepcopy(api.data)
    assert re.fullmatch(r'"[0-9a-f]{64}"', draft.headers["etag"])
    assert (await send(api, **{"If-Match": draft.headers["etag"]})).status_code == 412
    assert_unchanged(api, before)


# UC-30 D2: Audit/commit lỗi phải rollback cả tạo/gửi/gửi lại và lịch sử
@pytest.mark.parametrize("operation", ["tao", "gui", "gui_lai"])
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_failure_rolls_back_document_and_audit(api, operation, failure):
    if operation != "tao":
        await create(api)
        if operation == "gui_lai":
            api.data["completion"] = api.data["completion"].model_copy(update={
                "trang_thai": "tu_choi", "finish_time": NOW, "nguoi_xu_ly_id": 10,
                "xu_ly_at": NOW, "ly_do_tu_choi": "Kiểm tra lại",
            })
    reset_writes(api)
    before = deepcopy(api.data)
    if failure == "audit":
        api.audit.append.side_effect = RuntimeError("audit failed")
    else:
        api.session.commit.side_effect = RuntimeError("commit failed")
    response = await (create(api) if operation == "tao" else send(api))
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    assert api.data == before
    api.session.rollback.assert_awaited_once()
    if operation == "tao":
        api.repo.add.assert_awaited_once()
    else:
        api.repo.update.assert_awaited_once()


# UC-30 D5: Repository cấp mã từ nextval đúng bảng, tháng theo giờ Việt Nam và id sáu chữ số
async def test_next_code_uses_sequence_and_vietnam_month():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock()
    session.execute.return_value.one.return_value = (42, "202612")
    resource_id, code = await SqlAlchemyChungTuHoanThanhRepository(session).next_code()
    assert resource_id == 42 and code == "HTSX-202612-000042"
    assert re.fullmatch(r"HTSX-[0-9]{6}-[0-9]{6}", code)
    statement, params = session.execute.call_args.args
    assert str(statement) == (
        "SELECT nextval(pg_get_serial_sequence(:table_name, 'id')), "
        "to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMM')"
    )
    assert params == {"table_name": '"ChungTuHoanThanhSx"'}


# UC-30 D2: Adapter khóa đúng bảng, refresh sau chờ khóa, cập nhật tăng phiên bản
async def test_repository_lock_and_update():
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repo = SqlAlchemyChungTuHoanThanhRepository(session)
    assert await repo.get_for_update(12) is None
    query = session.scalar.call_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert 'FROM "ChungTuHoanThanhSx"' in sql and '"ChungTuHoanThanhSx".id = 12' in sql
    assert sql.endswith("FOR UPDATE")
    assert query.get_execution_options()["populate_existing"] is True
    record = ChungTuHoanThanhSx(
        id=12, ma_phieu="HTSX-202611-000012", yeu_cau_san_xuat_id=1,
        nhan_vien_id=20, so_luong_hoan_thanh=7, trang_thai="nhap",
        created_at=NOW, updated_at=NOW, phien_ban=1,
    )
    session.get.return_value = record
    after = await repo.update(12, {"trang_thai": "cho_duyet", "finish_time": CONFIRMED_AT})
    assert after.phien_ban == 2 and after.trang_thai == "cho_duyet"
    assert after.finish_time == CONFIRMED_AT and after.updated_at >= NOW
    session.flush.assert_awaited_once()


# UC-30 D5: Adapter lưu Nháp dùng id/mã được cấp, ORM/SQL bảo vệ duy nhất và trạng thái
async def test_repository_add_and_bootstrap_contract():
    session = AsyncMock(spec=AsyncSession)
    repo = SqlAlchemyChungTuHoanThanhRepository(session)
    repo.next_code = AsyncMock(return_value=(42, "HTSX-202611-000042"))

    async def defaults():
        record = session.add.call_args.args[0]
        record.trang_thai, record.phien_ban = "nhap", 1
        record.created_at = record.updated_at = NOW

    session.flush.side_effect = defaults
    record = await repo.add(1, 7, 20)
    assert (record.id, record.ma_phieu, record.so_luong_hoan_thanh, record.nhan_vien_id) == (
        42, "HTSX-202611-000042", 7, 20,
    )
    assert record.yeu_cau_san_xuat_id == 1 and record.finish_time is None
    assert record.trang_thai == "nhap" and record.phien_ban == 1
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    sql = (Path(__file__).resolve().parents[2] / "infra/postgres/init.sql").read_text(encoding="utf-8")
    assert '"yeu_cau_san_xuat_id" int UNIQUE NOT NULL' in sql
    assert "CHECK (so_luong_hoan_thanh > 0)" in sql
    assert "CHECK (trang_thai = 'nhap' OR finish_time IS NOT NULL)" in sql
    assert "'gui', 'gui_lai'" in sql
    assert 'trg_hoan_thanh_bat_bien BEFORE UPDATE OR DELETE ON "ChungTuHoanThanhSx"' in sql


# UC-30 D1: Ứng dụng thật đăng ký đúng API mới, không thêm danh sách/duyệt/từ chối
# UC-33 D1: Bổ sung GET danh sách bên cạnh POST lập chứng từ
def test_application_registers_only_uc30_completion_routes():
    from app.main import app

    paths = app.openapi()["paths"]
    assert {path: set(methods) for path, methods in paths.items() if path.startswith(URL)} == {
        URL: {"post", "get"}, f"{URL}/cua_toi": {"get"}, f"{URL}/{{id}}": {"get"}, f"{URL}/{{id}}/gui": {"post"},
        f"{URL}/{{id}}/duyet": {"post"},
        f"{URL}/{{id}}/tu_choi": {"post"},
    }
    assert BY_REQUEST.replace("/1/", "/{id}/") in paths
