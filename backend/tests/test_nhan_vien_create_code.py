"""Employee code allocation and HTTP contract, without any database connection."""

from contextlib import AbstractAsyncContextManager
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.core.errors import DuplicateCodeException
from app.core.exceptions import register_exception_handlers
from app.core.security import password_version
from app.dependencies import get_current_user_payload, get_nhan_vien_service
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import EmployeeRecord, NhanVienCreate, VaiTroRead
from app.modules.nhan_vien.service import NhanVienService

BODY = {"ten_dang_nhap": "new.employee", "mat_khau": "test-password", "vai_tro_id": 3}
ACTOR = {"sub": "1", "roles": ["quan_tri_vien"], "pwdv": password_version("admin-hash")}
RECORD = EmployeeRecord(
    id=9,
    ma_nhan_vien="NV-000009",
    ho_ten=None,
    vai_tro_id=3,
    ma_vai_tro="nhan_vien",
    trang_thai="hoat_dong",
    ten_dang_nhap="new.employee",
    ngay_sinh=None,
    so_dien_thoai=None,
    email=None,
    ngay_vao_lam=None,
    he_so_luong=None,
)


class Transaction(AbstractAsyncContextManager):
    def __init__(self, events):
        self.events = events

    async def __aenter__(self):
        self.events.append("begin")
        return self

    async def __aexit__(self, error_type, *_args):
        self.events.append("rollback" if error_type else "commit")
        return False


class CodeSession:
    """Evaluate the aggregate over memory and inspect the actual PostgreSQL query."""

    def __init__(self, employees, events):
        self.employees = employees
        self.events = events

    async def scalar(self, statement):
        sql = str(
            statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        )
        assert 'max(CAST(right("NhanVien".ma_nhan_vien, 6) AS INTEGER))' in sql
        assert 'FROM "NhanVien"' in sql and "WHERE" not in sql
        self.events.append("max")
        return max((int(employee[0][-6:]) for employee in self.employees), default=None)


def feature(monkeypatch, employees):
    events = []
    repo, audit = AsyncMock(), AsyncMock()
    allocator = SqlAlchemyNhanVienRepository(CodeSession(employees, events))

    async def lock(_id):
        events.append("admin_lock")
        return SimpleNamespace(
            trang_thai="hoat_dong", roles=["quan_tri_vien"], password_hash="admin-hash"
        )

    async def create(employee):
        events.append("insert")
        return replace(
            RECORD,
            ma_nhan_vien=employee.ma_nhan_vien,
            vai_tro_id=employee.vai_tro_id,
            ma_vai_tro=repo.get_role.return_value.ma_vai_tro,
        )

    repo.lock_credentials_by_id.side_effect = lock
    repo.get_role.return_value = VaiTroRead(
        id=3, ma_vai_tro="nhan_vien", ten_vai_tro="Nhân viên", mo_ta=None
    )
    repo.find_by_username.return_value = None
    repo.next_employee_code.side_effect = allocator.next_employee_code
    repo.create.side_effect = create
    monkeypatch.setattr(
        "app.modules.nhan_vien.service.get_password_hash", lambda _password: "test-hash"
    )
    service = NhanVienService(repo, audit, Transaction(events))
    return service, repo, audit, events


# UC-04 R6: mã max+1 kể cả tài khoản khóa, rỗng và biên; cấp dưới khóa trong transaction
@pytest.mark.parametrize(
    "employees,expected",
    [
        ([("NV-000008", "hoat_dong")], "NV-000009"),
        ([("NV-000003", "hoat_dong"), ("NV-000008", "bi_khoa")], "NV-000009"),
        ([], "NV-000001"),
        ([("NV-999998", "bi_khoa")], "NV-999999"),
    ],
)
async def test_code_includes_locked_accounts_and_is_allocated_under_admin_lock(
    monkeypatch, employees, expected
):
    service, repo, audit, events = feature(monkeypatch, employees)
    response, etag = await service.create_employee(NhanVienCreate(**BODY), ACTOR, "req")
    assert response.data.ma_nhan_vien == expected and etag.startswith('"')
    assert events == ["begin", "admin_lock", "max", "insert", "commit"]
    assert repo.create.call_args.args[0].ma_nhan_vien == expected
    assert "ma_nhan_vien" not in repo.create.call_args.args[0].profile
    assert audit.append.call_args.args[0].du_lieu_sau["ma_nhan_vien"] == expected


async def post(service, body):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user_payload] = lambda: ACTOR
    app.dependency_overrides[get_nhan_vien_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/v1/nhan_vien", json=body)


# UC-04 A4: gửi kèm mã nhân viên bị từ chối trước mọi truy cập repository
async def test_client_employee_code_is_rejected_with_422(monkeypatch):
    service, repo, _, events = feature(monkeypatch, [])
    response = await post(service, {**BODY, "ma_nhan_vien": "NV-000008"})
    assert response.status_code == 422
    assert "ma_nhan_vien" in response.text
    assert not events
    assert repo.mock_calls == []
    repo.create.assert_not_awaited()


# UC-04 R6: hết dải trả 409, rollback và không tạo tài khoản/lịch sử
async def test_exhaustion_returns_409_without_create_or_audit(monkeypatch):
    service, repo, audit, events = feature(monkeypatch, [("NV-999999", "bi_khoa")])
    response = await post(service, BODY)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert response.json()["error"]["message"] == "Đã hết mã nhân viên khả dụng"
    assert events == ["begin", "admin_lock", "max", "rollback"]
    repo.create.assert_not_awaited()
    audit.append.assert_not_awaited()


# UC-04 R6: API trả mã tự cấp cùng Location, ETag và không lộ mật khẩu
async def test_create_http_returns_generated_code_location_and_etag(monkeypatch):
    service, _, _, _ = feature(monkeypatch, [("NV-000008", "bi_khoa")])
    response = await post(service, BODY)
    assert response.status_code == 201
    assert response.json()["data"]["ma_nhan_vien"] == "NV-000009"
    assert response.headers["location"] == "/api/v1/nhan_vien/9"
    assert response.headers["etag"].startswith('"')
    assert "mat_khau" not in response.json()["data"]


# UC-04 AC-1: cho phép tạo thêm QTV với mã tự cấp và lịch sử
async def test_can_create_second_admin(monkeypatch):
    service, repo, audit, events = feature(monkeypatch, [])
    repo.get_role.return_value = VaiTroRead(
        id=1, ma_vai_tro="quan_tri_vien", ten_vai_tro="Quản trị viên", mo_ta=None
    )
    response = await post(service, {**BODY, "vai_tro_id": 1})
    assert response.status_code == 201
    assert response.json()["data"]["ma_vai_tro"] == "quan_tri_vien"
    assert response.json()["data"]["ma_nhan_vien"] == "NV-000001"
    assert events == ["begin", "admin_lock", "max", "insert", "commit"]
    repo.next_employee_code.assert_awaited_once()
    audit.append.assert_awaited_once()


# UC-04 R6: trùng mã khi tạo đồng thời trả 409, rollback và không ghi lịch sử
async def test_concurrent_code_conflict_returns_409(monkeypatch):
    service, repo, audit, events = feature(monkeypatch, [])
    message = "Mã nhân viên vừa được cấp cho tài khoản khác, vui lòng thử lại"
    repo.create.side_effect = DuplicateCodeException(message=message)
    response = await post(service, BODY)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ma_bi_trung"
    assert response.json()["error"]["message"] == message
    assert events == ["begin", "admin_lock", "max", "rollback"]
    audit.append.assert_not_awaited()
