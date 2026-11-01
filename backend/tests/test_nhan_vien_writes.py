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
from app.core.security import create_access_token, password_version, verify_password
from app.modules.audit.models import LichSuThaoTac
from app.modules.nhan_vien.models import NhanVien, VaiTro


@compiles(JSONB, "sqlite")
def compile_jsonb_for_test(element, compiler, **kwargs):
    return "JSON"


def headers(user_id):
    return {
        "Authorization": f"Bearer {create_access_token(user_id, ['quan_tri_vien'], credential_version=password_version('legacy-private-hash'))}"
    }


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
                connection, tables=[VaiTro.__table__, NhanVien.__table__, LichSuThaoTac.__table__]
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                VaiTro(id=1, ma_vai_tro="quan_tri_vien", ten_vai_tro="Quản trị viên"),
                VaiTro(id=2, ma_vai_tro="quan_ly", ten_vai_tro="Quản lý"),
                VaiTro(id=3, ma_vai_tro="nhan_vien", ten_vai_tro="Nhân viên"),
            ]
        )
        for employee_id, role_id in [(1, 1), (2, 2), (3, 3), (4, 3), (5, 3)]:
            session.add(
                NhanVien(
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
    stored = await session.get(NhanVien, data["id"])
    assert stored.mat_khau.startswith("$argon2id$")
    assert verify_password(new_employee()["mat_khau"], stored.mat_khau)
    audit = await session.scalar(select(LichSuThaoTac))
    assert audit.thao_tac == "tao" and audit.doi_tuong_id == data["id"]
    assert "mat_khau" not in audit.du_lieu_sau and "tai_khoan_id" not in audit.du_lieu_sau
    assert "mat_khau" not in response.text and new_employee()["mat_khau"] not in response.text


@pytest.mark.parametrize("coefficient", ["2", "2.5", "0.000"])
async def test_create_etag_matches_persisted_decimal_representation(employee_client, coefficient):
    client, _ = employee_client
    created = await client.post(
        "/api/v1/nhan_vien",
        headers=headers(1),
        json=new_employee(he_so_luong=coefficient),
    )
    assert created.status_code == 201, created.text
    detail = await client.get(created.headers["location"], headers=headers(1))
    assert detail.status_code == 200
    assert created.json()["data"] == detail.json()["data"]
    assert created.headers["etag"] == detail.headers["etag"]
    patched = await client.patch(
        created.headers["location"],
        headers={**headers(1), "If-Match": created.headers["etag"]},
        json={"ho_ten": "Updated immediately"},
    )
    assert patched.status_code == 200


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
        ("post", "/3/mo_khoa", {"ly_do": "Forbidden"}),
        ("delete", "/3", {"ly_do": "Forbidden"}),
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
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


@pytest.mark.parametrize("actor_id", [2, 3])
async def test_self_patch_is_forbidden_for_non_admin(employee_client, actor_id):
    client, session = employee_client
    condition = await conditional_headers(client, actor_id, actor_id)
    response = await client.patch(
        f"/api/v1/nhan_vien/{actor_id}",
        headers=condition,
        json={"ho_ten": "My Name", "email": None},
    )
    assert response.status_code == 403
    assert (await session.get(NhanVien, actor_id)).ho_ten == f"Employee {actor_id}"
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


@pytest.mark.parametrize("field,value", [("he_so_luong", "5.00"), ("ngay_vao_lam", None)])
async def test_self_patch_forbidden_field_rejects_whole_request(employee_client, field, value):
    client, session = employee_client
    response = await client.patch(
        "/api/v1/nhan_vien/3",
        headers=await conditional_headers(client, 3, 3),
        json={"ho_ten": "Must not save", field: value},
    )
    assert response.status_code == 403
    assert (await session.get(NhanVien, 3)).ho_ten == "Employee 3"
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


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
        ("post", "/mo_khoa", {"ly_do": "Reason"}),
        ("delete", "", {"ly_do": "Reason"}),
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
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


async def test_soft_delete_keeps_row_and_audit_and_blocks_existing_token(employee_client):
    client, session = employee_client
    condition = await conditional_headers(client)
    result = await client.request(
        "DELETE", "/api/v1/nhan_vien/3", headers=condition, json={"ly_do": " Ngừng sử dụng "}
    )
    assert result.status_code == 204 and result.content == b""
    assert result.headers["etag"] != condition["If-Match"]
    assert (await session.get(NhanVien, 3)).trang_thai == "bi_khoa"
    assert (await client.get("/api/v1/nhan_vien/3", headers=headers(1))).status_code == 200
    blocked = await client.get("/api/v1/nhan_vien/3", headers=headers(3))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"
    audit = await session.scalar(select(LichSuThaoTac))
    assert audit.ly_do == "Ngừng sử dụng" and audit.thao_tac == "vo_hieu_hoa"
    assert audit.du_lieu_truoc["trang_thai"] == "hoat_dong"
    assert audit.du_lieu_sau["trang_thai"] == "bi_khoa"
    again = await client.request(
        "DELETE",
        "/api/v1/nhan_vien/3",
        headers=await conditional_headers(client),
        json={"ly_do": "Again"},
    )
    assert again.status_code == 409
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 1


@pytest.mark.parametrize("method,suffix", [("DELETE", ""), ("POST", "/mo_khoa")])
@pytest.mark.parametrize(
    "body", [None, {}, {"ly_do": " "}, {"ly_do": None}, {"ly_do": "Reason", "extra": 1}]
)
async def test_status_actions_require_reason(employee_client, method, suffix, body):
    client, session = employee_client
    response = await client.request(
        method, "/api/v1/nhan_vien/3" + suffix, headers=await conditional_headers(client), json=body
    )
    assert response.status_code == 422
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


async def test_unlock_restores_access_and_writes_one_audit(employee_client):
    client, session = employee_client
    deleted = await client.request(
        "DELETE",
        "/api/v1/nhan_vien/3",
        headers=await conditional_headers(client),
        json={"ly_do": "Leave"},
    )
    assert deleted.status_code == 204
    response = await client.post(
        "/api/v1/nhan_vien/3/mo_khoa",
        headers=await conditional_headers(client),
        json={"ly_do": " Return "},
    )
    assert response.status_code == 200
    assert response.json()["data"]["trang_thai"] == "hoat_dong"
    assert response.headers["etag"] != deleted.headers["etag"]
    assert "access_token" not in response.text
    assert (await client.get("/api/v1/nhan_vien/3", headers=headers(3))).status_code == 200
    audits = (await session.scalars(select(LichSuThaoTac).order_by(LichSuThaoTac.id))).all()
    assert [entry.thao_tac for entry in audits] == ["vo_hieu_hoa", "sua"]
    assert audits[1].ly_do == "Return"
    assert audits[1].du_lieu_truoc["trang_thai"] == "bi_khoa"
    repeated = await client.post(
        "/api/v1/nhan_vien/3/mo_khoa",
        headers=await conditional_headers(client),
        json={"ly_do": "Again"},
    )
    assert repeated.status_code == 409
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 2


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


async def test_admin_cannot_disable_self(employee_client):
    client, _ = employee_client
    result = await client.request(
        "DELETE",
        "/api/v1/nhan_vien/1",
        headers=await conditional_headers(client, 1),
        json={"ly_do": "Reason"},
    )
    assert result.status_code == 409


async def test_only_admin_cannot_be_demoted(employee_client):
    client, session = employee_client
    result = await client.put(
        "/api/v1/nhan_vien/1/vai_tro",
        headers=await conditional_headers(client, 1),
        json={"vai_tro_id": 3},
    )
    assert result.status_code == 409
    assert (await session.get(NhanVien, 1)).vai_tro_id == 1


async def test_cannot_create_or_promote_second_admin(employee_client):
    client, session = employee_client
    created = await client.post(
        "/api/v1/nhan_vien", headers=headers(1), json=new_employee(vai_tro_id=1)
    )
    assert created.status_code == 409
    promoted = await client.put(
        "/api/v1/nhan_vien/3/vai_tro",
        headers=await conditional_headers(client),
        json={"vai_tro_id": 1},
    )
    assert promoted.status_code == 409
    assert (
        await session.scalar(
            select(func.count()).select_from(NhanVien).where(NhanVien.vai_tro_id == 1)
        )
        == 1
    )
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


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
        {"ngay_sinh": "1672531200"},
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
    assert await session.scalar(select(func.count()).select_from(NhanVien)) == 5
    assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


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
    from app.dependencies import get_nhan_vien_service
    from app.main import app
    from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
    from app.modules.nhan_vien.service import NhanVienService

    client, session = employee_client

    class UnavailableAudit:
        async def append(self, entry):
            raise RuntimeError("Audit unavailable")

    app.dependency_overrides[get_nhan_vien_service] = lambda: NhanVienService(
        SqlAlchemyNhanVienRepository(session),
        UnavailableAudit(),
        SqlAlchemyTransaction(session),
    )
    condition = await conditional_headers(client)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        await client.patch(
            "/api/v1/nhan_vien/3", headers=condition, json={"ho_ten": "Do not persist"}
        )
    persisted = await session.scalar(select(NhanVien).where(NhanVien.id == 3))
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
    blocked = await client.request(
        "DELETE",
        f"/api/v1/nhan_vien/{employee_id}",
        headers={**headers(1), "If-Match": created.headers["etag"]},
        json={"ly_do": "No longer needed"},
    )
    assert blocked.status_code == 204
    assert (await client.post("/api/v1/auth/token", data=credentials)).status_code == 403


async def test_removed_disable_endpoint_is_not_registered(employee_client):
    client, _ = employee_client
    response = await client.post(
        "/api/v1/nhan_vien/3/vo_hieu_hoa", headers=headers(1), json={"ly_do": "Reason"}
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"mat_khau": "secret"},
        {"ten_dang_nhap": " "},
        {"ma_nhan_vien": None},
        {"ma_nhan_vien": "NV-000000"},
        {"ma_nhan_vien": "NV001"},
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
