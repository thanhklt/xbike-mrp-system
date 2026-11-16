"""UC-07 service/ASGI contracts and isolated SQL Core repository checks."""

from datetime import timedelta
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, call

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.errors import InvalidWorkflowState, LastActiveAdminException
from app.core.exceptions import register_exception_handlers
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    password_version,
)
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_auth_service, get_nhan_vien_service
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.schemas import ThaoTac
from app.modules.audit.service import AuditService
from app.modules.auth.router import router as auth_router
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import EmployeeCredentials, VaiTroRead
from app.modules.nhan_vien.service import NhanVienService

URL = "/api/v1/nhan_vien"
PASSWORD = "UC07-test-password"
ROLES = {1: "quan_tri_vien", 2: "quan_ly", 3: "nhan_vien"}
UNFINISHED = ("nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien")


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash(PASSWORD)


@pytest.fixture
async def api(password_hash):
    def record(id_, role, status="hoat_dong"):
        return EmployeeCredentials(
            id=id_,
            ma_nhan_vien=f"NV-{id_:06d}",
            ten_dang_nhap=f"uc07-{id_}",
            ho_ten=f"Người dùng {id_}",
            vai_tro_id={"quan_tri_vien": 1, "quan_ly": 2, "nhan_vien": 3}[role],
            ma_vai_tro=role,
            trang_thai=status,
            roles=[role],
            password_hash=password_hash,
            ngay_sinh=None,
            so_dien_thoai=None,
            email=None,
            ngay_vao_lam=None,
            he_so_luong=None,
        )

    stored = {
        1: record(1, "quan_tri_vien"),
        2: record(2, "quan_tri_vien"),
        3: record(3, "nhan_vien", "bi_khoa"),
        4: record(4, "quan_ly"),
        5: record(5, "nhan_vien"),
    }
    pending, history, pending_history = {}, [], []
    assignments = []
    roles = {
        id_: VaiTroRead(id=id_, ma_vai_tro=code, ten_vai_tro=code, mo_ta=None)
        for id_, code in ROLES.items()
    }
    repo = AsyncMock(spec=NhanVienRepository)
    audit, session = AsyncMock(), AsyncMock()

    def read(id_):
        return pending.get(id_, stored.get(id_))

    async def set_role(id_, role_id):
        user = read(id_)
        pending[id_] = user.model_copy(update={
            "vai_tro_id": role_id,
            "ma_vai_tro": ROLES[role_id],
            "roles": [ROLES[role_id]],
            "phien_ban_dang_nhap": user.phien_ban_dang_nhap + 1,
        })
        return pending[id_]

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
    repo.get_credentials_by_id.side_effect = read
    repo.lock_credentials_by_id.side_effect = read
    repo.find_by_username.side_effect = lambda name: next(
        (user for user in stored.values() if user.ten_dang_nhap == name), None
    )
    repo.count_active_admins.side_effect = lambda: sum(
        user.ma_vai_tro == "quan_tri_vien" and user.trang_thai == "hoat_dong"
        for user in stored.values()
    )
    repo.get_role.side_effect = roles.get
    repo.set_role.side_effect = set_role
    repo.count_unfinished_assigned_requests.side_effect = lambda id_: sum(
        employee_id == id_ and status in UNFINISHED
        for employee_id, status in assignments
    )
    audit.append.side_effect = pending_history.append
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    service = NhanVienService(repo, AuditService(audit), SqlAlchemyTransaction(session))
    auth = AuthService(service)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_nhan_vien_service] = lambda: service
    app.dependency_overrides[get_auth_service] = lambda: auth

    def headers(id_):
        user = stored[id_]
        token = create_access_token(
            id_, user.roles,
            credential_version=password_version(user.password_hash),
            session_version=user.phien_ban_dang_nhap,
        )
        return {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test", headers=headers(1),
    ) as client:
        async def etag(id_):
            response = await client.get(f"{URL}/{id_}")
            assert response.status_code == 200
            return response.headers["etag"]

        yield SimpleNamespace(
            client=client, repo=repo, audit=audit, session=session, service=service, auth=auth,
            stored=stored, pending=pending, history=history, pending_history=pending_history,
            etag=etag, headers=headers, assignments=assignments,
        )


async def change(api, id_=4, role_id=3, *, body=None, headers=None):
    return await api.client.put(
        f"{URL}/{id_}/vai_tro", json={"vai_tro_id": role_id, **(body or {})},
        headers={"If-Match": await api.etag(id_), **(headers or {})},
    )


# UC-07 AC-1: đổi giữa cả ba vai trò trả hồ sơ mới và ETag khớp GET
@pytest.mark.parametrize("id_,role_id", [(4, 3), (4, 1), (5, 1), (5, 2), (2, 2), (2, 3)])
async def test_change_between_all_roles(api, id_, role_id):
    before = dict(api.stored)
    old_etag = await api.etag(id_)
    response = await change(api, id_, role_id)
    assert response.status_code == 200
    assert response.json()["data"]["ma_vai_tro"] == ROLES[role_id]
    assert response.json()["data"]["vai_tro_id"] == role_id
    assert "phien_ban_dang_nhap" not in response.json()["data"]
    assert response.headers["etag"] != old_etag
    assert response.headers["etag"] == await api.etag(id_)
    expected = before[id_].model_copy(update={
        "vai_tro_id": role_id, "ma_vai_tro": ROLES[role_id], "roles": [ROLES[role_id]],
        "phien_ban_dang_nhap": 1,
    })
    assert api.stored == {**before, id_: expected}
    api.repo.set_status.assert_not_awaited()
    api.repo.update_profile.assert_not_awaited()
    api.repo.set_password_hash.assert_not_awaited()
    api.session.commit.assert_awaited_once()


# UC-07 AC-2: lý do thiếu/null/rỗng/khoảng trắng thành null và vẫn lưu thành công
@pytest.mark.parametrize("body", [{}, {"ly_do": None}, {"ly_do": ""}, {"ly_do": "   "}])
async def test_optional_reason(api, body):
    response = await change(api, body=body)
    assert response.status_code == 200
    assert len(api.history) == 1 and api.history[0].ly_do is None


# UC-07 AC-2: lý do tối đa 1000 ký tự, vượt giới hạn trả 422 mà không ghi
@pytest.mark.parametrize("length,status", [(1000, 200), (1001, 422)])
async def test_reason_length(api, length, status):
    before = dict(api.stored)
    response = await change(api, body={"ly_do": "x" * length})
    assert response.status_code == status
    if status == 422:
        assert any(d["field"] == "ly_do" for d in response.json()["error"]["details"])
        assert api.stored == before and not api.history
        api.repo.set_role.assert_not_awaited()
    else:
        assert api.history[0].ly_do == "x" * length


# UC-07 AC-3: NV không còn yêu cầu chưa kết thúc được nâng QTV và tăng số QTV hoạt động
async def test_promote_employee_increases_admin_count(api):
    assert await api.repo.count_active_admins() == 2
    assert (await change(api, 5, 1)).status_code == 200
    assert await api.repo.count_active_admins() == 3
    api.repo.count_unfinished_assigned_requests.assert_awaited_once_with(5)


# UC-07 AC-4: yêu cầu chờ bổ sung linh kiện và mọi trạng thái chưa kết thúc chặn đổi vai trò
@pytest.mark.parametrize("state", UNFINISHED)
@pytest.mark.parametrize("role_id", [1, 2])
async def test_unfinished_assignment_prevents_change(api, state, role_id):
    before = dict(api.stored)
    api.assignments.append((5, state))
    response = await change(api, 5, role_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "con_yeu_cau_chua_ket_thuc"
    assert response.json()["error"]["message"] == "Nhân viên còn yêu cầu sản xuất chưa kết thúc"
    assert api.stored == before and not api.history
    api.repo.set_role.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()


# UC-07 AC-5: NV được giao yêu cầu Nháp vẫn bị chặn dù tài khoản đang khóa
async def test_draft_assignment_blocks_locked_employee(api):
    before = api.stored[3]
    api.assignments.append((3, "nhap"))
    response = await change(api, 3, 1)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "con_yeu_cau_chua_ket_thuc"
    assert api.stored[3] == before and not api.history
    api.repo.set_role.assert_not_awaited()


# UC-07 AC-6: yêu cầu hoàn thành/đã hủy và yêu cầu của người khác không chặn NV
async def test_only_finished_own_assignments_allow_change(api):
    api.assignments.extend([(5, "hoan_thanh"), (5, "da_huy"), (3, "nhap")])
    assert (await change(api, 5, 2)).status_code == 200
    assert api.stored[5].ma_vai_tro == "quan_ly"


# UC-07 AC-6: SQL Core SQLite đếm đúng bốn trạng thái v4, bỏ qua người khác và trạng thái đã kết thúc
async def test_repository_counts_unfinished_v4_requests():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with AsyncSession(engine) as session:
            await session.execute(text(
                'CREATE TABLE "YeuCauSanXuat" ('
                'id INTEGER PRIMARY KEY, nhan_vien_duoc_giao_id INTEGER NOT NULL, '
                'trang_thai TEXT NOT NULL)'
            ))
            repository = SqlAlchemyNhanVienRepository(session)
            assert await repository.count_unfinished_assigned_requests(5) == 0
            states = (*UNFINISHED, "hoan_thanh", "da_huy")
            await session.execute(text(
                'INSERT INTO "YeuCauSanXuat" (id, nhan_vien_duoc_giao_id, trang_thai) '
                'VALUES (:id, :employee, :state)'
            ), [
                {"id": index + 1, "employee": employee, "state": state}
                for index, (employee, state) in enumerate(
                    [(5, state) for state in states] + [(8, state) for state in states]
                )
            ])
            assert await repository.count_unfinished_assigned_requests(5) == 4
            assert await repository.count_unfinished_assigned_requests(8) == 4
            assert await repository.count_unfinished_assigned_requests(99) == 0
            for state in UNFINISHED:
                await session.execute(text(
                    'DELETE FROM "YeuCauSanXuat" WHERE nhan_vien_duoc_giao_id = :id'
                ), {"id": 5})
                await session.execute(text(
                    'INSERT INTO "YeuCauSanXuat" (id, nhan_vien_duoc_giao_id, trang_thai) '
                    'VALUES (100, 5, :state)'
                ), {"state": state})
                assert await repository.count_unfinished_assigned_requests(5) == 1
    finally:
        await engine.dispose()


# UC-07 AC-7: mọi token cũ của QLK thành NV bị 401; đăng nhập lại dùng vai trò mới
async def test_role_change_revokes_existing_sessions(api):
    second_token = create_access_token(
        4, ["quan_ly"], expires_delta=timedelta(minutes=30),
        credential_version=password_version(api.stored[4].password_hash), session_version=0,
    )
    old_headers = [api.headers(4), {"Authorization": f"Bearer {second_token}"}]
    assert old_headers[0] != old_headers[1]
    for headers in old_headers:
        assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    assert (await change(api)).status_code == 200
    for headers in old_headers:
        response = await api.client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Please sign in again"
    login = await api.client.post("/api/v1/auth/dang_nhap", json={
        "ten_dang_nhap": "uc07-4", "mat_khau": PASSWORD,
    })
    assert login.status_code == 200
    data = login.json()["data"]
    assert data["nhan_vien"]["ma_vai_tro"] == "nhan_vien"
    assert decode_access_token(data["access_token"])["pbdn"] == 1
    response = await api.client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {data['access_token']}",
    })
    assert response.status_code == 200
    assert response.json()["data"]["ma_vai_tro"] == "nhan_vien"


# UC-07 AC-8: QTV đang hoạt động cuối cùng không tự hạ quyền; QTV khóa không được tính
@pytest.mark.parametrize("role_id", [2, 3])
async def test_last_active_admin_cannot_demote_self(api, role_id):
    api.stored[2] = api.stored[2].model_copy(update={"trang_thai": "bi_khoa"})
    before = dict(api.stored)
    response = await change(api, 1, role_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quan_tri_vien_cuoi_cung"
    assert response.json()["error"]["message"] == (
        "Không hạ quyền được Quản trị viên đang hoạt động cuối cùng"
    )
    assert api.stored == before and not api.history
    api.repo.set_role.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-07 A3: khóa VaiTro QTV trước actor và đích, sau đó kiểm tra vai trò và đếm QTV
async def test_demotion_uses_shared_role_lock_before_employee_locks(api):
    assert (await change(api, 2, 3)).status_code == 200
    calls = api.repo.mock_calls
    ordered = [
        call.lock_admin_role(), call.lock_credentials_by_id(1), call.get_for_update(2),
        call.get_role(3), call.count_active_admins(), call.set_role(2, 3),
    ]
    positions = [calls.index(item) for item in ordered]
    assert positions == sorted(positions)
    api.repo.count_unfinished_assigned_requests.assert_not_awaited()
    assert await api.repo.count_active_admins() == 1
    api.repo.set_role.reset_mock()
    response = await change(api, 1, 2)
    assert response.status_code == 409
    api.repo.set_role.assert_not_awaited()
    assert len(api.history) == 1 and api.stored[1].ma_vai_tro == "quan_tri_vien"


# UC-07 AC-9: đúng một audit doi_vai_tro v4, actor/đích, hồ sơ trước/sau và lý do trim
async def test_single_role_audit(api):
    assert (await change(api, body={"ly_do": "  Phân công mới  "})).status_code == 200
    assert len(api.history) == 1
    entry = api.history[0]
    assert entry.thao_tac == "doi_vai_tro" and entry.thao_tac in get_args(ThaoTac)
    assert entry.nhan_vien_id == 1 and entry.doi_tuong_id == 4
    assert entry.loai_doi_tuong == "nhan_vien" and entry.ly_do == "Phân công mới"
    assert entry.trang_thai_truoc is None and entry.trang_thai_sau is None
    assert entry.du_lieu_truoc["ma_vai_tro"] == "quan_ly"
    assert entry.du_lieu_truoc["vai_tro_id"] == 2
    assert entry.du_lieu_sau == {
        **entry.du_lieu_truoc, "ma_vai_tro": "nhan_vien", "vai_tro_id": 3,
    }
    assert api.stored[4].password_hash not in entry.model_dump_json()
    assert "phien_ban_dang_nhap" not in entry.model_dump_json()
    assert not LichSuThaoTac.__table__.c.created_at.nullable
    assert str(LichSuThaoTac.__table__.c.created_at.server_default.arg) == "now()"
    api.audit.append.assert_awaited_once_with(entry)


# UC-07 A2: vai trò hiện tại trả 409 trước R3/R4, không audit hoặc tăng phiên bản
@pytest.mark.parametrize("id_", [1, 4, 5])
async def test_same_role_is_rejected_without_writes(api, id_):
    api.stored[2] = api.stored[2].model_copy(update={"trang_thai": "bi_khoa"})
    api.assignments.append((5, "nhap"))
    before = dict(api.stored)
    response = await change(api, id_, api.stored[id_].vai_tro_id)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert response.json()["error"]["message"] == "Vai trò mới trùng vai trò hiện tại"
    api.repo.count_active_admins.assert_not_awaited()
    api.repo.count_unfinished_assigned_requests.assert_not_awaited()
    api.repo.set_role.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    assert api.stored == before and not api.history
    assert (await api.client.get("/api/v1/auth/me", headers=api.headers(id_))).status_code == 200


# UC-07 A5: còn QTV khác thì tự hạ quyền thành công, token hiện tại 401 và đăng nhập lại vai trò mới
async def test_self_change_ends_own_session(api):
    assert (await change(api, 1, 2)).status_code == 200
    assert (await api.client.get("/api/v1/auth/me")).status_code == 401
    assert api.stored[2].ma_vai_tro == "quan_tri_vien"
    login = await api.client.post("/api/v1/auth/dang_nhap", json={
        "ten_dang_nhap": "uc07-1", "mat_khau": PASSWORD,
    })
    assert login.status_code == 200
    assert login.json()["data"]["nhan_vien"]["ma_vai_tro"] == "quan_ly"
    assert api.history[0].nhan_vien_id == api.history[0].doi_tuong_id == 1


# UC-07 D4: set_role tăng phiên bản đúng 1 bằng SQL trong cùng câu UPDATE
async def test_repository_increments_session_in_role_update():
    session = AsyncMock()
    repository = SqlAlchemyNhanVienRepository(session)
    repository.get_for_update = AsyncMock(return_value=object())
    await repository.set_role(5, 1)
    session.execute.assert_awaited_once()
    sql = str(session.execute.await_args.args[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert sql.startswith('UPDATE "NhanVien" SET ')
    assert "vai_tro_id=1" in sql
    assert 'phien_ban_dang_nhap=("NhanVien".phien_ban_dang_nhap + 1)' in sql
    assert 'WHERE "NhanVien".id = 5' in sql
    repository.get_for_update.assert_awaited_once_with(5)
    session.commit.assert_not_awaited()


# UC-07 D4: vai trò và phiên bản chờ cùng transaction, audit ghi trước commit
async def test_role_and_version_are_staged_together(api):
    before = api.stored[4]

    async def append(entry):
        assert api.stored[4] == before
        assert api.pending[4].ma_vai_tro == "nhan_vien"
        assert api.pending[4].phien_ban_dang_nhap == 1
        api.session.commit.assert_not_awaited()
        api.pending_history.append(entry)

    api.audit.append.side_effect = append
    assert (await change(api)).status_code == 200
    api.session.commit.assert_awaited_once()
    assert api.stored[4].phien_ban_dang_nhap == 1 and len(api.history) == 1


# UC-07 A4: ETag cũ, thiếu If-Match hoặc vai trò không tồn tại không ghi dữ liệu
@pytest.mark.parametrize("version,role_id,status,code", [
    ("stale", 3, 412, "du_lieu_da_thay_doi"),
    ("missing", 3, 428, "thieu_if_match"),
    ("current", 99, 404, "khong_tim_thay"),
])
async def test_preconditions_and_missing_role(api, version, role_id, status, code):
    before = dict(api.stored)
    headers = {} if version == "missing" else {
        "If-Match": '"stale"' if version == "stale" else await api.etag(4),
    }
    response = await api.client.put(f"{URL}/4/vai_tro", json={"vai_tro_id": role_id}, headers=headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert api.stored == before and not api.history
    api.repo.set_role.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()


# UC-07 A8: QLK/NV gọi trực tiếp trả 403, không lấy khóa ghi hoặc lưu lịch sử
@pytest.mark.parametrize("id_", [4, 5])
async def test_nonadmin_cannot_change_role(api, id_):
    response = await change(api, headers=api.headers(id_))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    api.repo.lock_admin_role.assert_not_awaited()
    api.repo.lock_credentials_by_id.assert_not_awaited()
    api.repo.set_role.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-07 A9: audit/commit lỗi rollback vai trò, phiên bản, lịch sử và giữ token cũ hợp lệ
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_failed_save_rolls_back_role_version_and_audit(api, failure):
    before = dict(api.stored)
    headers = api.headers(4)
    target = api.audit.append if failure == "audit" else api.session.commit
    target.side_effect = RuntimeError("save unavailable")
    response = await change(api)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    api.repo.set_role.assert_awaited_once_with(4, 3)
    api.session.rollback.assert_awaited_once()
    assert api.stored == before and not api.history
    assert not api.pending and not api.pending_history
    assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200


# UC-07 A2: service từ chối vai trò trùng ngay cả khi gọi không qua HTTP
async def test_service_rejects_same_role(api):
    actor = {"sub": "1", "roles": ["quan_tri_vien"],
             "pwdv": password_version(api.stored[1].password_hash)}
    with pytest.raises(InvalidWorkflowState, match="Vai trò mới trùng"):
        await api.service.change_role(4, 2, actor, await api.etag(4), "req-uc07")
    api.repo.set_role.assert_not_awaited()


# UC-07 AC-8: service dùng lại LastActiveAdminException với thông báo riêng cho hạ quyền
async def test_service_reuses_last_admin_exception(api):
    api.stored[2] = api.stored[2].model_copy(update={"trang_thai": "bi_khoa"})
    actor = {"sub": "1", "roles": ["quan_tri_vien"],
             "pwdv": password_version(api.stored[1].password_hash)}
    with pytest.raises(LastActiveAdminException, match="Không hạ quyền"):
        await api.service.change_role(1, 2, actor, await api.etag(1), "req-uc07")
    api.repo.set_role.assert_not_awaited()
