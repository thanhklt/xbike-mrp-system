"""Kiểm tra đổi tên đăng nhập in-process, không kết nối database."""

from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.errors import DuplicateUsernameException
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, password_version
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_nhan_vien_service
from app.modules.auth.router import router as auth_router
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import EmployeeCredentials, EmployeeRecord
from app.modules.nhan_vien.service import NhanVienService

URL = "/api/v1/nhan_vien/3"


@pytest.fixture
async def api():
    records = {
        employee_id: EmployeeRecord(
            id=employee_id,
            ma_nhan_vien=f"NV-{employee_id:06d}",
            ho_ten=None,
            vai_tro_id=employee_id,
            ma_vai_tro=role,
            trang_thai="hoat_dong",
            ten_dang_nhap=f"employee-{employee_id}",
            ngay_sinh=None,
            so_dien_thoai=None,
            email=None,
            ngay_vao_lam=None,
            he_so_luong=None,
        )
        for employee_id, role in [(1, "quan_tri_vien"), (2, "quan_ly"), (3, "nhan_vien")]
    }
    repo = AsyncMock(spec=NhanVienRepository)
    audit, session = AsyncMock(), AsyncMock()

    def credentials(employee_id):
        record = records[employee_id]
        return EmployeeCredentials(
            **asdict(record), roles=[record.ma_vai_tro], password_hash="test-hash"
        )

    async def update(employee_id, changes):
        records[employee_id] = replace(records[employee_id], **changes)
        return records[employee_id]

    repo.get_by_id.side_effect = records.get
    repo.get_for_update.side_effect = records.get
    repo.get_credentials_by_id.side_effect = credentials
    repo.lock_credentials_by_id.side_effect = credentials
    repo.find_by_username.side_effect = lambda username: next(
        (credentials(record.id) for record in records.values() if record.ten_dang_nhap == username),
        None,
    )
    repo.update_profile.side_effect = update
    service = NhanVienService(repo, audit, SqlAlchemyTransaction(session))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[get_nhan_vien_service] = lambda: service

    def headers(employee_id=1):
        token = create_access_token(
            employee_id,
            [records[employee_id].ma_vai_tro],
            credential_version=password_version("test-hash"),
            session_version=0,
        )
        return {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(
            client=client, repo=repo, audit=audit, session=session, records=records, headers=headers
        )


async def patch(api, username, employee_id=1):
    headers = api.headers(employee_id)
    detail = await api.client.get(URL, headers=headers)
    return await api.client.patch(
        URL, headers={**headers, "If-Match": detail.headers["etag"]},
        json={"ten_dang_nhap": username},
    )


async def test_rename_returns_trimmed_username_new_etag_and_audit(api):
    before = await api.client.get(URL, headers=api.headers())
    response = await patch(api, "  renamed.employee  ")
    assert response.status_code == 200
    assert response.json()["data"]["ten_dang_nhap"] == "renamed.employee"
    assert response.headers["etag"] != before.headers["etag"]
    detail = await api.client.get(URL, headers=api.headers())
    assert response.headers["etag"] == detail.headers["etag"]
    entry = api.audit.append.call_args.args[0]
    assert entry.thao_tac == "sua"
    assert entry.du_lieu_truoc["ten_dang_nhap"] == "employee-3"
    assert entry.du_lieu_sau["ten_dang_nhap"] == "renamed.employee"
    api.audit.append.assert_awaited_once()
    api.session.commit.assert_awaited_once()


async def test_duplicate_username_returns_409_without_update_or_audit(api):
    response = await patch(api, "employee-2")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ten_dang_nhap_bi_trung"
    assert response.json()["error"]["message"] == "Tên đăng nhập đã tồn tại"
    api.repo.update_profile.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()
    assert api.records[3].ten_dang_nhap == "employee-3"


async def test_same_username_is_noop(api):
    before = await api.client.get(URL, headers=api.headers())
    response = await patch(api, "  employee-3  ")
    assert response.status_code == 200
    assert response.headers["etag"] == before.headers["etag"]
    api.repo.update_profile.assert_not_awaited()
    api.audit.append.assert_not_awaited()


@pytest.mark.parametrize("username", ["", "   ", None, "x" * 256])
async def test_invalid_username_returns_422(api, username):
    response = await patch(api, username)
    assert response.status_code == 422
    api.repo.update_profile.assert_not_awaited()
    api.audit.append.assert_not_awaited()


@pytest.mark.parametrize("employee_id", [2, 3])
async def test_non_admin_cannot_rename(api, employee_id):
    response = await patch(api, "renamed.employee", employee_id)
    assert response.status_code == 403
    api.repo.update_profile.assert_not_awaited()
    api.audit.append.assert_not_awaited()


async def test_token_issued_before_rename_still_reads_auth_me(api):
    old_headers = api.headers(3)
    before = await api.client.get("/api/v1/auth/me", headers=old_headers)
    assert before.status_code == 200
    assert (await patch(api, "renamed.employee")).status_code == 200
    after = await api.client.get("/api/v1/auth/me", headers=old_headers)
    assert after.status_code == 200
    assert after.json()["data"]["ten_dang_nhap"] == "renamed.employee"


async def test_concurrent_duplicate_rolls_back_without_audit(api):
    api.repo.update_profile.side_effect = DuplicateUsernameException()
    response = await patch(api, "renamed.employee")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ten_dang_nhap_bi_trung"
    api.audit.append.assert_not_awaited()
    api.session.rollback.assert_awaited_once()


@pytest.mark.parametrize("source", ["constraint", "cause", "diag", "sqlite", "other_unique", "check"])
async def test_repository_maps_only_username_unique_violation(source):
    original = RuntimeError("constraint violation")
    original.sqlstate = "23514" if source == "check" else "23505"
    constraint = "NhanVien_ten_dang_nhap_key"
    if source == "constraint":
        original.constraint_name = constraint
    elif source == "cause":
        original.__cause__ = RuntimeError("unique")
        original.__cause__.constraint_name = constraint
    elif source == "diag":
        original.diag = SimpleNamespace(constraint_name=constraint)
    elif source == "sqlite":
        original = RuntimeError("UNIQUE constraint failed: NhanVien.ten_dang_nhap")
        original.sqlite_errorname = "SQLITE_CONSTRAINT_UNIQUE"
    else:
        original.constraint_name = "NhanVien_ma_nhan_vien_key"
    error = IntegrityError("UPDATE", {}, original)
    session = AsyncMock()
    session.execute.side_effect = error
    mapped = source not in ("other_unique", "check")
    with pytest.raises(DuplicateUsernameException if mapped else IntegrityError) as caught:
        await SqlAlchemyNhanVienRepository(session).update_profile(3, {"ten_dang_nhap": "new"})
    assert caught.value.__cause__ is error if mapped else caught.value is error
    session.scalar.assert_not_awaited()
