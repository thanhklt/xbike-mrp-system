"""UC-04 service/ASGI contracts with real hashing and an isolated in-memory store."""

from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.errors import DuplicateCodeException, DuplicateUsernameException
from app.core.exceptions import register_exception_handlers
from app.core.security import (
    decode_access_token,
    get_password_hash,
    password_version,
    verify_password,
)
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_auth_service, get_current_user_payload, get_nhan_vien_service
from app.modules.audit.service import AuditService
from app.modules.auth.router import router as auth_router
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import (
    EmployeeCredentials,
    EmployeeRecord,
    NewEmployee,
    VaiTroRead,
)
from app.modules.nhan_vien.service import NhanVienService
from app.shared.records import RecordPage

URL = "/api/v1/nhan_vien"
BODY = {"ten_dang_nhap": "uc04-new", "mat_khau": "123456", "vai_tro_id": 1}
ROLES = {1: "quan_tri_vien", 2: "quan_ly", 3: "nhan_vien"}


@pytest.fixture(scope="module")
def admin_hash():
    return get_password_hash("UC04-admin-password")


@pytest.fixture
async def api(admin_hash):
    actor = {"sub": "1", "roles": ["quan_tri_vien"], "pwdv": password_version(admin_hash)}
    current = SimpleNamespace(
        trang_thai="hoat_dong", roles=["quan_tri_vien"], password_hash=admin_hash
    )
    repo = AsyncMock(spec=NhanVienRepository)
    audit_repo, session = AsyncMock(), AsyncMock()
    stored, pending, history, pending_history = {}, {}, [], []

    async def create(employee):
        record = EmployeeRecord(
            id=9,
            ma_nhan_vien=employee.ma_nhan_vien,
            ten_dang_nhap=employee.ten_dang_nhap,
            vai_tro_id=employee.vai_tro_id,
            ma_vai_tro=ROLES[employee.vai_tro_id],
            trang_thai="hoat_dong",
            **employee.profile,
        )
        pending[record.ten_dang_nhap] = EmployeeCredentials(
            **asdict(record), roles=[record.ma_vai_tro], password_hash=employee.password_hash
        )
        return record

    async def commit():
        stored.update(pending)
        history.extend(pending_history)
        pending.clear()
        pending_history.clear()

    async def rollback():
        pending.clear()
        pending_history.clear()

    repo.lock_credentials_by_id.return_value = current
    repo.get_role.side_effect = lambda id_: (
        VaiTroRead(id=id_, ma_vai_tro=ROLES[id_], ten_vai_tro=ROLES[id_], mo_ta=None)
        if id_ in ROLES
        else None
    )
    repo.find_by_username.side_effect = stored.get
    repo.next_employee_code.return_value = "NV-000009"
    repo.create.side_effect = create
    repo.list_employees.side_effect = lambda _params: RecordPage(list(stored.values()), len(stored))
    audit_repo.append.side_effect = pending_history.append
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    service = NhanVienService(repo, AuditService(audit_repo), SqlAlchemyTransaction(session))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user_payload] = lambda: actor
    app.dependency_overrides[get_nhan_vien_service] = lambda: service
    app.dependency_overrides[get_auth_service] = lambda: AuthService(service)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield SimpleNamespace(
            client=client,
            repo=repo,
            audit=audit_repo,
            session=session,
            service=service,
            actor=actor,
            current=current,
            stored=stored,
            pending=pending,
            history=history,
            pending_history=pending_history,
        )


# UC-04 AC-1: tạo QTV hoạt động, hash đúng và đăng nhập với quyền quản trị
async def test_create_administrator_can_login(api):
    await assert_created_account_can_login(api, 1)


# UC-04 AC-2: tạo QLK/NV hoạt động và đăng nhập theo đúng vai trò đã chọn
@pytest.mark.parametrize("role_id", [2, 3])
async def test_create_business_account_can_login(api, role_id):
    await assert_created_account_can_login(api, role_id)


async def assert_created_account_can_login(api, role_id):
    response = await api.client.post(URL, json={**BODY, "vai_tro_id": role_id})
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["ma_vai_tro"] == ROLES[role_id]
    assert data["vai_tro_id"] == role_id
    assert data["trang_thai"] == "hoat_dong"
    assert data["ma_nhan_vien"] == "NV-000009"
    assert response.headers["Location"] == f"{URL}/9"
    assert response.headers["ETag"].startswith('"')
    assert not {"mat_khau", "password_hash", "ly_do"}.intersection(data)
    for field in ("ho_ten", "email", "ngay_sinh", "so_dien_thoai", "ngay_vao_lam", "he_so_luong"):
        assert data[field] is None
    created = api.repo.create.await_args.args[0]
    assert verify_password(BODY["mat_khau"], created.password_hash)
    assert not {"mat_khau", "ly_do", "ma_nhan_vien"}.intersection(created.profile)
    listing = await api.client.get(URL)
    assert listing.status_code == 200
    assert listing.json()["data"] == [data]
    login = await api.client.post(
        "/api/v1/auth/dang_nhap",
        json={key: BODY[key] for key in ("ten_dang_nhap", "mat_khau")},
    )
    assert login.status_code == 200
    principal = login.json()["data"]
    assert principal["nhan_vien"]["ma_vai_tro"] == ROLES[role_id]
    token = decode_access_token(principal["access_token"])
    assert token["roles"] == [ROLES[role_id]]
    assert token["sub"] == str(data["id"])


# UC-04 AC-3: trùng tên có sẵn bị từ chối trước cấp mã, tạo và ghi lịch sử
async def test_existing_username_does_not_allocate_or_create(api):
    api.repo.find_by_username.side_effect = None
    api.repo.find_by_username.return_value = object()
    response = await api.client.post(URL, json=BODY)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ten_dang_nhap_bi_trung"
    assert response.json()["error"]["message"] == "Tên đăng nhập đã tồn tại"
    api.repo.next_employee_code.assert_not_awaited()
    api.repo.create.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    assert not api.stored and not api.history


# UC-04 AC-3: tên bị tạo đồng thời trả cùng lỗi 409, không ghi lịch sử
async def test_concurrent_username_conflict_rolls_back(api):
    api.repo.create.side_effect = DuplicateUsernameException()
    response = await api.client.post(URL, json=BODY)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ten_dang_nhap_bi_trung"
    assert response.json()["error"]["message"] == "Tên đăng nhập đã tồn tại"
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    api.session.commit.assert_not_awaited()
    assert not api.stored and not api.history


# UC-04 AC-4: biên mật khẩu 5 ký tự bị chặn, 6 ký tự được tạo
@pytest.mark.parametrize("password,status", [("12345", 422), ("123456", 201)])
async def test_initial_password_boundary(api, password, status):
    response = await api.client.post(URL, json={**BODY, "mat_khau": password})
    assert response.status_code == status
    if status == 422:
        assert api.repo.mock_calls == []
        assert any(d["field"] == "mat_khau" for d in response.json()["error"]["details"])
        api.audit.append.assert_not_awaited()
    else:
        api.repo.create.assert_awaited_once()


# UC-04 AC-5: đúng một lịch sử tạo, lý do trim/null; không lộ mật khẩu/hash
@pytest.mark.parametrize(
    "reason,expected", [("  Bổ sung QTV  ", "Bổ sung QTV"), ("", None), ("   ", None), (None, None)]
)
async def test_creation_audit_contains_actor_reason_and_safe_profile(api, reason, expected):
    body = dict(BODY)
    if reason is not None:
        body["ly_do"] = reason
    response = await api.client.post(URL, json=body)
    assert response.status_code == 201
    api.audit.append.assert_awaited_once()
    entry = api.audit.append.await_args.args[0]
    assert entry.nhan_vien_id == 1
    assert entry.loai_doi_tuong == "nhan_vien"
    assert entry.doi_tuong_id == response.json()["data"]["id"]
    assert entry.thao_tac == "tao"
    assert entry.ly_do == expected
    assert entry.du_lieu_truoc is None
    assert entry.du_lieu_sau == response.json()["data"]
    serialized = entry.model_dump_json()
    assert BODY["mat_khau"] not in serialized
    assert api.repo.create.await_args.args[0].password_hash not in serialized
    assert "mat_khau" not in serialized and "password_hash" not in serialized
    assert api.history == [entry]
    assert "ly_do" not in api.repo.create.await_args.args[0].profile


# UC-04 AC-5: lý do tối đa 1000 ký tự; dài hơn bị từ chối trước repository
@pytest.mark.parametrize("length,status", [(1000, 201), (1001, 422)])
async def test_reason_length_limit(api, length, status):
    response = await api.client.post(URL, json={**BODY, "ly_do": "x" * length})
    assert response.status_code == status
    if status == 422:
        assert api.repo.mock_calls == []
    else:
        assert api.history[0].ly_do == "x" * length


# UC-04 A1: trường bắt buộc thiếu/rỗng bị chỉ rõ và không truy cập repository
@pytest.mark.parametrize(
    "field,value",
    [
        ("ten_dang_nhap", None),
        ("mat_khau", None),
        ("vai_tro_id", None),
        ("ten_dang_nhap", ""),
        ("ten_dang_nhap", "   "),
    ],
)
async def test_missing_or_blank_required_field(api, field, value):
    body = dict(BODY)
    if value is None:
        body.pop(field)
    else:
        body[field] = value
    response = await api.client.post(URL, json=body)
    assert response.status_code == 422
    assert any(d["field"] == field for d in response.json()["error"]["details"])
    assert api.repo.mock_calls == []
    api.audit.append.assert_not_awaited()
    assert not api.stored and not api.history


# UC-04 A6: QLK/NV gọi trực tiếp API tạo bị chặn trước mọi truy cập repository
@pytest.mark.parametrize("role", ["quan_ly", "nhan_vien"])
async def test_nonadministrator_cannot_create(api, role):
    api.actor["roles"] = [role]
    response = await api.client.post(URL, json=BODY)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    assert api.repo.mock_calls == []
    api.audit.append.assert_not_awaited()


# UC-04 A6: claim QTV nhưng DB đã hạ vai trò bị chặn sau lấy khóa
async def test_demoted_administrator_cannot_create(api):
    api.current.roles = ["nhan_vien"]
    response = await api.client.post(URL, json=BODY)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    api.repo.lock_credentials_by_id.assert_awaited_once_with(1)
    api.repo.get_role.assert_not_awaited()
    api.repo.next_employee_code.assert_not_awaited()
    api.repo.create.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()


# UC-04 A7: audit hoặc commit thất bại rollback tài khoản và lịch sử, trả 500
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_failed_save_rolls_back_account_and_audit(api, failure):
    target = api.audit.append if failure == "audit" else api.session.commit
    target.side_effect = RuntimeError("save unavailable")
    response = await api.client.post(URL, json=BODY)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    api.repo.create.assert_awaited_once()
    api.audit.append.assert_awaited_once()
    api.session.rollback.assert_awaited_once()
    assert not api.stored and not api.history
    assert not api.pending and not api.pending_history


# UC-04 A1: vai trò không tồn tại trả 404, không cấp mã hay lưu tài khoản
async def test_unknown_role_does_not_allocate(api):
    response = await api.client.post(URL, json={**BODY, "vai_tro_id": 99})
    assert response.status_code == 404
    api.repo.next_employee_code.assert_not_awaited()
    api.repo.create.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()


# UC-04 AC-3: repository phân biệt unique username/mã theo metadata hoặc thông báo DB
@pytest.mark.parametrize(
    "column,error_type",
    [
        ("ten_dang_nhap", DuplicateUsernameException),
        ("ma_nhan_vien", DuplicateCodeException),
    ],
)
@pytest.mark.parametrize("driver", ["sqlite", "asyncpg", "psycopg"])
async def test_repository_unique_violation_mapping(column, error_type, driver):
    original = RuntimeError(f"UNIQUE constraint failed: NhanVien.{column}")
    if driver == "sqlite":
        original.sqlite_errorname = "SQLITE_CONSTRAINT_UNIQUE"
    else:
        original.sqlstate = "23505"
        metadata = SimpleNamespace(constraint_name=f"NhanVien_{column}_key")
        if driver == "asyncpg":
            cause = RuntimeError("unique violation")
            cause.constraint_name = metadata.constraint_name
            original = RuntimeError("adapter error")
            original.sqlstate = "23505"
            original.__cause__ = cause
        else:
            original.diag = metadata
    session = AsyncMock()
    session.add = lambda _row: None
    session.flush.side_effect = IntegrityError("INSERT", {}, original)
    repository = SqlAlchemyNhanVienRepository(session)
    with pytest.raises(error_type) as error:
        await repository.create(NewEmployee("new", "NV-000009", 1, "hash", {}))
    expected_message = (
        "Tên đăng nhập đã tồn tại"
        if column == "ten_dang_nhap"
        else "Mã nhân viên vừa được cấp cho tài khoản khác, vui lòng thử lại"
    )
    assert error.value.message == expected_message
    assert error.value.__cause__ is session.flush.side_effect
    session.refresh.assert_not_awaited()


# UC-04 A7: lỗi ràng buộc khác không bị báo nhầm thành trùng tên hoặc mã
async def test_repository_preserves_other_integrity_errors():
    session = AsyncMock()
    session.add = lambda _row: None
    original = RuntimeError("foreign key violation")
    original.sqlstate = "23503"
    error = IntegrityError("INSERT", {}, original)
    session.flush.side_effect = error
    with pytest.raises(IntegrityError) as caught:
        await SqlAlchemyNhanVienRepository(session).create(
            NewEmployee("new", "NV-000009", 1, "hash", {})
        )
    assert caught.value is error
