"""UC-01 HTTP contract with real auth services and no database."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import register_exception_handlers
from app.core.security import decode_access_token, get_password_hash
from app.dependencies import get_auth_service
from app.modules.audit.service import AuditService
from app.modules.auth.router import router
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.schemas import EmployeeCredentials
from app.modules.nhan_vien.service import NhanVienService


@pytest.fixture(scope="module")
def password():
    plain = "UC01-test-password"
    return SimpleNamespace(plain=plain, hashed=get_password_hash(plain))


@pytest.fixture
async def api(password):
    employee = EmployeeCredentials(
        id=17,
        ma_nhan_vien="NV-000017",
        ten_dang_nhap="uc01-user",
        email="uc01@example.test",
        ho_ten="Nhân viên UC-01",
        vai_tro_id=3,
        ma_vai_tro="nhan_vien",
        roles=["nhan_vien"],
        trang_thai="hoat_dong",
        password_hash=password.hashed,
        ngay_sinh=None,
        so_dien_thoai=None,
        ngay_vao_lam=None,
        he_so_luong=None,
    )
    repo = AsyncMock()
    repo.find_by_username.side_effect = lambda name: (
        employee if name == employee.ten_dang_nhap else None
    )
    repo.find_unique_by_email.side_effect = lambda email: (
        employee if email == employee.email else None
    )
    audit_repo = AsyncMock()
    transaction = AsyncMock()
    service = AuthService(NhanVienService(repo, AuditService(audit_repo), transaction))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_auth_service] = lambda: service
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield SimpleNamespace(
            client=client,
            employee=employee,
            repo=repo,
            audit_repo=audit_repo,
            transaction=transaction,
            credentials={"ten_dang_nhap": employee.ten_dang_nhap, "mat_khau": password.plain},
        )


# UC-01 AC-1: Đăng nhập thành công theo vai trò
@pytest.mark.parametrize("role", ["quan_tri_vien", "quan_ly", "nhan_vien"])
async def test_login_for_each_role(api, role):
    api.employee.ma_vai_tro = role
    api.employee.roles = [role]

    response = await api.client.post("/api/v1/auth/dang_nhap", json=api.credentials)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["nhan_vien"]["ma_vai_tro"] == role
    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == str(api.employee.id)
    assert payload["roles"] == [role]


# UC-01 AC-2: Sai mật khẩu
async def test_wrong_password_does_not_create_session_or_audit(api):
    response = await api.client.post(
        "/api/v1/auth/dang_nhap", json={**api.credentials, "mat_khau": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "thong_tin_dang_nhap_khong_hop_le"
    assert "access_token" not in response.text
    api.audit_repo.append.assert_not_awaited()
    api.transaction.__aenter__.assert_not_awaited()


# UC-01 A2: Sai tên đăng nhập hoặc mật khẩu
async def test_unknown_username_matches_wrong_password_error(api):
    unknown = await api.client.post(
        "/api/v1/auth/dang_nhap", json={**api.credentials, "ten_dang_nhap": "unknown-user"}
    )
    wrong_password = await api.client.post(
        "/api/v1/auth/dang_nhap", json={**api.credentials, "mat_khau": "wrong-password"}
    )

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json()["error"] == wrong_password.json()["error"]
    assert unknown.json()["error"]["code"] == "thong_tin_dang_nhap_khong_hop_le"
    assert "access_token" not in unknown.text
    api.audit_repo.append.assert_not_awaited()


# UC-01 AC-3: Tài khoản bị khóa không đăng nhập được
async def test_locked_account_does_not_create_session_or_audit(api):
    api.employee.trang_thai = "bi_khoa"

    response = await api.client.post("/api/v1/auth/dang_nhap", json=api.credentials)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    assert "access_token" not in response.text
    api.audit_repo.append.assert_not_awaited()
    api.transaction.__aenter__.assert_not_awaited()


# UC-01 AC-4: Ghi lịch sử đăng nhập
async def test_login_appends_one_audit_without_password_or_hash(api, password):
    response = await api.client.post("/api/v1/auth/dang_nhap", json=api.credentials)

    assert response.status_code == 200
    api.audit_repo.append.assert_awaited_once()
    entry = api.audit_repo.append.await_args.args[0]
    assert entry.nhan_vien_id == entry.doi_tuong_id == api.employee.id
    assert entry.loai_doi_tuong == "nhan_vien"
    assert entry.thao_tac == "dang_nhap"
    assert entry.du_lieu_truoc is None
    assert entry.du_lieu_sau is None
    serialized = entry.model_dump_json()
    assert password.plain not in serialized
    assert password.hashed not in serialized
    api.transaction.__aenter__.assert_awaited_once()
    api.transaction.__aexit__.assert_awaited_once_with(None, None, None)


# UC-01 A1: Thiếu tên đăng nhập hoặc mật khẩu
@pytest.mark.parametrize(
    "credentials",
    [
        {},
        {"mat_khau": "password"},
        {"ten_dang_nhap": "user"},
        {"ten_dang_nhap": "", "mat_khau": "password"},
        {"ten_dang_nhap": "user", "mat_khau": ""},
        {"ten_dang_nhap": "   ", "mat_khau": "password"},
    ],
)
async def test_missing_or_empty_credentials_do_not_reach_repository(api, credentials):
    response = await api.client.post("/api/v1/auth/dang_nhap", json=credentials)

    assert response.status_code == 422
    assert "access_token" not in response.text
    assert api.repo.mock_calls == []
    api.audit_repo.append.assert_not_awaited()


# UC-01 A4: Không ghi được lịch sử đăng nhập
async def test_audit_failure_does_not_issue_token(api):
    api.audit_repo.append.side_effect = RuntimeError("audit unavailable")

    response = await api.client.post("/api/v1/auth/dang_nhap", json=api.credentials)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    assert "access_token" not in response.text
    api.audit_repo.append.assert_awaited_once()
    api.transaction.__aexit__.assert_awaited_once()
    assert api.transaction.__aexit__.await_args.args[0] is RuntimeError


# UC-01 AC-1: Đăng nhập thành công theo vai trò; R1/D1 chỉ dùng tên đăng nhập
@pytest.mark.parametrize("identifier,status", [("uc01@example.test", 401), ("uc01-user", 200)])
async def test_swagger_token_requires_username(api, identifier, status):
    response = await api.client.post(
        "/api/v1/auth/token",
        data={"username": identifier, "password": api.credentials["mat_khau"]},
    )

    assert response.status_code == status
    api.repo.find_unique_by_email.assert_not_awaited()
    if status == 200:
        assert decode_access_token(response.json()["access_token"])["sub"] == str(api.employee.id)
        api.audit_repo.append.assert_awaited_once()
    else:
        assert response.json()["error"]["code"] == "thong_tin_dang_nhap_khong_hop_le"
        assert "access_token" not in response.text
        api.audit_repo.append.assert_not_awaited()
