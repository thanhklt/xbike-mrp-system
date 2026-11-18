"""UC-08 service/ASGI contracts with staged writes and isolated SQL compilation."""

from datetime import timedelta
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.core.errors import ForbiddenException
from app.core.exceptions import register_exception_handlers
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    password_version,
    verify_password,
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
from app.modules.nhan_vien.schemas import EmployeeCredentials
from app.modules.nhan_vien.service import NhanVienService

URL = "/api/v1/nhan_vien"
PASSWORD = "UC08-old-password"
NEW_PASSWORD = "123456"


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash(PASSWORD)


@pytest.fixture
async def api(password_hash):
    def record(id_, role, status="hoat_dong"):
        return EmployeeCredentials(
            id=id_, ma_nhan_vien=f"NV-{id_:06d}", ten_dang_nhap=f"uc08-{id_}",
            ho_ten=f"Người dùng {id_}",
            vai_tro_id={"quan_tri_vien": 1, "quan_ly": 2, "nhan_vien": 3}[role],
            ma_vai_tro=role, trang_thai=status, roles=[role], password_hash=password_hash,
            ngay_sinh=None, so_dien_thoai=None, email=None, ngay_vao_lam=None,
            he_so_luong=None, phien_ban_dang_nhap=2,
        )

    stored = {
        1: record(1, "quan_tri_vien"), 2: record(2, "quan_tri_vien"),
        3: record(3, "nhan_vien", "bi_khoa"), 4: record(4, "quan_ly"),
        5: record(5, "nhan_vien"),
    }
    pending, history, pending_history = {}, [], []
    repo = AsyncMock(spec=NhanVienRepository)
    audit, session = AsyncMock(), AsyncMock()

    def read(id_):
        return pending.get(id_, stored.get(id_))

    async def set_password_hash(id_, new_hash):
        user = read(id_)
        pending[id_] = user.model_copy(update={
            "password_hash": new_hash, "phien_ban_dang_nhap": user.phien_ban_dang_nhap + 1,
        })

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
    repo.set_password_hash.side_effect = set_password_hash
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
            id_, user.roles, credential_version=password_version(user.password_hash),
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
            client=client, repo=repo, audit=audit, session=session, service=service,
            stored=stored, pending=pending, history=history, pending_history=pending_history,
            etag=etag, headers=headers,
        )


async def reset(api, id_=5, password=NEW_PASSWORD, *, headers=None, extra=None):
    return await api.client.post(
        f"{URL}/{id_}/dat_lai_mat_khau",
        json={"mat_khau_moi": password, **(extra or {})},
        headers={"If-Match": await api.etag(id_), **(headers or {})},
    )


async def login(api, id_, password):
    return await api.client.post("/api/v1/auth/dang_nhap", json={
        "ten_dang_nhap": f"uc08-{id_}", "mat_khau": password,
    })


# UC-08 AC-1: QTV đổi cho mọi vai trò/trạng thái, chỉ hash và phiên bản thay đổi
@pytest.mark.parametrize("id_", [2, 3, 4, 5])
async def test_admin_resets_any_account(api, id_):
    before = dict(api.stored)
    response = await reset(api, id_)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == id_
    assert "mat_khau" not in response.json()["data"]
    assert "phien_ban_dang_nhap" not in response.json()["data"]
    assert response.headers["etag"] == await api.etag(id_)
    after = api.stored[id_]
    assert verify_password(NEW_PASSWORD, after.password_hash)
    assert after.phien_ban_dang_nhap == before[id_].phien_ban_dang_nhap + 1
    assert api.stored == {**before, id_: before[id_].model_copy(update={
        "password_hash": after.password_hash, "phien_ban_dang_nhap": 3,
    })}
    api.repo.set_role.assert_not_awaited()
    api.repo.set_status.assert_not_awaited()
    api.repo.update_profile.assert_not_awaited()
    api.session.commit.assert_awaited_once()
    if after.trang_thai == "hoat_dong":
        assert (await login(api, id_, NEW_PASSWORD)).status_code == 200
    else:
        assert (await login(api, id_, NEW_PASSWORD)).status_code == 403


# UC-08 AC-2: sau đổi mật khẩu cũ bị từ chối đăng nhập
async def test_old_password_is_rejected(api):
    assert (await reset(api)).status_code == 200
    response = await login(api, 5, PASSWORD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "thong_tin_dang_nhap_khong_hop_le"
    assert len(api.history) == 1


# UC-08 AC-3: 5 ký tự bị từ chối không ghi; 6 ký tự hợp lệ, không trim mật khẩu
@pytest.mark.parametrize("password,status", [("12345", 422), ("123456", 200), (" 12345", 200)])
async def test_password_minimum(api, password, status):
    before = dict(api.stored)
    response = await reset(api, password=password)
    assert response.status_code == status
    if status == 422:
        assert any(d["field"] == "mat_khau_moi" for d in response.json()["error"]["details"])
        assert api.stored == before and not api.history
        api.repo.set_password_hash.assert_not_awaited()
        api.audit.append.assert_not_awaited()
        api.session.commit.assert_not_awaited()
    else:
        assert verify_password(password, api.stored[5].password_hash)


# UC-08 AC-4: mọi token cũ của đích trả 401 ngay, phiên QTV khác vẫn dùng được
async def test_all_existing_sessions_end(api):
    user = api.stored[5]
    second_token = create_access_token(
        5, user.roles, expires_delta=timedelta(minutes=30),
        credential_version=password_version(user.password_hash), session_version=2,
    )
    old_headers = [api.headers(5), {"Authorization": f"Bearer {second_token}"}]
    assert old_headers[0] != old_headers[1]
    for headers in old_headers:
        assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    assert (await reset(api)).status_code == 200
    for headers in old_headers:
        response = await api.client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Please sign in again"
    assert (await api.client.get("/api/v1/auth/me")).status_code == 200
    response = await login(api, 5, NEW_PASSWORD)
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    assert decode_access_token(token)["pbdn"] == 3
    assert (await api.client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })).status_code == 200


# UC-08 AC-4: tăng phiên bản SQL đúng 1 trong cùng UPDATE với hash, không tự commit
async def test_repository_updates_hash_and_version_together():
    session = AsyncMock()
    await SqlAlchemyNhanVienRepository(session).set_password_hash(5, "new-hash")
    session.execute.assert_awaited_once()
    sql = str(session.execute.await_args.args[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    ))
    assert sql.startswith('UPDATE "NhanVien" SET ')
    assert "mat_khau='new-hash'" in sql
    assert 'phien_ban_dang_nhap=("NhanVien".phien_ban_dang_nhap + 1)' in sql
    assert 'WHERE "NhanVien".id = 5' in sql
    session.commit.assert_not_awaited()


# UC-08 AC-5: tự đổi chỉ cần mật khẩu mới, kể cả QTV hoạt động cuối, token hiện tại 401
async def test_self_reset_ends_admin_session(api):
    api.stored[2] = api.stored[2].model_copy(update={"trang_thai": "bi_khoa"})
    assert (await reset(api, 1)).status_code == 200
    assert (await api.client.get("/api/v1/auth/me")).status_code == 401
    response = await login(api, 1, NEW_PASSWORD)
    assert response.status_code == 200
    assert decode_access_token(response.json()["data"]["access_token"])["pbdn"] == 3
    assert api.history[0].nhan_vien_id == api.history[0].doi_tuong_id == 1


# UC-08 AC-5: gửi mật khẩu hiện tại bị extra=forbid từ chối, không ghi hoặc kết thúc phiên
async def test_current_password_is_not_accepted(api):
    before = dict(api.stored)
    response = await reset(api, 1, extra={"mat_khau_hien_tai": PASSWORD})
    assert response.status_code == 422
    assert api.stored == before and not api.history
    api.repo.set_password_hash.assert_not_awaited()
    assert (await api.client.get("/api/v1/auth/me")).status_code == 200


# UC-08 AC-6: QLK/NV gọi đổi cho mình hoặc người khác đều 403 không ghi
@pytest.mark.parametrize("actor_id", [4, 5])
@pytest.mark.parametrize("own", [False, True])
async def test_nonadmin_cannot_reset(api, actor_id, own):
    before = dict(api.stored)
    response = await reset(api, actor_id if own else 2, headers=api.headers(actor_id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    assert api.stored == before and not api.history
    api.repo.lock_credentials_by_id.assert_not_awaited()
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-08 AC-6: API tự phục vụ đã gỡ, mọi vai trò gọi lại nhận 404
@pytest.mark.parametrize("actor_id", [1, 4, 5])
async def test_self_service_route_is_removed(api, actor_id):
    response = await api.client.post("/api/v1/auth/doi_mat_khau", headers=api.headers(actor_id),
                                     json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD})
    assert response.status_code == 404
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-08 AC-6: gọi service trực tiếp vẫn kiểm tra quyền QTV
async def test_service_requires_admin(api):
    with pytest.raises(ForbiddenException):
        await api.service.reset_password(5, NEW_PASSWORD, {"sub": "5", "roles": ["nhan_vien"]},
                                         await api.etag(5), "req-uc08")
    api.repo.set_password_hash.assert_not_awaited()


# UC-08 AC-7: đúng một lịch sử doi_mat_khau v4 có actor/đích/thời điểm, không bí mật
async def test_safe_password_audit(api):
    old_hash = api.stored[5].password_hash
    assert (await reset(api)).status_code == 200
    assert len(api.history) == 1
    entry = api.history[0]
    assert entry.thao_tac == "doi_mat_khau" and entry.thao_tac in get_args(ThaoTac)
    assert entry.nhan_vien_id == 1 and entry.doi_tuong_id == 5
    assert entry.loai_doi_tuong == "nhan_vien"
    assert entry.du_lieu_truoc is None and entry.du_lieu_sau == {"da_doi_mat_khau": True}
    assert entry.ly_do is None
    assert entry.trang_thai_truoc is None and entry.trang_thai_sau is None
    for secret in [PASSWORD, NEW_PASSWORD, old_hash, api.stored[5].password_hash]:
        assert secret not in entry.model_dump_json()
    assert not LichSuThaoTac.__table__.c.created_at.nullable
    assert str(LichSuThaoTac.__table__.c.created_at.server_default.arg) == "now()"
    api.audit.append.assert_awaited_once_with(entry)


# UC-08 A6: ETag cũ/thiếu If-Match/đích không tồn tại không đổi mật khẩu hoặc phiên
@pytest.mark.parametrize("id_,etag,status,code", [
    (5, '"stale"', 412, "du_lieu_da_thay_doi"),
    (5, None, 428, "thieu_if_match"),
    (99, '"any"', 404, "khong_tim_thay"),
])
async def test_preconditions(api, id_, etag, status, code):
    before = dict(api.stored)
    response = await api.client.post(f"{URL}/{id_}/dat_lai_mat_khau",
                                     json={"mat_khau_moi": NEW_PASSWORD},
                                     headers={"If-Match": etag} if etag else {})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert api.stored == before and not api.history
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()


# UC-08 A6: hash/phiên bản/audit chờ cùng transaction và commit sau append audit
async def test_password_and_version_are_staged_until_audit(api):
    before = api.stored[5]

    async def append(entry):
        assert api.stored[5] == before
        assert verify_password(NEW_PASSWORD, api.pending[5].password_hash)
        assert api.pending[5].phien_ban_dang_nhap == 3
        api.session.commit.assert_not_awaited()
        api.pending_history.append(entry)

    api.audit.append.side_effect = append
    assert (await reset(api)).status_code == 200
    api.session.commit.assert_awaited_once()
    assert api.stored[5].phien_ban_dang_nhap == 3 and len(api.history) == 1


# UC-08 A6: audit/commit lỗi rollback hash, phiên bản, audit; mật khẩu và token cũ vẫn hợp lệ
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_failed_save_rolls_back_everything(api, failure):
    before = dict(api.stored)
    headers = api.headers(5)
    target = api.audit.append if failure == "audit" else api.session.commit
    target.side_effect = RuntimeError("save unavailable")
    response = await reset(api)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    api.repo.set_password_hash.assert_awaited_once()
    api.session.rollback.assert_awaited_once()
    assert api.stored == before and not api.history
    assert not api.pending and not api.pending_history
    assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    target.side_effect = api.pending_history.append if failure == "audit" else None
    assert (await login(api, 5, PASSWORD)).status_code == 200
    assert (await login(api, 5, NEW_PASSWORD)).status_code == 401


# -------------------------------------------------------------------------
# Employee self password change: POST /api/v1/nhan_vien/me/doi_mat_khau
# -------------------------------------------------------------------------
async def test_employee_self_change_password_success(api):
    headers = api.headers(5)
    second_token = create_access_token(
        5, api.stored[5].roles,
        credential_version=password_version(api.stored[5].password_hash),
        session_version=api.stored[5].phien_ban_dang_nhap,
    )
    second_headers = {"Authorization": f"Bearer {second_token}"}
    # Both active sessions
    assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    assert (await api.client.get("/api/v1/auth/me", headers=second_headers)).status_code == 200

    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 204
    assert not response.content  # 204 has empty body

    # Both old tokens fail immediately with 401
    assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 401
    assert (await api.client.get("/api/v1/auth/me", headers=second_headers)).status_code == 401
    # Old password fails
    assert (await login(api, 5, PASSWORD)).status_code == 401
    # New password succeeds
    login_res = await login(api, 5, NEW_PASSWORD)
    assert login_res.status_code == 200
    new_token = login_res.json()["data"]["access_token"]
    assert (await api.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})).status_code == 200

    # Audit recorded
    password_audits = [a for a in api.history if a.thao_tac == "doi_mat_khau"]
    assert len(password_audits) == 1
    audit_entry = password_audits[0]
    assert audit_entry.nhan_vien_id == 5 and audit_entry.doi_tuong_id == 5
    assert audit_entry.du_lieu_sau == {"da_doi_mat_khau": True}


async def test_employee_self_change_password_wrong_current(api):
    headers = api.headers(5)
    before = dict(api.stored)
    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": "wrong-password", "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    # Required: HTTP 400 with code mat_khau_hien_tai_khong_dung
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "mat_khau_hien_tai_khong_dung"
    # Session remains intact!
    assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200
    # Password unchanged
    assert (await login(api, 5, PASSWORD)).status_code == 200
    # No password change audit
    password_audits = [a for a in api.history if a.thao_tac == "doi_mat_khau"]
    assert len(password_audits) == 0
    assert api.stored == before


@pytest.mark.parametrize("bad_pwd", ["12345", ""])
async def test_employee_self_change_password_short_or_empty(api, bad_pwd):
    headers = api.headers(5)
    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": bad_pwd},
        headers=headers,
    )
    assert response.status_code == 422
    assert (await api.client.get("/api/v1/auth/me", headers=headers)).status_code == 200


@pytest.mark.parametrize("role_id", [1, 4])  # 1: admin, 4: quan_ly
async def test_employee_self_change_password_wrong_role(api, role_id):
    headers = api.headers(role_id)
    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 403


async def test_employee_self_change_password_extra_fields(api):
    headers = api.headers(5)
    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD, "nhan_vien_id": 2},
        headers=headers,
    )
    assert response.status_code == 422


async def test_employee_self_change_password_role_changed_at_lock(api):
    # Simulated race: token authenticates normally via get_credentials_by_id as nhan_vien,
    # but concurrent transaction changed role before lock_credentials_by_id
    original = api.stored[5]
    headers = api.headers(5)
    changed = original.model_copy(update={"roles": ["quan_ly"], "ma_vai_tro": "quan_ly", "vai_tro_id": 2})
    api.repo.lock_credentials_by_id = AsyncMock(return_value=changed)
    api.repo.set_password_hash.reset_mock()
    api.audit.append.reset_mock()

    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 403
    api.repo.lock_credentials_by_id.assert_awaited_once_with(5)
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()


async def test_employee_self_change_password_stale_pbdn_at_lock(api):
    # Simulated race: token authenticated with pbdn=2, but locked credentials has pbdn=3
    original = api.stored[5]
    headers = api.headers(5)
    changed = original.model_copy(update={"phien_ban_dang_nhap": 3})
    api.repo.lock_credentials_by_id = AsyncMock(return_value=changed)
    api.repo.set_password_hash.reset_mock()
    api.audit.append.reset_mock()

    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 401
    assert "sign in again" in response.text
    api.repo.lock_credentials_by_id.assert_awaited_once_with(5)
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()


async def test_employee_self_change_password_account_locked_at_lock(api):
    # Simulated race: token authenticated, but locked credentials is now bi_khoa
    original = api.stored[5]
    headers = api.headers(5)
    changed = original.model_copy(update={"trang_thai": "bi_khoa"})
    api.repo.lock_credentials_by_id = AsyncMock(return_value=changed)
    api.repo.set_password_hash.reset_mock()
    api.audit.append.reset_mock()

    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    api.repo.lock_credentials_by_id.assert_awaited_once_with(5)
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()


async def test_employee_self_change_password_pwdv_changed_at_lock(api):
    # Simulated race: token authenticated, but another password reset changed pwdv before lock
    original = api.stored[5]
    headers = api.headers(5)
    changed = original.model_copy(update={"password_hash": "$argon2id$v=19$m=65536,t=3,p=4$changed$changed"})
    api.repo.lock_credentials_by_id = AsyncMock(return_value=changed)
    api.repo.set_password_hash.reset_mock()
    api.audit.append.reset_mock()

    response = await api.client.post(
        f"{URL}/me/doi_mat_khau",
        json={"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 401
    api.repo.lock_credentials_by_id.assert_awaited_once_with(5)
    api.repo.set_password_hash.assert_not_awaited()
    api.audit.append.assert_not_awaited()
