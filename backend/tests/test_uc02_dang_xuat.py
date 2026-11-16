"""UC-02 protected API contract with real auth services and no database."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, get_password_hash, password_version
from app.dependencies import get_auth_service
from app.modules.audit.service import AuditService
from app.modules.auth.router import router
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.schemas import EmployeeCredentials, NhanVienRead
from app.modules.nhan_vien.service import NhanVienService


@pytest.fixture(scope="module")
def password_hashes():
    return SimpleNamespace(
        original=get_password_hash("UC02-original-password"),
        changed=get_password_hash("UC02-changed-password"),
    )


@pytest.fixture
async def api(password_hashes):
    employee = EmployeeCredentials(
        id=17,
        ma_nhan_vien="NV-000017",
        ten_dang_nhap="uc02-user",
        email="uc02@example.test",
        ho_ten="Nhân viên UC-02",
        vai_tro_id=3,
        ma_vai_tro="nhan_vien",
        roles=["nhan_vien"],
        trang_thai="hoat_dong",
        password_hash=password_hashes.original,
        ngay_sinh=None,
        so_dien_thoai=None,
        ngay_vao_lam=None,
        he_so_luong=None,
    )
    repo = AsyncMock()
    repo.get_credentials_by_id.side_effect = lambda employee_id: (
        employee if employee_id == employee.id else None
    )
    audit_repo = AsyncMock()
    transaction = AsyncMock()
    service = AuthService(NhanVienService(repo, AuditService(audit_repo), transaction))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_auth_service] = lambda: service
    token = create_access_token(
        employee.id,
        roles=employee.roles,
        credential_version=password_version(employee.password_hash),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield SimpleNamespace(
            client=client,
            employee=employee,
            repo=repo,
            audit_repo=audit_repo,
            transaction=transaction,
            token=token,
        )
    audit_repo.append.assert_not_called()
    transaction.__aenter__.assert_not_awaited()


# UC-02 AC-2: Phải đăng nhập lại sau khi đăng xuất
async def test_missing_token_requires_login(api):
    response = await api.client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "chua_xac_thuc"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    api.repo.get_credentials_by_id.assert_not_awaited()


# UC-02 A1: Mở lại trang cần đăng nhập sau khi đăng xuất
@pytest.mark.parametrize("token_kind", ["garbage", "wrong_key", "expired"])
async def test_invalid_or_expired_token_requires_login(api, token_kind):
    if token_kind == "garbage":
        token = "not-a-jwt"
    elif token_kind == "wrong_key":
        token = jwt.encode(
            jwt.get_unverified_claims(api.token),
            settings.secret_key + "-wrong-key",
            algorithm=settings.algorithm,
        )
    else:
        token = create_access_token(
            api.employee.id,
            roles=api.employee.roles,
            expires_delta=timedelta(minutes=-1),
            credential_version=password_version(api.employee.password_hash),
        )

    response = await api.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "chua_xac_thuc"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    api.repo.get_credentials_by_id.assert_not_awaited()


# UC-02 AC-1: Đăng xuất kết thúc phiên — đối chứng phiên hợp lệ
async def test_valid_session_returns_current_profile(api):
    response = await api.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {api.token}"}
    )

    assert response.status_code == 200
    assert response.json()["data"] == NhanVienRead.model_validate(api.employee).model_dump(
        mode="json"
    )


# UC-02 A2: Phiên đã kết thúc từ trước — tài khoản đã bị khóa
async def test_locked_account_rejects_existing_token(api):
    api.employee.trang_thai = "bi_khoa"

    response = await api.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {api.token}"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    api.repo.get_credentials_by_id.assert_awaited_once_with(api.employee.id)


# UC-02 A2: Phiên đã kết thúc từ trước — mật khẩu đã đổi
async def test_changed_password_rejects_old_token(api, password_hashes):
    api.employee.password_hash = password_hashes.changed

    response = await api.client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {api.token}"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "chua_xac_thuc"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    api.repo.get_credentials_by_id.assert_awaited_once_with(api.employee.id)
