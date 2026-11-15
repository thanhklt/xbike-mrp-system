"""Employee code allocation and HTTP contract, without any database connection."""

from contextlib import AbstractAsyncContextManager
from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError

from app.core.errors import InvalidWorkflowState
from app.core.exceptions import register_exception_handlers
from app.core.security import password_version
from app.dependencies import get_current_user_payload, get_nhan_vien_service
from app.modules.nhan_vien.models import NhanVien
from app.modules.nhan_vien.ports import NhanVienRepository
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import EmployeeRecord, NewEmployee, NhanVienCreate, VaiTroRead
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


def feature(monkeypatch, generated_code="NV-000009"):
    events = []
    repo, audit = AsyncMock(spec=NhanVienRepository), AsyncMock()

    async def lock(_id):
        events.append("admin_lock")
        return SimpleNamespace(
            trang_thai="hoat_dong", roles=["quan_tri_vien"], password_hash="admin-hash"
        )

    async def create(employee):
        events.append("insert")
        return replace(
            RECORD,
            ma_nhan_vien=generated_code,
            vai_tro_id=employee.vai_tro_id,
            ma_vai_tro=repo.get_role.return_value.ma_vai_tro,
        )

    repo.lock_credentials_by_id.side_effect = lock
    repo.get_role.return_value = VaiTroRead(
        id=3, ma_vai_tro="nhan_vien", ten_vai_tro="Nhân viên", mo_ta=None
    )
    repo.find_by_username.return_value = None
    repo.create.side_effect = create
    monkeypatch.setattr(
        "app.modules.nhan_vien.service.get_password_hash", lambda _password: "test-hash"
    )
    service = NhanVienService(repo, audit, Transaction(events))
    return service, repo, audit, events


# UC-04 R6: dữ liệu tạo không có mã; response/lịch sử dùng mã repository trả về trong transaction
@pytest.mark.parametrize("expected", ["NV-000001", "NV-000009", "NV-999999"])
async def test_response_and_audit_use_repository_generated_code(monkeypatch, expected):
    service, repo, audit, events = feature(monkeypatch, expected)
    response, etag = await service.create_employee(NhanVienCreate(**BODY), ACTOR, "req")
    assert response.data.ma_nhan_vien == expected and etag.startswith('"')
    assert events == ["begin", "admin_lock", "insert", "commit"]
    assert "ma_nhan_vien" not in asdict(repo.create.call_args.args[0])
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
    service, repo, _, events = feature(monkeypatch)
    response = await post(service, {**BODY, "ma_nhan_vien": "NV-000008"})
    assert response.status_code == 422
    assert "ma_nhan_vien" in response.text
    assert not events
    assert repo.mock_calls == []
    repo.create.assert_not_awaited()


# UC-04 R6: hết dải trả 409, rollback và không tạo tài khoản/lịch sử
async def test_exhaustion_returns_409_without_account_or_audit(monkeypatch):
    service, repo, audit, events = feature(monkeypatch)

    async def exhausted(_employee):
        events.append("insert")
        raise InvalidWorkflowState(message="Đã hết mã nhân viên khả dụng")

    repo.create.side_effect = exhausted
    response = await post(service, BODY)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert response.json()["error"]["message"] == "Đã hết mã nhân viên khả dụng"
    assert events == ["begin", "admin_lock", "insert", "rollback"]
    repo.create.assert_awaited_once()
    audit.append.assert_not_awaited()


# UC-04 R6: API trả mã tự cấp cùng Location, ETag và không lộ mật khẩu
async def test_create_http_returns_generated_code_location_and_etag(monkeypatch):
    service, _, _, _ = feature(monkeypatch)
    response = await post(service, BODY)
    assert response.status_code == 201
    assert response.json()["data"]["ma_nhan_vien"] == "NV-000009"
    assert response.headers["location"] == "/api/v1/nhan_vien/9"
    assert response.headers["etag"].startswith('"')
    assert "mat_khau" not in response.json()["data"]


# UC-04 AC-1: cho phép tạo thêm QTV với mã tự cấp và lịch sử
async def test_can_create_second_admin(monkeypatch):
    service, repo, audit, events = feature(monkeypatch, "NV-000001")
    repo.get_role.return_value = VaiTroRead(
        id=1, ma_vai_tro="quan_tri_vien", ten_vai_tro="Quản trị viên", mo_ta=None
    )
    response = await post(service, {**BODY, "vai_tro_id": 1})
    assert response.status_code == 201
    assert response.json()["data"]["ma_vai_tro"] == "quan_tri_vien"
    assert response.json()["data"]["ma_nhan_vien"] == "NV-000001"
    assert events == ["begin", "admin_lock", "insert", "commit"]
    audit.append.assert_awaited_once()


# UC-04 R6: ORM bỏ mã khỏi INSERT và repository đọc mã DB sinh sau flush/refresh
async def test_repository_omits_code_and_returns_database_values():
    session = AsyncMock()
    session.add = Mock()
    events = []

    async def flush():
        events.append("flush")
        user = session.add.call_args.args[0]
        assert "ma_nhan_vien" not in user.__dict__
        assert NhanVien.__table__.c.ma_nhan_vien.server_default is not None
        statement = NhanVien.__table__.insert().values(
            ten_dang_nhap=user.ten_dang_nhap,
            vai_tro_id=user.vai_tro_id,
            mat_khau=user.mat_khau,
            trang_thai=user.trang_thai,
        )
        assert "ma_nhan_vien" not in statement.compile(dialect=postgresql.dialect()).params

    async def refresh(user):
        events.append("refresh")
        for name, value in asdict(RECORD).items():
            if name != "ma_vai_tro":
                setattr(user, name, value)
        user.role = SimpleNamespace(ma_vai_tro=RECORD.ma_vai_tro)

    session.flush.side_effect = flush
    session.refresh.side_effect = refresh
    result = await SqlAlchemyNhanVienRepository(session).create(
        NewEmployee("new.employee", 3, "hash", {})
    )
    assert result == RECORD
    assert events == ["flush", "refresh"]
    session.refresh.assert_awaited_once_with(session.add.call_args.args[0])


# UC-04 R6: chỉ P0001 kèm NV-NNNNNN được ánh xạ hết dải; giữ nguyên lỗi DB khác
@pytest.mark.parametrize(
    "sqlstate,message,is_exhausted",
    [
        ("P0001", "Hết dải mã nhân viên NV-NNNNNN", True),
        ("P0001", "Không được sửa mã nhân viên", False),
        ("23514", "NV-NNNNNN check violation", False),
    ],
)
async def test_repository_maps_only_employee_code_exhaustion(sqlstate, message, is_exhausted):
    session = AsyncMock()
    session.add = Mock()
    original = RuntimeError(message)
    original.sqlstate = sqlstate
    error = DBAPIError("INSERT", {}, original)
    session.flush.side_effect = error
    with pytest.raises(InvalidWorkflowState if is_exhausted else DBAPIError) as caught:
        await SqlAlchemyNhanVienRepository(session).create(NewEmployee("new", 3, "hash", {}))
    if is_exhausted:
        assert caught.value.message == "Đã hết mã nhân viên khả dụng"
        assert caught.value.__cause__ is error
    else:
        assert caught.value is error
    session.refresh.assert_not_awaited()
