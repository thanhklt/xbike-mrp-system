"""UC-05 service/ASGI contracts with isolated records and staged transactions."""

from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, call

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.core.errors import LastActiveAdminException
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, get_password_hash, password_version
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_auth_service, get_nhan_vien_service
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
PASSWORD = "UC05-test-password"


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash(PASSWORD)


@pytest.fixture
async def api(password_hash):
    def record(id_, role, status="hoat_dong"):
        return EmployeeCredentials(
            id=id_,
            ma_nhan_vien=f"NV-{id_:06d}",
            ten_dang_nhap=f"uc05-{id_}",
            ho_ten=f"Người dùng {id_}",
            vai_tro_id={
                "quan_tri_vien": 1,
                "quan_ly": 2,
                "nhan_vien": 3,
            }[role],
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
        3: record(3, "nhan_vien"),
        4: record(4, "quan_tri_vien", "bi_khoa"),
        5: record(5, "quan_ly"),
    }
    pending, history, pending_history = {}, [], []
    repo = AsyncMock(spec=NhanVienRepository)
    audit, session = AsyncMock(), AsyncMock()

    def read(id_):
        return pending.get(id_, stored.get(id_))

    async def set_status(id_, status):
        pending[id_] = read(id_).model_copy(update={"trang_thai": status})
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
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_nhan_vien_service] = lambda: service
    app.dependency_overrides[get_auth_service] = lambda: AuthService(service)

    def headers(id_):
        user = stored[id_]
        token = create_access_token(
            id_, user.roles, credential_version=password_version(user.password_hash)
        )
        return {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
        headers=headers(1),
    ) as client:

        async def etag(id_):
            response = await client.get(f"{URL}/{id_}")
            assert response.status_code == 200
            return response.headers["etag"]

        yield SimpleNamespace(
            client=client,
            repo=repo,
            audit=audit,
            session=session,
            service=service,
            stored=stored,
            pending=pending,
            history=history,
            pending_history=pending_history,
            etag=etag,
            headers=headers,
        )


async def lock(api, id_=3, *, body=None, etag=None, headers=None):
    version = etag if etag is not None else await api.etag(id_)
    return await api.client.request(
        "DELETE",
        f"{URL}/{id_}",
        json=body,
        headers={"If-Match": version, **(headers or {})},
    )


# UC-05 AC-1: thiếu body, thiếu lý do, null hoặc chỉ khoảng trắng vẫn khóa và lưu lý do null
@pytest.mark.parametrize("body", [None, {}, {"ly_do": None}, {"ly_do": ""}, {"ly_do": "   "}])
async def test_optional_reason_locks_account(api, body):
    old_etag = await api.etag(3)
    response = await lock(api, body=body, etag=old_etag)
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["etag"] != old_etag
    assert response.headers["etag"] == await api.etag(3)
    assert api.stored[3].trang_thai == "bi_khoa"
    assert len(api.history) == 1
    assert api.history[0].ly_do is None
    api.session.commit.assert_awaited_once()


# UC-05 AC-2: token cấp trước khi khóa bị từ chối ở request tiếp theo, không đăng nhập lại được
async def test_locked_employee_loses_existing_session_immediately(api):
    token_headers = api.headers(3)
    assert (await api.client.get("/api/v1/auth/me", headers=token_headers)).status_code == 200
    assert (await lock(api)).status_code == 204
    response = await api.client.get("/api/v1/auth/me", headers=token_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    login = await api.client.post(
        "/api/v1/auth/dang_nhap", json={"ten_dang_nhap": "uc05-3", "mat_khau": PASSWORD}
    )
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    assert len(api.history) == 1


# UC-05 AC-3: QTV cuối bị chặn kể cả tự khóa; QTV đã khóa không được tính
async def test_last_active_admin_cannot_lock_self(api):
    api.stored[2] = api.stored[2].model_copy(update={"trang_thai": "bi_khoa"})
    response = await lock(api, 1)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quan_tri_vien_cuoi_cung"
    assert response.json()["error"]["message"] == (
        "Không khóa được Quản trị viên đang hoạt động cuối cùng"
    )
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    assert api.stored[1].trang_thai == "hoat_dong" and not api.history


# UC-05 AC-3: còn QTV khác thì khóa được QTV đích, thứ tự khóa vai trò → actor → đích → đếm
async def test_can_lock_another_admin_after_role_lock(api):
    response = await lock(api, 2)
    assert response.status_code == 204
    calls = api.repo.mock_calls
    role_lock = calls.index(call.lock_admin_role())
    actor_lock = calls.index(call.lock_credentials_by_id(1))
    target_lock = calls.index(call.get_for_update(2))
    count = calls.index(call.count_active_admins())
    assert role_lock < actor_lock < target_lock < count < calls.index(call.set_status(2, "bi_khoa"))
    assert api.stored[1].trang_thai == "hoat_dong"
    assert api.stored[2].trang_thai == "bi_khoa"


# UC-05 A2: sau thao tác khóa QTV thứ nhất, thao tác kế tiếp không khóa được QTV còn lại
async def test_second_lock_cannot_remove_last_active_admin(api):
    assert (await lock(api, 2)).status_code == 204
    api.repo.set_status.reset_mock()
    api.audit.append.reset_mock()
    response = await lock(api, 1)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "quan_tri_vien_cuoi_cung"
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    assert len(api.history) == 1 and api.stored[1].trang_thai == "hoat_dong"


# UC-05 A3: tự khóa khi còn QTV khác thành công, token hiện tại mất quyền và không đăng nhập lại
async def test_self_lock_ends_own_session(api):
    assert (await lock(api, 1)).status_code == 204
    response = await api.client.get("/api/v1/auth/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    login = await api.client.post(
        "/api/v1/auth/dang_nhap", json={"ten_dang_nhap": "uc05-1", "mat_khau": PASSWORD}
    )
    assert login.status_code == 403
    assert api.stored[2].trang_thai == "hoat_dong"
    assert api.history[0].nhan_vien_id == api.history[0].doi_tuong_id == 1


# UC-05 AC-4: chỉ set_status và append audit; hồ sơ/vai trò và mọi dữ liệu khác giữ nguyên
async def test_lock_only_changes_status_and_appends_one_audit(api):
    before = dict(api.stored)
    etag = await api.etag(3)
    api.repo.reset_mock()
    assert (await lock(api, etag=etag)).status_code == 204
    assert api.repo.mock_calls == [
        call.get_credentials_by_id(1),
        call.lock_admin_role(),
        call.lock_credentials_by_id(1),
        call.get_for_update(3),
        call.set_status(3, "bi_khoa"),
    ]
    assert api.stored == {**before, 3: before[3].model_copy(update={"trang_thai": "bi_khoa"})}
    api.audit.append.assert_awaited_once()
    assert api.audit.mock_calls == [call.append(api.history[0])]


# UC-05 AC-5: audit khoa thuộc ThaoTac v4, đúng actor/đích, trạng thái và lý do đã trim
async def test_lock_audit_records_states_and_reason(api):
    assert (await lock(api, body={"ly_do": "  Tạm ngừng truy cập  "})).status_code == 204
    entry = api.history[0]
    assert len(api.history) == 1
    assert entry.nhan_vien_id == 1 and entry.doi_tuong_id == 3
    assert entry.loai_doi_tuong == "nhan_vien"
    assert entry.thao_tac == "khoa" and entry.thao_tac in get_args(ThaoTac)
    assert entry.trang_thai_truoc == "hoat_dong" and entry.trang_thai_sau == "bi_khoa"
    assert entry.ly_do == "Tạm ngừng truy cập"
    assert entry.du_lieu_truoc["trang_thai"] == "hoat_dong"
    assert entry.du_lieu_sau == {**entry.du_lieu_truoc, "trang_thai": "bi_khoa"}
    assert "password_hash" not in entry.model_dump_json()
    assert api.stored[3].password_hash not in entry.model_dump_json()


# UC-05 A4: đã khóa với ETag hiện tại trả 409, ETag cũ trả 412, thiếu If-Match trả 428
@pytest.mark.parametrize(
    "version,status,code",
    [
        ("current", 409, "trang_thai_khong_hop_le"),
        ("stale", 412, "du_lieu_da_thay_doi"),
        ("missing", 428, "thieu_if_match"),
    ],
)
async def test_changed_state_and_preconditions_do_not_write(api, version, status, code):
    etag = await api.etag(3)
    api.stored[3] = api.stored[3].model_copy(update={"trang_thai": "bi_khoa"})
    headers = (
        {}
        if version == "missing"
        else {"If-Match": await api.etag(3) if version == "current" else etag}
    )
    response = await api.client.request("DELETE", f"{URL}/3", headers=headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    assert not api.history


# UC-05 A8: QLK/NV gọi trực tiếp không được khóa tài khoản hay lấy khóa ghi
@pytest.mark.parametrize("actor_id", [3, 5])
async def test_nonadmin_cannot_lock(api, actor_id):
    response = await lock(api, headers=api.headers(actor_id))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    api.repo.lock_admin_role.assert_not_awaited()
    api.repo.lock_credentials_by_id.assert_not_awaited()
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-05 A9: audit hoặc commit lỗi rollback trạng thái và lịch sử, trả thất bại
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_failed_save_rolls_back_status_and_history(api, failure):
    before = dict(api.stored)
    target = api.audit.append if failure == "audit" else api.session.commit
    target.side_effect = RuntimeError("save unavailable")
    response = await lock(api)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    api.repo.set_status.assert_awaited_once_with(3, "bi_khoa")
    api.session.rollback.assert_awaited_once()
    assert api.stored == before and not api.history
    assert not api.pending and not api.pending_history


# UC-05 AC-1: lý do tối đa 1000 ký tự, vượt giới hạn trả 422 và không ghi
@pytest.mark.parametrize("length,status", [(1000, 204), (1001, 422)])
async def test_optional_reason_length_limit(api, length, status):
    response = await lock(api, body={"ly_do": "x" * length})
    assert response.status_code == status
    if status == 422:
        assert any(d["field"] == "ly_do" for d in response.json()["error"]["details"])
        api.repo.set_status.assert_not_awaited()
        api.audit.append.assert_not_awaited()
    else:
        assert api.history[0].ly_do == "x" * length


# UC-05 A7: không có endpoint xóa hẳn, DELETE hiện có giữ dòng nhân viên
async def test_no_hard_delete_endpoint(api):
    response = await api.client.request("DELETE", f"{URL}/3/xoa")
    assert response.status_code == 404
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    assert 3 in api.stored


# UC-05 AC-3: service ném đúng lỗi nghiệp vụ khi số QTV hoạt động không còn đủ
async def test_service_rejects_last_admin(api):
    etag = await api.etag(1)
    api.stored[2] = api.stored[2].model_copy(update={"trang_thai": "bi_khoa"})
    actor = {
        "sub": "1",
        "roles": ["quan_tri_vien"],
        "pwdv": password_version(api.stored[1].password_hash),
    }
    with pytest.raises(LastActiveAdminException):
        await api.service.soft_delete_employee(1, actor, etag, None, "req-uc05")
    api.repo.set_status.assert_not_awaited()
    api.audit.append.assert_not_awaited()


# UC-05 AC-3: SQL khóa đúng dòng VaiTro QTV và đếm chỉ NhanVien QTV đang hoạt động
async def test_repository_role_lock_and_active_admin_count():
    session = AsyncMock()
    session.scalar.side_effect = [object(), 2]
    repository = SqlAlchemyNhanVienRepository(session)
    await repository.lock_admin_role()
    assert await repository.count_active_admins() == 2
    statements = [args.args[0] for args in session.scalar.await_args_list]
    sql = [
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement in statements
    ]
    assert 'FROM "VaiTro"' in sql[0]
    assert "\"VaiTro\".ma_vai_tro = 'quan_tri_vien'" in sql[0]
    assert sql[0].endswith("FOR UPDATE")
    assert 'JOIN "VaiTro" ON "NhanVien".vai_tro_id = "VaiTro".id' in sql[1]
    assert "\"VaiTro\".ma_vai_tro = 'quan_tri_vien'" in sql[1]
    assert "\"NhanVien\".trang_thai = 'hoat_dong'" in sql[1]
