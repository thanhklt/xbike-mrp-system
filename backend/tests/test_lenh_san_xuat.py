"""Contract and workflow checks without application database writes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidInputException,
    NotFoundException,
)
from app.core.exceptions import register_exception_handlers
from app.dependencies import get_current_user_payload, get_lenh_san_xuat_service
from app.modules.lenh_san_xuat.router import router
from app.modules.lenh_san_xuat.schemas import (
    LenhListQuery,
    LenhRead,
    LyDoInput,
    NguoiThucHienInput,
    VatTuLenhRead,
)
from app.modules.lenh_san_xuat.service import LenhSanXuatService
from app.shared.records import RecordPage

MANAGER = {"sub": "9", "roles": ["quan_ly"]}
WORKER = {"sub": "7", "roles": ["nhan_vien"]}


@pytest.fixture
def order():
    return LenhRead(
        id=1,
        ma_lenh_san_xuat="LSX-202611-000001",
        yeu_cau_san_xuat_id=1,
        lenh_san_xuat_cha_id=None,
        mat_hang_id=2,
        bom_id=3,
        so_luong=10,
        nhan_vien_id=7,
        trang_thai="nhap",
        created_at=datetime.now(timezone.utc),
        started_at=None,
        completed_at=None,
        nhu_cau_truc_tiep=[dict(id=1, mat_hang_id=4, so_luong_can=20)],
        so_luong_da_hoan_thanh=0,
        so_luong_con_phai_hoan_thanh=10,
        lenh_con_ids=[],
    )


@pytest.fixture
def workflow(order):
    repo, audit, tx = AsyncMock(), AsyncMock(), AsyncMock()
    tx.__aexit__.return_value = False
    repo.get_order.return_value = order
    repo.lock_order.return_value = order
    repo.list_orders.return_value = RecordPage([order], 1)
    repo.employee_active.return_value = True
    repo.request_active.return_value = True
    repo.formula_matches.return_value = True
    repo.has_postings.return_value = False
    repo.has_active_children.return_value = False
    repo.materials.return_value = VatTuLenhRead(
        lenh_san_xuat_id=1, chi_tiet=[], du_dieu_kien_bat_dau=True
    )
    return LenhSanXuatService(repo, audit, tx), repo, audit, tx


@pytest.mark.parametrize("state", ["da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"])
async def test_assignment_only_draft(workflow, order, state):
    service, repo, audit, tx = workflow
    order.trang_thai = state
    with pytest.raises(ConflictException):
        await service.assign(1, 8, MANAGER, "r")
    repo.assign.assert_not_awaited()
    audit.append.assert_not_awaited()
    assert tx.__aexit__.call_args.args[0] is ConflictException


@pytest.mark.parametrize("guard", ["request_active", "formula_matches"])
async def test_send_guards(workflow, guard):
    service, repo, audit, _ = workflow
    getattr(repo, guard).return_value = False
    with pytest.raises(ConflictException):
        await service.send(1, MANAGER, "r")
    repo.transition.assert_not_awaited()
    audit.append.assert_not_awaited()


async def test_invalid_assignee(workflow):
    service, repo, _, _ = workflow
    repo.employee_active.return_value = False
    with pytest.raises(InvalidInputException):
        await service.assign(1, 8, MANAGER, "r")
    with pytest.raises(InvalidInputException):
        await service.send(1, MANAGER, "r")


@pytest.mark.parametrize("actor", [MANAGER, {"sub": "8", "roles": ["nhan_vien"]}])
async def test_start_requires_assigned_worker(workflow, order, actor):
    service, repo, _, _ = workflow
    order.trang_thai = "da_gui"
    with pytest.raises(ForbiddenException):
        await service.start(1, actor, "r")
    repo.transition.assert_not_awaited()


async def test_start_requires_materials(workflow, order):
    service, repo, _, _ = workflow
    order.trang_thai = "da_gui"
    repo.materials.return_value.du_dieu_kien_bat_dau = False
    with pytest.raises(ConflictException):
        await service.start(1, WORKER, "r")
    repo.transition.assert_not_awaited()


@pytest.mark.parametrize("guard", ["has_postings", "has_active_children"])
async def test_cancel_guards(workflow, guard):
    service, repo, audit, _ = workflow
    getattr(repo, guard).return_value = True
    with pytest.raises(ConflictException):
        await service.cancel(1, "Thay đổi", MANAGER, "r")
    repo.transition.assert_not_awaited()
    audit.append.assert_not_awaited()


@pytest.mark.parametrize(
    "action,state,actor",
    [
        ("send", "nhap", MANAGER),
        ("start", "da_gui", WORKER),
        ("cancel", "nhap", MANAGER),
        ("assign", "nhap", MANAGER),
    ],
)
async def test_actions_audit_in_transaction(workflow, order, action, state, actor):
    service, repo, audit, tx = workflow
    order.trang_thai = state
    args = {
        "send": (1, actor, "r"),
        "start": (1, actor, "r"),
        "cancel": (1, "Thay đổi", actor, "r"),
        "assign": (1, 8, actor, "r"),
    }
    result = await getattr(service, action)(*args[action])
    assert result.data.id == 1
    audit.append.assert_awaited_once()
    assert audit.append.call_args.args[0].nhan_vien_id == int(actor["sub"])
    tx.__aenter__.assert_awaited_once()
    tx.__aexit__.assert_awaited_once()
    if action == "assign":
        repo.assign.assert_awaited_once_with(1, 8)
    else:
        expected = {"send": "da_gui", "start": "dang_thuc_hien", "cancel": "da_huy"}
        repo.transition.assert_awaited_once_with(1, expected[action])


async def test_not_found(workflow):
    service, repo, _, _ = workflow
    repo.get_order.return_value = None
    with pytest.raises(NotFoundException):
        await service.get_order(1, "r")
    with pytest.raises(NotFoundException):
        await service.get_order(2**40, "r")


@pytest.mark.parametrize("payload", [{"nhan_vien_id": 0}, {"nhan_vien_id": 2, "so_luong": 10}])
def test_assignment_schema(payload):
    with pytest.raises(ValidationError):
        NguoiThucHienInput(**payload)


def test_query_and_reason_validation():
    for payload in [
        dict(sort="id; DROP TABLE x"),
        dict(tu_ngay="2026-11-02", den_ngay="2026-11-01"),
        dict(page_size=101),
    ]:
        with pytest.raises(ValidationError):
            LenhListQuery(**payload)
    with pytest.raises(ValidationError):
        LyDoInput(ly_do="   ")


@pytest.fixture
def api(workflow):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_lenh_san_xuat_service] = lambda: workflow[0]
    return app


@pytest.mark.parametrize(
    "method,path,role,status",
    [
        ("GET", "/1", "quan_tri_vien", 403),
        ("GET", "/1", "nhan_vien", 200),
        ("PATCH", "/1", "nhan_vien", 403),
        ("POST", "/1/gui", "nhan_vien", 403),
        ("POST", "/1/bat_dau", "quan_ly", 403),
        ("POST", "/1/huy", "nhan_vien", 403),
        ("POST", "", "quan_ly", 405),
    ],
)
async def test_http_permissions(api, method, path, role, status):
    api.dependency_overrides[get_current_user_payload] = lambda: {"sub": "7", "roles": [role]}
    async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
        response = await client.request(
            method,
            "/api/v1/lenh_san_xuat" + path,
            json={"nhan_vien_id": 7} if method == "PATCH" else {},
        )
    assert response.status_code == status


async def test_http_validation(api):
    async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
        assert (await client.get("/api/v1/lenh_san_xuat/1")).status_code == 401
        api.dependency_overrides[get_current_user_payload] = lambda: MANAGER
        for url in ["?page=0", "?sort=unknown", "?unknown=1"]:
            assert (await client.get("/api/v1/lenh_san_xuat" + url)).status_code == 422
        assert (
            await client.patch("/api/v1/lenh_san_xuat/1", json={"nhan_vien_id": 7, "bom_id": 1})
        ).status_code == 422
        assert (
            await client.post("/api/v1/lenh_san_xuat/1/gui", json={"extra": 1})
        ).status_code == 422


@pytest.mark.parametrize(
    "method,path,actor,state,payload",
    [
        ("GET", "", MANAGER, "nhap", None),
        ("GET", "/1/vat_tu", WORKER, "da_gui", None),
        ("PATCH", "/1", MANAGER, "nhap", {"nhan_vien_id": 8}),
        ("POST", "/1/gui", MANAGER, "nhap", {}),
        ("POST", "/1/bat_dau", WORKER, "da_gui", {}),
        ("POST", "/1/huy", MANAGER, "nhap", {"ly_do": "Thay đổi kế hoạch"}),
    ],
)
async def test_http_success(api, order, method, path, actor, state, payload):
    order.trang_thai = state
    api.dependency_overrides[get_current_user_payload] = lambda: actor
    async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
        response = await client.request(method, "/api/v1/lenh_san_xuat" + path, json=payload)
    assert response.status_code == 200
    assert set(response.json()) == {"data", "meta"}


@pytest.mark.parametrize(
    "action,state,actor",
    [
        ("send", "da_gui", MANAGER),
        ("start", "nhap", WORKER),
        ("cancel", "hoan_thanh", MANAGER),
        ("cancel", "da_huy", MANAGER),
    ],
)
async def test_wrong_transition(workflow, order, action, state, actor):
    service, repo, audit, _ = workflow
    order.trang_thai = state
    with pytest.raises(ConflictException):
        if action == "cancel":
            await service.cancel(1, "Thay đổi", actor, "r")
        else:
            await getattr(service, action)(1, actor, "r")
    repo.transition.assert_not_awaited()
    audit.append.assert_not_awaited()


async def test_audit_failure_aborts_transaction(workflow):
    service, _, audit, tx = workflow
    audit.append.side_effect = RuntimeError("audit unavailable")
    with pytest.raises(RuntimeError):
        await service.assign(1, 8, MANAGER, "r")
    assert tx.__aexit__.call_args.args[0] is RuntimeError
