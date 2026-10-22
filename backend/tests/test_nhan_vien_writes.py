"""Employee mutations exercise HTTP, persistence and audit in an isolated database."""

from datetime import datetime, timezone
from decimal import Decimal

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.core.database import Base, get_db
from app.core.security import create_access_token, verify_password
from app.modules.audit.models import AuditTrailLog
from app.modules.nhan_vien.models import Role, User


@compiles(JSONB, "sqlite")
def compile_jsonb_for_test(element, compiler, **kwargs):
    return "JSON"


def headers(user_id):
    return {"Authorization": f"Bearer {create_access_token(user_id, ['quan_tri_vien'])}"}


@pytest.fixture
async def employee_client():
    from app.main import app

    engine = create_async_engine("sqlite+aiosqlite://")

    @event.listens_for(engine.sync_engine, "connect")
    def sqlite_functions(connection, record):
        connection.create_function(
            "now", 0, lambda: datetime.now(timezone.utc).replace(tzinfo=None).isoformat(" ")
        )
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda connection: Base.metadata.create_all(
                connection, tables=[Role.__table__, User.__table__, AuditTrailLog.__table__]
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                Role(id=1, ma_vai_tro="quan_tri_vien", ten_vai_tro="Quản trị viên"),
                Role(id=2, ma_vai_tro="quan_ly", ten_vai_tro="Quản lý"),
                Role(id=3, ma_vai_tro="nhan_vien", ten_vai_tro="Nhân viên"),
            ]
        )
        for employee_id, role_id in [(1, 1), (2, 2), (3, 3), (4, 3), (5, 1)]:
            session.add(
                User(
                    id=employee_id,
                    vai_tro_id=role_id,
                    ten_dang_nhap=f"user{employee_id}",
                    ma_nhan_vien=f"NV-{employee_id:06}",
                    mat_khau="legacy-private-hash",
                    ho_ten=f"Employee {employee_id}",
                    trang_thai="hoat_dong",
                    email=f"user{employee_id}@example.com",
                    he_so_luong=Decimal("1.25"),
                )
            )
        await session.commit()

        async def override_db():
            yield session

        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client, session
        finally:
            app.dependency_overrides = previous
    await engine.dispose()


async def conditional_headers(client, employee_id=3, actor_id=1):
    result = await client.get(f"/api/v1/nhan_vien/{employee_id}", headers=headers(actor_id))
    assert result.status_code == 200
    return {**headers(actor_id), "If-Match": result.headers["etag"]}


def new_employee(**changes):
    return {
        "ten_dang_nhap": "new-user",
        "mat_khau": "Mật khẩu đủ dài 🔒",
        "ma_nhan_vien": "NV-000006",
        "vai_tro_id": 3,
        "ho_ten": " New Employee ",
        "he_so_luong": "2.50",
        **changes,
    }


async def test_create_hashes_password_and_commits_one_redacted_audit(employee_client):
    client, session = employee_client
    response = await client.post("/api/v1/nhan_vien", headers=headers(1), json=new_employee())
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["id"] > 5 and data["ho_ten"] == "New Employee"
    assert data["trang_thai"] == "hoat_dong" and data["he_so_luong"] == "2.50"
    assert response.headers["location"] == f"/api/v1/nhan_vien/{data['id']}"
    assert response.headers["etag"]
    stored = await session.get(User, data["id"])
    assert stored.mat_khau.startswith("$argon2id$")
    assert verify_password(new_employee()["mat_khau"], stored.mat_khau)
    audit = await session.scalar(select(AuditTrailLog))
    assert audit.thao_tac == "tao" and audit.doi_tuong_id == data["id"]
    assert "mat_khau" not in audit.du_lieu_sau and "tai_khoan_id" not in audit.du_lieu_sau
    assert "mat_khau" not in response.text and new_employee()["mat_khau"] not in response.text


@pytest.mark.parametrize("actor_id", [2, 3])
async def test_non_admin_cannot_create_or_change_others(employee_client, actor_id):
    client, session = employee_client
    result = await client.post("/api/v1/nhan_vien", headers=headers(actor_id), json=new_employee())
    assert result.status_code == 403
    condition = await conditional_headers(client)
    condition.update(headers(actor_id))
    for method, path, body in [
        ("patch", "/3", {"ho_ten": "Forbidden"}),
        ("put", "/3/vai_tro", {"vai_tro_id": 1}),
        ("post", "/3/vo_hieu_hoa", {"ly_do": "Forbidden"}),
        ("delete", "/3", None),
    ]:
        if method == "patch" and actor_id == 3:
            path = "/4"
        response = await client.request(
            method,
            "/api/v1/nhan_vien" + path,
            headers=condition,
            **({"json": body} if body else {}),
        )
        assert response.status_code == 403, response.text
    assert await session.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


@pytest.mark.parametrize("actor_id", [2, 3])
async def test_self_patch_allows_contact_fields_and_preserves_other_fields(
    employee_client, actor_id
):
    client, session = employee_client
    condition = await conditional_headers(client, actor_id, actor_id)
    response = await client.patch(
        f"/api/v1/nhan_vien/{actor_id}",
        headers=condition,
        json={"ho_ten": " My Name ", "email": None, "ngay_sinh": "2000-01-01"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["ho_ten"] == "My Name"
    assert response.json()["data"]["email"] is None
    assert response.json()["data"]["he_so_luong"] == "1.25"
    assert response.headers["etag"] != condition["If-Match"]
    audit = await session.scalar(select(AuditTrailLog))
    assert audit.du_lieu_truoc["email"] == f"user{actor_id}@example.com"
    assert audit.du_lieu_sau["email"] is None


@pytest.mark.parametrize("field,value", [("he_so_luong", "5.00"), ("ngay_vao_lam", None)])
async def test_self_patch_forbidden_field_rejects_whole_request(employee_client, field, value):
    client, session = employee_client
    response = await client.patch(
        "/api/v1/nhan_vien/3",
        headers=await conditional_headers(client, 3, 3),
        json={"ho_ten": "Must not save", field: value},
    )
    assert response.status_code == 403
    assert (await session.get(User, 3)).ho_ten == "Employee 3"
    assert await session.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


async def test_admin_patch_preserves_omitted_values_and_can_clear_nullable_fields(employee_client):
    client, _ = employee_client
    response = await client.patch(
        "/api/v1/nhan_vien/3",
        headers=await conditional_headers(client),
        json={"he_so_luong": "999.99", "ngay_vao_lam": "2026-10-01"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["email"] == "user3@example.com"
    cleared = await client.patch(
        "/api/v1/nhan_vien/3",
        headers={**headers(1), "If-Match": response.headers["etag"]},
        json={"he_so_luong": None},
    )
    assert cleared.status_code == 200 and cleared.json()["data"]["he_so_luong"] is None


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("patch", "", {"ho_ten": "Changed"}),
        ("put", "/vai_tro", {"vai_tro_id": 2}),
        ("post", "/vo_hieu_hoa", {"ly_do": "Reason"}),
        ("delete", "", None),
    ],
)
async def test_mutations_require_current_etag(employee_client, method, suffix, body):
    client, session = employee_client
    for condition, expected in [(headers(1), 428), ({**headers(1), "If-Match": '"stale"'}, 412)]:
        response = await client.request(
            method,
            "/api/v1/nhan_vien/3" + suffix,
            headers=condition,
            **({"json": body} if body else {}),
        )
        assert response.status_code == expected, response.text
        assert response.json()["meta"]["request_id"]
    assert await session.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


async def test_soft_delete_keeps_row_and_audit_and_blocks_existing_token(employee_client):
    client, session = employee_client
    condition = await conditional_headers(client)
    result = await client.delete("/api/v1/nhan_vien/3", headers=condition)
    assert result.status_code == 204 and result.content == b""
    assert (await session.get(User, 3)).trang_thai == "bi_khoa"
    assert (await client.get("/api/v1/nhan_vien/3", headers=headers(1))).status_code == 200
    blocked = await client.get("/api/v1/nhan_vien/3", headers=headers(3))
    assert (
        blocked.status_code == 403 and blocked.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    )
    again = await client.delete("/api/v1/nhan_vien/3", headers=await conditional_headers(client))
    assert again.status_code == 204
    assert await session.scalar(select(func.count()).select_from(AuditTrailLog)) == 1


async def test_disable_requires_reason_and_rejects_wrong_state(employee_client):
    client, session = employee_client
    condition = await conditional_headers(client)
    blank = await client.post(
        "/api/v1/nhan_vien/3/vo_hieu_hoa", headers=condition, json={"ly_do": " "}
    )
    assert blank.status_code == 422
    response = await client.post(
        "/api/v1/nhan_vien/3/vo_hieu_hoa", headers=condition, json={"ly_do": " Ngừng sử dụng "}
    )
    assert response.status_code == 200 and response.json()["data"]["trang_thai"] == "bi_khoa"
    audit = await session.scalar(select(AuditTrailLog))
    assert audit.ly_do == "Ngừng sử dụng" and audit.thao_tac == "vo_hieu_hoa"
    repeated = await client.post(
        "/api/v1/nhan_vien/3/vo_hieu_hoa",
        headers=await conditional_headers(client),
        json={"ly_do": "Again"},
    )
    assert repeated.status_code == 409


async def test_role_change_updates_response_and_permissions_of_existing_token(employee_client):
    client, _ = employee_client
    response = await client.put(
        "/api/v1/nhan_vien/3/vai_tro",
        headers=await conditional_headers(client),
        json={"vai_tro_id": 2},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["ma_vai_tro"] == "quan_ly"
    assert (await client.get("/api/v1/nhan_vien", headers=headers(3))).status_code == 200


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("delete", "", None),
        ("post", "/vo_hieu_hoa", {"ly_do": "Reason"}),
    ],
)
async def test_admin_cannot_disable_self(employee_client, method, suffix, body):
    client, _ = employee_client
    result = await client.request(
        method,
        "/api/v1/nhan_vien/1" + suffix,
        headers=await conditional_headers(client, 1),
        **({"json": body} if body else {}),
    )
    assert result.status_code == 409


async def test_last_active_admin_cannot_be_demoted(employee_client):
    client, session = employee_client
    other = await session.get(User, 5)
    other.trang_thai = "bi_khoa"
    await session.commit()
    result = await client.put(
        "/api/v1/nhan_vien/1/vai_tro",
        headers=await conditional_headers(client, 1),
        json={"vai_tro_id": 3},
    )
    assert result.status_code == 409
    assert (await session.get(User, 1)).vai_tro_id == 1


@pytest.mark.parametrize(
    "body",
    [
        {"vai_tro_id": 1},
        {"trang_thai": "bi_khoa"},
        {"ten_dang_nhap": "other"},
        {"ma_nhan_vien": "other"},
        {"mat_khau": "private-secret"},
        {"he_so_luong": "1000.00"},
        {"he_so_luong": "1.234"},
        {"he_so_luong": 2.5},
        {"ngay_sinh": 0},
        {"ngay_vao_lam": "2026-10-20T00:00:00Z"},
    ],
)
async def test_patch_rejects_immutable_unknown_or_invalid_fields(employee_client, body):
    client, _ = employee_client
    result = await client.patch(
        "/api/v1/nhan_vien/3", headers=await conditional_headers(client), json=body
    )
    assert result.status_code == 422
    assert "private-secret" not in result.text


@pytest.mark.parametrize("field", ["ten_dang_nhap", "ma_nhan_vien"])
async def test_create_duplicate_returns_conflict_without_extra_account_or_audit(
    employee_client, field
):
    client, session = employee_client
    result = await client.post(
        "/api/v1/nhan_vien",
        headers=headers(1),
        json=new_employee(**{field: "user3" if field == "ten_dang_nhap" else "NV-000003"}),
    )
    assert result.status_code == 409 and result.json()["error"]["code"] == "ma_bi_trung"
    assert await session.scalar(select(func.count()).select_from(User)) == 5
    assert await session.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


async def test_role_listing_uses_v2_pagination_and_permissions(employee_client):
    client, _ = employee_client
    for actor_id in [1, 2]:
        result = await client.get("/api/v1/vai_tro?page=2&page_size=2", headers=headers(actor_id))
        assert result.status_code == 200, result.text
        assert result.json()["data"] == [
            {"id": 3, "ma_vai_tro": "nhan_vien", "ten_vai_tro": "Nhân viên"}
        ]
        assert result.json()["meta"]["total"] == 3
    assert (await client.get("/api/v1/vai_tro", headers=headers(3))).status_code == 403
    assert (await client.get("/api/v1/vai_tro?extra=1", headers=headers(1))).status_code == 422


async def test_audit_failure_rolls_back_profile_change(employee_client):
    from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
    from app.dependencies import get_employee_writer
    from app.main import app
    from app.modules.nhan_vien.repository import SqlAlchemyEmployeeRepository
    from app.modules.nhan_vien.write_service import EmployeeWriter

    client, session = employee_client

    class UnavailableAudit:
        async def append(self, entry):
            raise RuntimeError("Audit unavailable")

    app.dependency_overrides[get_employee_writer] = lambda: EmployeeWriter(
        SqlAlchemyEmployeeRepository(session),
        UnavailableAudit(),
        SqlAlchemyTransaction(session),
        lambda value: value,
    )
    condition = await conditional_headers(client)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        await client.patch(
            "/api/v1/nhan_vien/3", headers=condition, json={"ho_ten": "Do not persist"}
        )
    persisted = await session.scalar(select(User).where(User.id == 3))
    assert persisted.ho_ten == "Employee 3"


def test_bcrypt_passwords_remain_valid_after_argon2_upgrade():
    legacy = bcrypt.hashpw(b"LegacyPassword", bcrypt.gensalt(rounds=4)).decode()
    assert verify_password("LegacyPassword", legacy)
    assert not verify_password("WrongPassword", legacy)


async def test_new_account_can_login_but_blocked_account_cannot(employee_client):
    client, _ = employee_client
    created = await client.post("/api/v1/nhan_vien", headers=headers(1), json=new_employee())
    assert created.status_code == 201
    credentials = {"username": "new-user", "password": new_employee()["mat_khau"]}
    login = await client.post("/api/v1/auth/token", data=credentials)
    assert login.status_code == 200
    employee_id = created.json()["data"]["id"]
    blocked = await client.delete(
        f"/api/v1/nhan_vien/{employee_id}",
        headers={**headers(1), "If-Match": created.headers["etag"]},
    )
    assert blocked.status_code == 204
    assert (await client.post("/api/v1/auth/token", data=credentials)).status_code == 401


@pytest.mark.parametrize("state", [None, "invalid", "bi_khoa"])
async def test_auth_defensively_rejects_legacy_invalid_account_status(state):
    from app.core.errors import InactiveAccountException
    from app.modules.auth.schemas import AuthEmployee
    from app.modules.auth.service import AuthService

    class LegacyAccountRepository:
        async def get_by_id(self, employee_id):
            return AuthEmployee(
                id=employee_id,
                ten_dang_nhap="legacy",
                email=None,
                full_name=None,
                roles=["quan_tri_vien"],
                trang_thai=state,
                password_hash="not-a-password",
            )

    with pytest.raises(InactiveAccountException):
        await AuthService(LegacyAccountRepository()).current_payload(create_access_token(1))


@pytest.mark.parametrize(
    "body",
    [
        {"mat_khau": "secret"},
        {"ten_dang_nhap": " "},
        {"ma_nhan_vien": None},
        {"vai_tro_id": True},
        {"vai_tro_id": None},
        {"vai_tro_id": "3"},
        {"trang_thai": "bi_khoa"},
    ],
)
async def test_create_validates_required_and_server_owned_fields(employee_client, body):
    client, _ = employee_client
    response = await client.post("/api/v1/nhan_vien", headers=headers(1), json=new_employee(**body))
    assert response.status_code == 422
    assert "secret" not in response.text
    assert all(set(detail) == {"field", "reason"} for detail in response.json()["error"]["details"])


async def test_missing_role_and_missing_employee_return_404(employee_client):
    client, _ = employee_client
    missing_role = await client.post(
        "/api/v1/nhan_vien", headers=headers(1), json=new_employee(vai_tro_id=99)
    )
    assert missing_role.status_code == 404
    missing_employee = await client.patch(
        "/api/v1/nhan_vien/999",
        headers={**headers(1), "If-Match": '"unknown"'},
        json={"email": None},
    )
    assert missing_employee.status_code == 404
