"""UC-03 API contracts and real repository queries on isolated SQLite tables."""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, get_password_hash, password_version
from app.dependencies import get_auth_service, get_nhan_vien_service
from app.modules.audit.service import AuditService
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.models import NhanVien, VaiTro
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router
from app.modules.nhan_vien.schemas import EmployeeCredentials, EmployeeRecord, NhanVienListQuery
from app.modules.nhan_vien.service import NhanVienService
from app.shared.records import RecordPage

LIST_URL = "/api/v1/nhan_vien"
PROFILE = {
    "ngay_sinh": date(1990, 2, 3),
    "so_dien_thoai": "0901234567",
    "email": "uc03@example.test",
    "ngay_vao_lam": date(2020, 4, 5),
    "he_so_luong": Decimal("1.25"),
}
JSON_PROFILE = {
    **PROFILE,
    "ngay_sinh": "1990-02-03",
    "ngay_vao_lam": "2020-04-05",
    "he_so_luong": "1.25",
}
MANAGER_FIELDS = {
    "id",
    "ma_nhan_vien",
    "ho_ten",
    "vai_tro_id",
    "ma_vai_tro",
    "trang_thai",
    *PROFILE,
}
SEEDS = [
    (1, 1, "NV-000006", "Zoe Admin", "admin", "hoat_dong"),
    (2, 2, "NV-000002", "Binh Manager", "manager", "hoat_dong"),
    (3, 3, "NV-000005", "An Worker", "login-only-match", "hoat_dong"),
    (4, 3, "NV-000001", "An Worker", "locked-worker", "bi_khoa"),
    (5, 2, "NV-000004", "Rate% Person", "locked-manager", "bi_khoa"),
    (6, 3, "NV-000003", "Under_score Person", "worker-six", "hoat_dong"),
]
ROLES = {1: "quan_tri_vien", 2: "quan_ly", 3: "nhan_vien"}


@pytest.fixture
def records():
    return [
        EmployeeRecord(
            id=id_,
            vai_tro_id=role,
            ma_vai_tro=ROLES[role],
            ma_nhan_vien=code,
            ho_ten=name,
            ten_dang_nhap=login,
            trang_thai=status,
            **PROFILE,
        )
        for id_, role, code, name, login, status in SEEDS
    ]


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash("UC03-test-password")


@pytest.fixture
async def api(records, password_hash):
    credentials = {
        row.id: EmployeeCredentials(
            **asdict(row),
            roles=[row.ma_vai_tro],
            password_hash=password_hash,
        )
        for row in records
    }
    repo = AsyncMock()
    repo.get_credentials_by_id.side_effect = credentials.get
    repo.get_by_id.side_effect = lambda id_: next((r for r in records if r.id == id_), None)
    # API tests exercise HTTP/auth/projections; filtering and ordering use real SQL below.
    repo.list_employees.side_effect = lambda params: RecordPage(
        records[(params.page - 1) * params.page_size : params.page * params.page_size],
        len(records),
    )
    audit_repo, transaction = AsyncMock(), AsyncMock()
    service = NhanVienService(repo, AuditService(audit_repo), transaction)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_nhan_vien_service] = lambda: service
    app.dependency_overrides[get_auth_service] = lambda: AuthService(service)
    tokens = {
        id_: {
            "Authorization": "Bearer "
            + create_access_token(
                id_,
                roles=user.roles,
                credential_version=password_version(user.password_hash),
            )
        }
        for id_, user in credentials.items()
    }
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield SimpleNamespace(client=client, headers=tokens, repo=repo, records=records)
    audit_repo.append.assert_not_called()
    transaction.__aenter__.assert_not_awaited()


@pytest.fixture
async def repository(records, password_hash):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda conn: NhanVien.metadata.create_all(
                    conn,
                    tables=[VaiTro.__table__, NhanVien.__table__],
                )
            )
            tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
            assert set(tables) == {"VaiTro", "NhanVien"}
        async with AsyncSession(engine, expire_on_commit=False) as session:
            session.add_all(
                [VaiTro(id=id_, ma_vai_tro=code, ten_vai_tro=code) for id_, code in ROLES.items()]
            )
            await session.flush()
            session.add_all(
                [
                    NhanVien(
                        **{k: v for k, v in asdict(row).items() if k != "ma_vai_tro"},
                        mat_khau=password_hash,
                    )
                    for row in records
                ]
            )
            await session.flush()
            yield SqlAlchemyNhanVienRepository(session)
            await session.rollback()
    finally:
        await engine.dispose()


# UC-03 AC-1: Quản trị viên thấy toàn bộ tài khoản, kể cả bị khóa
async def test_admin_list_contains_all_accounts(api):
    response = await api.client.get(LIST_URL, headers=api.headers[1])

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == len(SEEDS)
    assert {r["id"] for r in body["data"]} == {r.id for r in api.records}
    assert any(r["trang_thai"] == "bi_khoa" for r in body["data"])
    for row in body["data"]:
        assert set(row) == MANAGER_FIELDS | {"ten_dang_nhap"}
        assert row["ten_dang_nhap"] == api.records[row["id"] - 1].ten_dang_nhap
        assert not {"mat_khau", "password_hash"}.intersection(row)


# UC-03 AC-2: Người không có quyền bị chặn — Nhân viên không được xem danh sách
async def test_employee_cannot_list_accounts(api):
    response = await api.client.get(LIST_URL, headers=api.headers[3])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    api.repo.list_employees.assert_not_awaited()


# UC-03 A4: Chưa đăng nhập hoặc tài khoản đã bị khóa — không có token
async def test_missing_token_is_unauthorized(api):
    response = await api.client.get(LIST_URL)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    api.repo.list_employees.assert_not_awaited()


# UC-03 A4: Chưa đăng nhập hoặc tài khoản đã bị khóa — chặn token còn hạn
async def test_locked_account_is_forbidden(api):
    response = await api.client.get(LIST_URL, headers=api.headers[4])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    api.repo.list_employees.assert_not_awaited()


# UC-03 R4: QLK nhận đủ hồ sơ trừ tên đăng nhập và mật khẩu ở danh sách, chi tiết người khác
@pytest.mark.parametrize("path", [LIST_URL, f"{LIST_URL}/3"])
async def test_manager_projection_has_all_noncredential_fields(api, path):
    response = await api.client.get(path, headers=api.headers[2])

    assert response.status_code == 200
    data = response.json()["data"]
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        expected = asdict(api.records[row["id"] - 1])
        expected.pop("ten_dang_nhap")
        expected.update(JSON_PROFILE)
        assert set(row) == MANAGER_FIELDS
        assert row == expected
        assert not {"ten_dang_nhap", "mat_khau", "password_hash"}.intersection(row)
    if not isinstance(data, list):
        assert response.headers["ETag"].startswith('"')


# UC-03 R4: QTV và chính chủ thấy tên đăng nhập, không response nào chứa hash mật khẩu
@pytest.mark.parametrize(("actor", "target"), [(1, 3), (2, 2), (3, 3)])
async def test_admin_and_owner_receive_full_detail(api, actor, target):
    response = await api.client.get(f"{LIST_URL}/{target}", headers=api.headers[actor])

    assert response.status_code == 200
    row = response.json()["data"]
    expected = asdict(api.records[target - 1])
    expected.update(JSON_PROFILE)
    assert set(row) == MANAGER_FIELDS | {"ten_dang_nhap"}
    assert row == expected
    assert not {"mat_khau", "password_hash"}.intersection(row)


# UC-03 A2: Chuyển trang — giữ tiêu chí và meta, không lặp, trang vượt tổng rỗng
async def test_api_pagination_and_out_of_range_page(api):
    ids = []
    criteria = {"page_size": 2, "sort": "ho_ten", "q": "NV-"}
    for page in range(1, 5):
        response = await api.client.get(
            LIST_URL,
            headers=api.headers[1],
            params={**criteria, "page": page},
        )
        assert response.status_code == 200
        body = response.json()
        assert {k: body["meta"][k] for k in ("page", "page_size", "total", "total_pages")} == {
            "page": page,
            "page_size": 2,
            "total": 6,
            "total_pages": 3,
        }
        assert isinstance(body["meta"]["request_id"], str)
        ids.extend(row["id"] for row in body["data"])
        received = api.repo.list_employees.call_args.args[0]
        assert received == NhanVienListQuery(**criteria, page=page)
    assert body["data"] == []
    assert len(ids) == len(set(ids)) == 6
    assert set(ids) == {row.id for row in api.records}


# UC-03 A2: Chuyển trang — giới hạn kích thước trang tối đa 100
async def test_page_size_above_limit_is_invalid(api):
    response = await api.client.get(LIST_URL, headers=api.headers[1], params={"page_size": 101})

    assert response.status_code == 422
    api.repo.list_employees.assert_not_awaited()


# UC-03 AC-1: Quản trị viên thấy toàn bộ tài khoản — SQL không lọc mặc định tài khoản khóa
async def test_repository_includes_locked_accounts(repository):
    result = await repository.list_employees(NhanVienListQuery())

    assert result.total == len(SEEDS)
    assert {r.id for r in result.items} == {1, 2, 3, 4, 5, 6}
    assert {r.id for r in result.items if r.trang_thai == "bi_khoa"} == {4, 5}


# UC-03 AC-3: Tìm kiếm, lọc đúng tiêu chí — mã/họ tên, ASCII hoa thường, escape và không tìm login
@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("v-000005", {3}),
        ("AN WORK", {3, 4}),
        ("login-only-match", set()),
        ("%", {5}),
        ("_", {6}),
    ],
)
async def test_repository_search(repository, q, expected):
    result = await repository.list_employees(NhanVienListQuery(q=q))

    assert {r.id for r in result.items} == expected
    assert result.total == len(expected)


# UC-03 AC-3: Tìm kiếm, lọc đúng tiêu chí — vai trò, trạng thái và giao mọi điều kiện
@pytest.mark.parametrize(
    ("criteria", "expected"),
    [
        ({"vai_tro_id": 3}, {3, 4, 6}),
        ({"trang_thai": "bi_khoa"}, {4, 5}),
        ({"q": "An", "vai_tro_id": 3, "trang_thai": "bi_khoa"}, {4}),
    ],
)
async def test_repository_filters(repository, criteria, expected):
    result = await repository.list_employees(NhanVienListQuery(**criteria))

    assert {r.id for r in result.items} == expected
    assert result.total == len(expected)


# UC-03 AC-3: Tìm kiếm, lọc đúng tiêu chí — R3 sắp xếp bốn chiều, trùng họ tên theo id tăng
@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("ma_nhan_vien", [4, 2, 6, 5, 3, 1]),
        ("-ma_nhan_vien", [1, 3, 5, 6, 2, 4]),
        ("ho_ten", [3, 4, 2, 5, 6, 1]),
        ("-ho_ten", [1, 6, 5, 2, 3, 4]),
    ],
)
async def test_repository_sorting(repository, sort, expected):
    result = await repository.list_employees(NhanVienListQuery(sort=sort))

    assert [r.id for r in result.items] == expected


# UC-03 A1: Không có tài khoản thỏa tiêu chí — SQL trả danh sách rỗng và tổng 0
async def test_repository_no_matches(repository):
    result = await repository.list_employees(NhanVienListQuery(q="no-such-person"))

    assert result.items == []
    assert result.total == 0


# UC-03 A2: Chuyển trang — SQL giữ tiêu chí, thứ tự ổn định, không lặp và trang vượt tổng rỗng
@pytest.mark.parametrize("criteria", [{}, {"q": "An", "vai_tro_id": 3}])
async def test_repository_pagination(repository, criteria):
    full = await repository.list_employees(NhanVienListQuery(**criteria, sort="ho_ten"))
    ids = []
    for page in range(1, (full.total + 1) // 2 + 2):
        result = await repository.list_employees(
            NhanVienListQuery(
                **criteria,
                sort="ho_ten",
                page_size=2,
                page=page,
            )
        )
        assert result.total == full.total
        ids.extend(r.id for r in result.items)
    assert result.items == []
    assert ids == [r.id for r in full.items]
    assert len(ids) == len(set(ids)) == full.total
