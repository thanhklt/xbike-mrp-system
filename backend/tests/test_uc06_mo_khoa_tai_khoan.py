"""UC-06 service/ASGI contracts with isolated records and staged transactions."""

from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.core.errors import InvalidWorkflowState, UnauthorizedException
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
from app.modules.nhan_vien.models import NhanVien
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository, employee_credentials
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import EmployeeCredentials
from app.modules.nhan_vien.service import NhanVienService

URL = "/api/v1/nhan_vien"
PASSWORD = "UC06-test-password"


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash(PASSWORD)


@pytest.fixture
async def api(password_hash):
    def record(id_, role, status="hoat_dong"):
        return EmployeeCredentials(
            id=id_,
            ma_nhan_vien=f"NV-{id_:06d}",
            ten_dang_nhap=f"uc06-{id_}",
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
    repo = AsyncMock(spec=NhanVienRepository)
    audit, session = AsyncMock(), AsyncMock()

    def read(id_):
        return pending.get(id_, stored.get(id_))

    async def set_status(id_, status):
        user = read(id_)
        pending[id_] = user.model_copy(update={
            "trang_thai": status,
            "phien_ban_dang_nhap": user.phien_ban_dang_nhap + (status == "bi_khoa"),
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
    repo.set_status.side_effect = set_status
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

    def headers(id_, *, legacy=False):
        user = stored[id_]
        token = create_access_token(
            id_, user.roles,
            credential_version=password_version(user.password_hash),
            session_version=None if legacy else user.phien_ban_dang_nhap,
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
            etag=etag, headers=headers,
        )


async def unlock(api, id_=3, *, body=None, headers=None):
    return await api.client.post(
        f"{URL}/{id_}/mo_khoa", json=body,
        headers={"If-Match": await api.etag(id_), **(headers or {})},
    )


# UC-06 AC-1: không body, thiếu/null/rỗng/khoảng trắng vẫn mở khóa và lưu lý do null
@pytest.mark.parametrize("body", [None, {}, {"ly_do": None}, {"ly_do": ""}, {"ly_do": "   "}])
async def test_optional_reason_unlocks_account(api, body):
    old_etag = await api.etag(3)
    response = await unlock(api, body=body)
    assert response.status_code == 200
    assert response.json()["data"]["trang_thai"] == "hoat_dong"
    assert "phien_ban_dang_nhap" not in response.json()["data"]
    assert response.headers["etag"] != old_etag
    assert response.headers["etag"] == await api.etag(3)
    assert api.stored[3].trang_thai == "hoat_dong"
    assert len(api.history) == 1 and api.history[0].ly_do is None
    api.session.commit.assert_awaited_once()


# UC-06 AC-1: lý do tối đa 1000 ký tự, vượt giới hạn trả 422 và không ghi
@pytest.mark.parametrize("length,status", [(1000, 200), (1001, 422)])
async def test_reason_length_limit(api, length, status):
    response = await unlock(api, body={"ly_do": "x" * length})
    assert response.status_code == status
    if status == 422:
        assert any(d["field"] == "ly_do" for d in response.json()["error"]["details"])
        assert api.stored[3].trang_thai == "bi_khoa" and not api.history
        api.repo.set_status.assert_not_awaited()
        api.audit.append.assert_not_awaited()
    else:
        assert api.history[0].ly_do == "x" * length


# UC-06 AC-2: mở khóa giữ nguyên vai trò/hồ sơ và đăng nhập bằng mật khẩu hiện có
@pytest.mark.parametrize("role,role_id", [("nhan_vien", 3), ("quan_ly", 2), ("quan_tri_vien", 1)])
async def test_unlock_preserves_role_and_existing_password(api, role, role_id):
    api.stored[3] = api.stored[3].model_copy(update={
        "ma_vai_tro": role, "roles": [role], "vai_tro_id": role_id,
    })
    before = api.stored[3].model_copy()
    response = await unlock(api)
    assert response.status_code == 200
    assert api.stored[3] == before.model_copy(update={"trang_thai": "hoat_dong"})
    profile = response.json()["data"]
    assert (profile["vai_tro_id"], profile["ma_vai_tro"]) == (role_id, role)
    login = await api.client.post(
        "/api/v1/auth/dang_nhap", json={"ten_dang_nhap": "uc06-3", "mat_khau": PASSWORD}
    )
    assert login.status_code == 200
    data = login.json()["data"]
    assert data["nhan_vien"] == profile
    assert decode_access_token(data["access_token"])["roles"] == [role]


# UC-06 AC-3: audit mo_khoa thuộc ThaoTac v4, đúng actor/đích, trạng thái và lý do trim
async def test_unlock_audit_records_states_actor_and_reason(api):
    assert (await unlock(api, body={"ly_do": "  Khôi phục truy cập  "})).status_code == 200
    assert len(api.history) == 1
    entry = api.history[0]
    assert entry.thao_tac == "mo_khoa" and entry.thao_tac in get_args(ThaoTac)
    assert entry.nhan_vien_id == 1 and entry.doi_tuong_id == 3
    assert entry.loai_doi_tuong == "nhan_vien"
    assert entry.trang_thai_truoc == "bi_khoa" and entry.trang_thai_sau == "hoat_dong"
    assert entry.ly_do == "Khôi phục truy cập"
    assert entry.du_lieu_truoc["trang_thai"] == "bi_khoa"
    assert entry.du_lieu_sau == {**entry.du_lieu_truoc, "trang_thai": "hoat_dong"}
    assert "password_hash" not in entry.model_dump_json()
    assert api.stored[3].password_hash not in entry.model_dump_json()
    assert not LichSuThaoTac.__table__.c.created_at.nullable
    assert str(LichSuThaoTac.__table__.c.created_at.server_default.arg) == "now()"
    api.audit.append.assert_awaited_once_with(entry)


# UC-06 A2: đã mở với ETag hiện tại trả 409, ETag cũ trả 412, thiếu If-Match trả 428
@pytest.mark.parametrize("version,status,code", [
    ("current", 409, "trang_thai_khong_hop_le"),
    ("stale", 412, "du_lieu_da_thay_doi"),
    ("missing", 428, "thieu_if_match"),
])
async def test_changed_state_and_preconditions_do_not_write(api, version, status, code):
    old_etag = await api.etag(3)
    api.stored[3] = api.stored[3].model_copy(update={"trang_thai": "hoat_dong"})
    headers = {} if version == "missing" else {
        "If-Match": await api.etag(3) if version == "current" else old_etag,
    }
    response = await api.client.post(f"{URL}/3/mo_khoa", headers=headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    assert not api.history


# UC-06 A2: service từ chối mở lại tài khoản đã hoạt động mà không ghi lịch sử
async def test_service_rejects_already_active_account(api):
    actor = {"sub": "1", "roles": ["quan_tri_vien"],
             "pwdv": password_version(api.stored[1].password_hash)}
    with pytest.raises(InvalidWorkflowState):
        await api.service.unlock_employee(5, actor, await api.etag(5), None, "req-uc06")
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-06 A3: phiên trước khóa không hồi sinh sau mở khóa, đăng nhập lại cấp phiên dùng được
async def test_old_session_stays_revoked_after_unlock(api):
    login = await api.client.post(
        "/api/v1/auth/dang_nhap", json={"ten_dang_nhap": "uc06-5", "mat_khau": PASSWORD}
    )
    assert login.status_code == 200
    old_token = login.json()["data"]["access_token"]
    assert decode_access_token(old_token)["pbdn"] == 0
    old_headers = {"Authorization": f"Bearer {old_token}"}
    assert (await api.client.get("/api/v1/auth/me", headers=old_headers)).status_code == 200
    locked = await api.client.delete(f"{URL}/5", headers={"If-Match": await api.etag(5)})
    assert locked.status_code == 204
    assert api.stored[5].phien_ban_dang_nhap == 1
    assert (await api.client.get("/api/v1/auth/me", headers=old_headers)).status_code == 403
    assert (await unlock(api, 5)).status_code == 200
    assert api.stored[5].phien_ban_dang_nhap == 1
    denied = await api.client.get("/api/v1/auth/me", headers=old_headers)
    assert denied.status_code == 401
    assert denied.json()["error"]["message"] == "Please sign in again"
    assert denied.headers["www-authenticate"] == "Bearer"
    login = await api.client.post(
        "/api/v1/auth/dang_nhap", json={"ten_dang_nhap": "uc06-5", "mat_khau": PASSWORD}
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    assert decode_access_token(token)["pbdn"] == api.stored[5].phien_ban_dang_nhap == 1
    assert (await api.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )).status_code == 200


# UC-06 D1: thiếu claim coi là 0, chỉ hợp lệ khi phiên bản DB bằng 0
@pytest.mark.parametrize("version,status", [(0, 200), (1, 401), (2, 401)])
async def test_legacy_token_defaults_to_zero(api, version, status):
    api.stored[5] = api.stored[5].model_copy(update={"phien_ban_dang_nhap": version})
    response = await api.client.get("/api/v1/auth/me", headers=api.headers(5, legacy=True))
    assert response.status_code == status
    if status == 401:
        assert response.json()["error"]["message"] == "Please sign in again"


# UC-06 D1: khóa tăng đúng 1 cùng transaction trước audit/commit; mở khóa không tăng
async def test_version_changes_only_on_lock_in_same_transaction(api):
    before = api.stored[5].model_copy()

    async def append(entry):
        assert api.stored[5] == before
        assert api.pending[5].trang_thai == "bi_khoa"
        assert api.pending[5].phien_ban_dang_nhap == 1
        api.session.commit.assert_not_awaited()
        api.pending_history.append(entry)

    api.audit.append.side_effect = append
    response = await api.client.delete(f"{URL}/5", headers={"If-Match": await api.etag(5)})
    assert response.status_code == 204
    api.session.commit.assert_awaited_once()
    assert api.stored[5].phien_ban_dang_nhap == 1
    assert len(api.history) == 1 and api.history[0].thao_tac == "khoa"
    api.audit.append.side_effect = api.pending_history.append
    assert (await unlock(api, 5)).status_code == 200
    assert api.stored[5] == before.model_copy(update={"phien_ban_dang_nhap": 1})
    assert len(api.history) == 2 and api.history[1].thao_tac == "mo_khoa"


# UC-06 D1: repository tăng phiên bản bằng biểu thức SQL, mở khóa chỉ đổi trạng thái
@pytest.mark.parametrize("status", ["bi_khoa", "hoat_dong"])
async def test_repository_uses_sql_increment_for_lock_only(status):
    session = AsyncMock()
    repository = SqlAlchemyNhanVienRepository(session)
    repository.get_for_update = AsyncMock(return_value=object())
    await repository.set_status(5, status)
    session.execute.assert_awaited_once()
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    ))
    assert sql.startswith('UPDATE "NhanVien" SET ')
    assert f"trang_thai='{status}'" in sql
    assert 'WHERE "NhanVien".id = 5' in sql
    if status == "bi_khoa":
        assert 'phien_ban_dang_nhap=("NhanVien".phien_ban_dang_nhap + 1)' in sql
    else:
        assert "phien_ban_dang_nhap" not in sql
    repository.get_for_update.assert_awaited_once_with(5)
    session.commit.assert_not_awaited()


# UC-06 D1: ORM đúng kiểu/default/ràng buộc và credentials chuyển phiên bản từ ORM
def test_session_mapping_and_credentials(password_hash):
    table = NhanVien.__table__
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert "phien_ban_dang_nhap INTEGER DEFAULT 0 NOT NULL" in ddl
    assert "CHECK (phien_ban_dang_nhap >= 0)" in ddl
    assert "created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL" in ddl
    user = NhanVien(
        id=5, vai_tro_id=3, ma_nhan_vien="NV-000005", ten_dang_nhap="uc06-5",
        mat_khau=password_hash, trang_thai="hoat_dong", phien_ban_dang_nhap=7,
    )
    credentials = employee_credentials(user)
    assert credentials.phien_ban_dang_nhap == 7


# UC-06 D1: current_payload và get_current_user truyền đúng phiên bản
async def test_auth_propagates_session_version(api):
    api.stored[5] = api.stored[5].model_copy(update={"phien_ban_dang_nhap": 2})
    payload = decode_access_token(api.headers(5)["Authorization"].removeprefix("Bearer "))
    assert (await api.auth.get_current_user(payload)).id == 5
    stale = {**payload, "pbdn": 1}
    with pytest.raises(UnauthorizedException, match="Please sign in again"):
        await api.auth.get_current_user(stale)
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    assert api.stored[5].phien_ban_dang_nhap == 2


# UC-06 A5: QLK/NV gọi trực tiếp không được mở khóa hoặc ghi dữ liệu/lịch sử
@pytest.mark.parametrize("actor_id", [4, 5])
async def test_nonadmin_cannot_unlock(api, actor_id):
    response = await unlock(api, headers=api.headers(actor_id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    api.repo.lock_credentials_by_id.assert_not_awaited()
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-06 A6: audit/commit lỗi khi khóa hoặc mở khóa rollback cả trạng thái, phiên bản và audit
@pytest.mark.parametrize("failure", ["audit", "commit"])
@pytest.mark.parametrize("operation", ["lock", "unlock"])
async def test_failed_save_rolls_back_status_version_and_history(api, failure, operation):
    before = dict(api.stored)
    target = api.audit.append if failure == "audit" else api.session.commit
    target.side_effect = RuntimeError("save unavailable")
    if operation == "unlock":
        response = await unlock(api)
    else:
        response = await api.client.delete(f"{URL}/5", headers={"If-Match": await api.etag(5)})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    api.repo.set_status.assert_awaited_once_with(
        3 if operation == "unlock" else 5, "hoat_dong" if operation == "unlock" else "bi_khoa"
    )
    api.session.rollback.assert_awaited_once()
    assert api.stored == before and not api.history
    assert not api.pending and not api.pending_history
