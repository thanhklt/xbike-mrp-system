"""UC-43 HTTP boundary, real JWT/auth policy, fake credential/audit repositories."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from test_audit_service import record

from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, password_version
from app.dependencies import get_audit_service, get_auth_service
from app.modules.audit.router import router
from app.modules.audit.schemas import AuditListQuery
from app.modules.audit.service import AuditService
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.schemas import EmployeeCredentials
from app.modules.nhan_vien.service import NhanVienService
from app.shared.records import RecordPage


def credential(employee_id, role, state="hoat_dong"):
    return EmployeeCredentials(
        id=employee_id,
        email=None,
        ho_ten=None,
        ten_dang_nhap=f"reader-{employee_id}",
        roles=[role],
        trang_thai=state,
        password_hash="test-credential-hash",
        ma_nhan_vien=f"NV-{employee_id:06}",
        vai_tro_id=employee_id,
        ma_vai_tro=role,
        ngay_sinh=None,
        so_dien_thoai=None,
        ngay_vao_lam=None,
        he_so_luong=None,
    )


def auth_headers(employee_id=1, *, claimed_role=None, version=None, expires=None):
    token = create_access_token(
        str(employee_id),
        roles=[claimed_role or "quan_tri_vien"],
        credential_version=version or password_version("test-credential-hash"),
        expires_delta=expires,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def api():
    people = {
        1: credential(1, "quan_tri_vien"),
        2: credential(2, "quan_ly"),
        3: credential(3, "nhan_vien"),
        4: credential(4, "quan_ly", "bi_khoa"),
    }
    repo = AsyncMock()
    repo.list_entries.return_value = RecordPage([record()], 1)
    repo.get_entry.return_value = record()
    credential_repo = AsyncMock()
    credential_repo.get_credentials_by_id.side_effect = people.get
    service = AuditService(repo)
    auth = AuthService(NhanVienService(credential_repo, AsyncMock(), AsyncMock()))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_audit_service] = lambda: service
    app.dependency_overrides[get_auth_service] = lambda: auth
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield SimpleNamespace(
            client=client, repo=repo, people=people, app=app, credentials=credential_repo
        )


@pytest.mark.parametrize("employee_id", [1, 2])
async def test_uc43_ac07_ac13_http_contract_for_both_roles(api, employee_id):
    headers = auth_headers(employee_id)
    listing = await api.client.get("/api/v1/audit", headers=headers)
    detail = await api.client.get("/api/v1/audit/1", headers=headers)
    assert listing.status_code == detail.status_code == 200
    body = listing.json()
    assert set(body) == {"success", "data", "pagination", "message"}
    assert body["data"] == [detail.json()["data"]]
    assert body["pagination"] == {
        "page": 1,
        "page_size": 20,
        "total_items": 1,
        "total_pages": 1,
        "has_next": False,
        "has_prev": False,
    }
    assert detail.json()["data"]["du_lieu_truoc"] is None
    assert detail.json()["data"]["trang_thai_sau"] == "cho_bo_sung_linh_kien"
    api.repo.append.assert_not_awaited()


@pytest.mark.parametrize("path", ["/api/v1/audit", "/api/v1/audit/1"])
@pytest.mark.parametrize(
    "headers,status",
    [
        ({}, 401),
        ({"Authorization": "Bearer invalid"}, 401),
        (auth_headers(1, expires=timedelta(seconds=-5)), 401),
        (auth_headers(1, version="stale"), 401),
        (auth_headers(3, claimed_role="quan_tri_vien"), 403),
        (auth_headers(4), 403),
        (auth_headers(999), 401),
    ],
)
async def test_uc43_ac03_ac09_auth_uses_current_database_identity(api, path, headers, status):
    response = await api.client.get(path, headers=headers)
    assert response.status_code == status
    assert "data" not in response.json()
    api.repo.list_entries.assert_not_awaited()
    api.repo.get_entry.assert_not_awaited()


async def test_uc43_ac09_locking_or_changing_role_takes_effect_on_next_request(api):
    headers = auth_headers(2)
    assert (await api.client.get("/api/v1/audit", headers=headers)).status_code == 200
    api.people[2] = credential(2, "quan_ly", "bi_khoa")
    assert (await api.client.get("/api/v1/audit", headers=headers)).status_code == 403
    api.people[2] = credential(2, "nhan_vien")
    assert (await api.client.get("/api/v1/audit/1", headers=headers)).status_code == 403
    assert api.repo.list_entries.await_count == 1
    api.repo.get_entry.assert_not_awaited()


async def test_uc43_ac09_database_role_grants_access_even_if_token_claim_is_outdated(api):
    response = await api.client.get(
        "/api/v1/audit", headers=auth_headers(2, claimed_role="nhan_vien")
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"sort_by": "du_lieu_truoc"},
        {"sort_by": "created_at; DROP TABLE"},
        {"sort_order": "up"},
        {"nhan_vien_id": "true"},
        {"nhan_vien_id": -1},
        {"doi_tuong_id": 2**31},
        {"loai_doi_tuong": "ticket_loi_dieu_chinh"},
        {"thao_tac": "unknown"},
        {"bo_thao_tac": "unknown"},
        {"tu_ngay": "20261114"},
        {"tu_ngay": "2026-W46-6"},
        {"tu_ngay": "2026-11-14T00:00:00Z"},
        {"tu_ngay": "2026-02-30"},
        {"den_ngay": "9999-12-31"},
        {"tu_ngay": "0001-01-01"},
        {"tu_ngay": "2026-11-15", "den_ngay": "2026-11-14"},
        {"unknown": "value"},
        [("page", "1"), ("page", "2")],
        [("thao_tac", "tao"), ("thao_tac", "sua")],
    ],
)
async def test_uc43_ac11_ac12_invalid_query_is_422_not_ignored(api, params):
    response = await api.client.get("/api/v1/audit", params=params, headers=auth_headers())
    assert response.status_code == 422, response.text
    api.repo.list_entries.assert_not_awaited()


@pytest.mark.parametrize(
    "entry_id,status", [("0", 422), ("-1", 422), ("abc", 422), (str(2**31), 404)]
)
async def test_uc43_ac13_detail_id_validation(api, entry_id, status):
    response = await api.client.get(f"/api/v1/audit/{entry_id}", headers=auth_headers())
    assert response.status_code == status
    api.repo.get_entry.assert_not_awaited()


async def test_uc43_ac13_detail_rejects_query_and_reports_missing_record(api):
    response = await api.client.get("/api/v1/audit/1?page=1", headers=auth_headers())
    assert response.status_code == 422
    api.repo.get_entry.assert_not_awaited()
    api.repo.get_entry.return_value = None
    response = await api.client.get("/api/v1/audit/1", headers=auth_headers())
    assert response.status_code == 404


async def test_uc43_ac06_ac10_all_filters_reach_service_and_legacy_exclusion_remains_valid(api):
    params = {
        "page": 2,
        "page_size": 5,
        "search": " sample ",
        "sort_by": "id",
        "sort_order": "asc",
        "nhan_vien_id": 2,
        "loai_doi_tuong": "cong_thuc",
        "doi_tuong_id": 10,
        "thao_tac": "tao_phien_ban",
        "bo_thao_tac": "thu_hoi_quyen",
        "tu_ngay": "2026-11-14",
        "den_ngay": "2026-11-14",
    }
    response = await api.client.get("/api/v1/audit", params=params, headers=auth_headers())
    assert response.status_code == 200
    expected = AuditListQuery(**params)
    assert api.repo.list_entries.call_args.args == (expected,)
    assert (
        api.repo.list_entries.call_args.kwargs["created_from"].isoformat()
        == "2026-11-13T17:00:00+00:00"
    )


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", ["/api/v1/audit", "/api/v1/audit/1"])
async def test_uc43_ac02_ac16_no_http_writes(api, method, path):
    response = await api.client.request(
        method, path, headers=auth_headers(), json={"ly_do": "tamper"}
    )
    assert response.status_code == 405
    api.repo.append.assert_not_awaited()
    api.repo.list_entries.assert_not_awaited()
    api.repo.get_entry.assert_not_awaited()


async def test_uc43_ac04_ac15_both_endpoints_redact_before_serialization(api):
    saved = record(du_lieu_sau={"da_doi_mat_khau": True, "nested": [{"matKhau": "secret"}]})
    api.repo.get_entry.return_value = saved
    api.repo.list_entries.return_value = RecordPage([saved], 1)
    for path in ("/api/v1/audit", "/api/v1/audit/1"):
        response = await api.client.get(path, headers=auth_headers())
        assert response.status_code == 200
        assert "secret" not in response.text and "matKhau" not in response.text
        assert "da_doi_mat_khau" in response.text
    assert saved.du_lieu_sau["nested"][0]["matKhau"] == "secret"


@pytest.mark.parametrize("path", ["/api/v1/audit", "/api/v1/audit/1"])
async def test_uc43_ac18_unexpected_database_error_is_sanitized(api, path):
    api.repo.list_entries.side_effect = RuntimeError("SELECT password FROM host:secret@database")
    api.repo.get_entry.side_effect = api.repo.list_entries.side_effect
    response = await api.client.get(path, headers=auth_headers())
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}


def test_uc43_openapi_documents_both_read_endpoints_and_query(api):
    schema = api.app.openapi()
    listing = schema["paths"]["/api/v1/audit"]["get"]
    detail = schema["paths"]["/api/v1/audit/{id}"]["get"]
    for operation in (listing, detail):
        assert "UC-43" in operation["description"]
        assert "specs/use_cases/audit/UC-43.md" in operation["description"]
        assert all(
            parameter["name"].lower() != "if-match" for parameter in operation.get("parameters", [])
        )
        assert operation["security"]
    names = {parameter["name"] for parameter in listing["parameters"]}
    assert names == set(AuditListQuery.model_fields)
