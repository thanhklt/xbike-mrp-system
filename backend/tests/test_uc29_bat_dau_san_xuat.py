"""UC-29: transactional service/ASGI ports and v4 SQL metadata, without a database."""

import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenException, UnauthorizedException
from app.core.exceptions import register_exception_handlers
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_current_user_payload, get_yeu_cau_san_xuat_service
from app.modules.audit.ports import AuditWriter
from app.modules.bom.repository import SqlAlchemyBomRepository
from app.modules.mat_hang.repository import SqlAlchemyMatHangRepository
from app.modules.san_xuat.models import ChungTuHoanThanhSx
from app.modules.san_xuat.ports import ProductionIssues, YeuCauSanXuatRepository
from app.modules.san_xuat.router import yeu_cau_sx_router
from app.modules.san_xuat.service.yeu_cau_san_xuat import (
    YeuCauSanXuatService,
    generate_yeu_cau_etag,
)
from tests.test_uc26_kiem_tra_giu_hang import NOW, request_record

URL = "/api/v1/yeu_cau_san_xuat/1/bat_dau"
EMPLOYEE = {"sub": "20", "roles": ["nhan_vien"]}


@pytest.fixture
async def api():
    data = {
        "request": request_record(trang_thai="dang_thuc_hien", so_luong_can_san_xuat=7,
                                  so_luong_dung_thanh_pham=3, kiem_tra_lan_dau_at=NOW),
        "issues": [{"id": 1, "loai_phieu": "xuat_linh_kien", "trang_thai": "da_duyet"}],
        "stock": {2: 93, 5: 10}, "held": {2: 0, 5: 3},
        "holds": [{"mat_hang_id": 2, "trang_thai": "da_xuat", "so_luong": 7}],
        "ledger": [{"mat_hang_id": 2, "so_luong_bien_dong": -7}], "history": [],
    }
    pending = None
    repo, audit = AsyncMock(spec=YeuCauSanXuatRepository), AsyncMock(spec=AuditWriter)
    issues, session = AsyncMock(spec=ProductionIssues), AsyncMock(spec=AsyncSession)
    items, employees = Mock(), Mock()

    def current():
        return pending if pending is not None else data

    async def lock(id_):
        nonlocal pending
        assert pending is None
        pending = deepcopy(data)
        return current()["request"] if id_ == 1 else None

    async def update(id_, changes):
        assert id_ == 1 and set(changes) == {"started_at"}
        before = current()["request"]
        current()["request"] = before.model_copy(update={
            **changes, "phien_ban": before.phien_ban + 1,
            "updated_at": datetime.now(timezone.utc),
        })
        return current()["request"]

    async def append(entry):
        current()["history"].append(entry.model_copy(deep=True))

    async def commit():
        nonlocal pending
        data.clear()
        data.update(pending)
        pending = None

    async def rollback():
        nonlocal pending
        pending = None

    repo.get_for_update.side_effect = lock
    repo.get_by_id.side_effect = lambda id_: data["request"] if id_ == 1 else None
    repo.update.side_effect = update
    issues.phieu_cua_yeu_cau.side_effect = lambda id_: current()["issues"]
    audit.append.side_effect = append
    session.commit.side_effect, session.rollback.side_effect = commit, rollback
    service = YeuCauSanXuatService(repo, audit, SqlAlchemyTransaction(session), items, employees, issues)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(yeu_cau_sx_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "nhan_vien")
        if role == "anonymous":
            raise UnauthorizedException()
        if role == "locked":
            raise ForbiddenException()
        return {"sub": request.headers.get("x-user", "20"), "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_yeu_cau_san_xuat_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False),
                           base_url="http://test") as client:
        yield SimpleNamespace(data=data, repo=repo, audit=audit, issues=issues, session=session,
                              service=service, items=items, employees=employees, client=client)


async def start(api, *, headers=None, body=None, url=URL):
    return await api.client.post(url, json={} if body is None else body, headers={
        "If-Match": generate_yeu_cau_etag(api.data["request"]), **(headers or {}),
    })


def unchanged(api, before):
    assert api.data == before
    api.repo.update.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.session.commit.assert_not_awaited()


# UC-29 AC-1: Không có/nháp/chờ duyệt/từ chối và phiếu sai loại đều bị từ chối nguyên tử
@pytest.mark.parametrize("kind,state", [
    (None, None), ("xuat_linh_kien", "nhap"), ("xuat_linh_kien", "cho_duyet"),
    ("xuat_linh_kien", "tu_choi"), ("xuat_thanh_pham", "da_duyet"),
])
async def test_unapproved_component_issue_rejected(api, kind, state):
    api.data["issues"] = [] if kind is None else [{"loai_phieu": kind, "trang_thai": state}]
    before = deepcopy(api.data)
    response = await start(api)
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "trang_thai_khong_hop_le", "message": "Phiếu xuất linh kiện chưa được duyệt",
        "details": [],
    }
    unchanged(api, before)


# UC-29 AC-2: Ghi thời điểm, tăng phiên bản đúng một lần, không đọc/ghi tồn hay giữ hàng
@pytest.mark.parametrize("kind", ["xuat_giao", "nhap_kho"])
async def test_start_records_time_without_touching_stock(api, kind):
    api.data["request"] = api.data["request"].model_copy(update={"loai_yeu_cau": kind})
    before = deepcopy(api.data)
    lower = datetime.now(timezone.utc)
    response = await start(api)
    assert response.status_code == 200, response.text
    after = api.data["request"]
    assert lower <= after.started_at <= datetime.now(timezone.utc)
    assert after.trang_thai == "dang_thuc_hien" and after.phien_ban == 2
    assert response.json()["data"] == after.model_dump(mode="json")
    assert response.headers["etag"] == generate_yeu_cau_etag(after)
    assert response.headers["etag"] != generate_yeu_cau_etag(before["request"])
    assert set(response.json()) == {"data", "meta"}
    assert response.json()["meta"]["request_id"]
    for key in ("stock", "held", "holds", "ledger", "issues"):
        assert api.data[key] == before[key]
    assert api.repo.mock_calls == [call.get_for_update(1), call.update(1, {"started_at": after.started_at})]
    assert api.issues.mock_calls == [call.phieu_cua_yeu_cau(1)]
    assert api.items.mock_calls == api.employees.mock_calls == []
    api.session.commit.assert_awaited_once()


# UC-29 D3: Một lịch sử đúng người, trạng thái và toàn bộ bản ghi trước/sau
async def test_start_audits_full_snapshots(api):
    before = api.data["request"].model_dump(mode="json")
    response = await start(api)
    assert response.status_code == 200
    assert len(api.data["history"]) == 1
    entry = api.data["history"][0]
    assert (entry.nhan_vien_id, entry.loai_doi_tuong, entry.doi_tuong_id, entry.thao_tac) == (
        20, "yeu_cau_san_xuat", 1, "bat_dau",
    )
    assert entry.trang_thai_truoc == entry.trang_thai_sau == "dang_thuc_hien"
    assert entry.du_lieu_truoc == before
    assert entry.du_lieu_sau == response.json()["data"]
    assert entry.du_lieu_truoc["started_at"] is None
    assert entry.du_lieu_sau["started_at"] is not None
    api.audit.append.assert_awaited_once()


# UC-29 AC-3: ETag mới trả nguyên kết quả, không tăng phiên bản hoặc ghi lịch sử lần hai
async def test_retry_preserves_time_version_and_history(api):
    first = await start(api)
    assert first.status_code == 200
    before = deepcopy(api.data)
    api.repo.update.reset_mock()
    api.audit.append.reset_mock()
    api.issues.phieu_cua_yeu_cau.reset_mock()
    second = await start(api, headers={"If-Match": first.headers["etag"]})
    assert second.status_code == 200
    assert second.json()["data"] == first.json()["data"]
    assert second.headers["etag"] == first.headers["etag"]
    assert api.data == before and len(api.data["history"]) == 1
    api.repo.update.assert_not_awaited()
    api.audit.append.assert_not_awaited()
    api.issues.phieu_cua_yeu_cau.assert_not_awaited()


# UC-29 D1: Chỉ trạng thái Đang thực hiện với lượng sản xuất dương
@pytest.mark.parametrize("state,quantity", [
    ("da_gui", 7), ("cho_bo_sung_linh_kien", 7), ("hoan_thanh", 7), ("da_huy", 7),
    ("dang_thuc_hien", 0), ("dang_thuc_hien", None), ("dang_thuc_hien", -1),
])
async def test_invalid_state_or_quantity_conflicts(api, state, quantity):
    api.data["request"] = api.data["request"].model_copy(update={
        "trang_thai": state, "so_luong_can_san_xuat": quantity,
    })
    before = deepcopy(api.data)
    assert (await start(api)).status_code == 409
    unchanged(api, before)
    api.issues.phieu_cua_yeu_cau.assert_not_awaited()


# UC-29 D1: QLK/NV khác 403, Nháp với NV 404, phiên không hợp lệ bị chặn
@pytest.mark.parametrize("headers,state,status", [
    ({"x-role": "quan_ly"}, "dang_thuc_hien", 403),
    ({"x-role": "quan_tri_vien"}, "dang_thuc_hien", 403),
    ({"x-user": "21"}, "dang_thuc_hien", 403), ({}, "nhap", 404),
    ({"x-role": "anonymous"}, "dang_thuc_hien", 401),
    ({"x-role": "locked"}, "dang_thuc_hien", 403),
])
async def test_start_access_control(api, headers, state, status):
    api.data["request"] = api.data["request"].model_copy(update={"trang_thai": state})
    before = deepcopy(api.data)
    assert (await start(api, headers=headers)).status_code == status
    unchanged(api, before)


# UC-29 D1: Mất yêu cầu và ID vượt INT32 trả 404
@pytest.mark.parametrize("id_", [2, 2**31])
async def test_missing_request_returns_404(api, id_):
    before = deepcopy(api.data)
    assert (await start(api, url=URL.replace("/1/", f"/{id_}/"))).status_code == 404
    unchanged(api, before)


# UC-29 D4: If-Match vẫn bắt buộc và phải hiện hành cả khi đã bắt đầu
@pytest.mark.parametrize("started", [False, True])
@pytest.mark.parametrize("etag,status", [(None, 428), ("", 428), ('"old"', 412), ("*", 412)])
async def test_start_requires_current_etag(api, started, etag, status):
    if started:
        api.data["request"] = api.data["request"].model_copy(update={"started_at": NOW})
    before = deepcopy(api.data)
    response = await api.client.post(URL, json={}, headers={} if etag is None else {"If-Match": etag})
    assert response.status_code == status
    assert response.json()["error"]["code"] == (
        "thieu_if_match" if status == 428 else "du_lieu_da_thay_doi"
    )
    unchanged(api, before)


# UC-29 D1: Body phải rỗng và không nhận query tùy ý
@pytest.mark.parametrize("body,suffix", [({"started_at": "2026-11-16T08:00:00Z"}, ""), ({}, "?force=true")])
async def test_start_rejects_extra_input(api, body, suffix):
    before = deepcopy(api.data)
    response = await start(api, body=body, url=URL + suffix)
    assert response.status_code == 422
    unchanged(api, before)


# UC-29 D3: Audit/commit lỗi rollback cả thời điểm và lịch sử, không báo thành công
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_start_rolls_back_on_failure(api, failure):
    before = deepcopy(api.data)
    if failure == "audit":
        api.audit.append.side_effect = RuntimeError("audit failed")
    else:
        api.session.commit.side_effect = RuntimeError("commit failed")
    response = await start(api)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "loi_noi_bo"
    assert api.data == before
    api.repo.update.assert_awaited_once()
    api.session.rollback.assert_awaited_once()


# UC-29 D1: Service cũng chặn QLK và NV ngoài phạm vi khi gọi trực tiếp
@pytest.mark.parametrize("actor", [{"sub": "10", "roles": ["quan_ly"]}, {"sub": "21", "roles": ["nhan_vien"]}])
async def test_service_checks_scope(api, actor):
    before = deepcopy(api.data)
    with pytest.raises(ForbiddenException):
        await api.service.bat_dau(1, actor, generate_yeu_cau_etag(api.data["request"]), "test")
    unchanged(api, before)


# UC-29 D6: Router lệnh và chứng từ v3 đã gỡ khỏi ứng dụng thật, mọi đường dẫn cũ trả 404
@pytest.mark.parametrize("resource", ["lenh_san_xuat", "chung_tu_hoan_thanh_sx"])
# UC-33 D1: Chứng từ có GET danh sách và POST lập cùng URL; các route v3 vẫn bị gỡ
async def test_removed_v3_routes_return_404(resource):
    from app.main import app

    if resource == "lenh_san_xuat":
        assert not any(path.startswith(f"/api/v1/{resource}") for path in app.openapi()["paths"])
    else:
        assert {path for path in app.openapi()["paths"] if path.startswith(f"/api/v1/{resource}")} == {
            f"/api/v1/{resource}", f"/api/v1/{resource}/{{id}}", f"/api/v1/{resource}/{{id}}/gui",
            f"/api/v1/{resource}/{{id}}/duyet",  # UC-31
            f"/api/v1/{resource}/{{id}}/tu_choi",  # UC-32
        }
        assert set(app.openapi()["paths"][f"/api/v1/{resource}"]) == {"post", "get"}
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        for path in ("", "/1", "/1/bat_dau", "/1/gui", "/1/duyet", "/1/tu_choi", "/1/huy", "/1/ve_nhap", "/1/vat_tu"):
            if resource == "chung_tu_hoan_thanh_sx" and path in {"", "/1", "/1/gui", "/1/duyet", "/1/tu_choi"}:
                continue  # UC-30 restores these resources; their methods are tested in UC-30.
            for method in ("GET", "POST", "PATCH", "DELETE"):
                response = await client.request(method, f"/api/v1/{resource}{path}")
                assert response.status_code == 404, (method, path, response.text)


# UC-29 D6: ORM chứng từ khớp toàn bộ cột, kiểu, null/default, khóa, check và index bootstrap v4
def test_completion_orm_matches_v4_bootstrap():
    sql = (Path(__file__).resolve().parents[2] / "infra/postgres/init.sql").read_text(encoding="utf-8")
    block = sql.split('CREATE TABLE "ChungTuHoanThanhSx" (', 1)[1].split("\n);", 1)[0]
    table = ChungTuHoanThanhSx.__table__
    columns = re.findall(r'^  "(\w+)" (.*?)(?:,)?$', block, re.M)
    assert set(table.c.keys()) == {name for name, _ in columns}
    for name, definition in columns:
        column = table.c[name]
        assert column.nullable == ("NOT NULL" not in definition and "PRIMARY KEY" not in definition), name
        expected_type = definition.split()[0].lower()
        assert str(column.type.compile(dialect=postgresql.dialect())).lower() == {
            "int": "integer", "varchar": "varchar", "timestamptz": "timestamp with time zone", "text": "text",
        }[expected_type], name
        if "DEFAULT" in definition and name != "id":
            assert str(column.server_default.arg).strip("()") == definition.split("DEFAULT ")[1].strip("(),"), name
        elif name != "id":
            assert column.server_default is None, name
        if "UNIQUE" in definition:
            assert any(isinstance(c, UniqueConstraint) and list(c.columns.keys()) == [name] for c in table.constraints), name
    assert table.c.id.primary_key and table.c.id.identity.always is False
    checks = dict(re.findall(r'CONSTRAINT "(ck_htsx_\w+)" CHECK \((.*)\)', block))
    actual = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
    assert actual == checks
    assert {fk.parent.name: fk.target_fullname for fk in table.foreign_keys} == {
        "yeu_cau_san_xuat_id": "YeuCauSanXuat.id", "nhan_vien_id": "NhanVien.id", "nguoi_xu_ly_id": "NhanVien.id",
    }
    assert all(fk.deferrable and fk.initially == "IMMEDIATE" for fk in table.foreign_keys)
    assert {index.name: list(index.columns.keys()) for index in table.indexes} == {
        "ix_htsx_trang_thai": ["trang_thai", "finish_time"], "ix_htsx_nhan_vien": ["nhan_vien_id"],
    }
    assert not {"LenhSanXuat", "ChiTietLenhSanXuat"}.intersection(table.metadata.tables)


# UC-29 D6: BOM đã dùng được tính bằng EXISTS yêu cầu tham chiếu BOM, không phụ thuộc trạng thái
async def test_bom_usage_sql_uses_request_bom_id():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock()
    session.execute.return_value.one_or_none.return_value = None
    assert await SqlAlchemyBomRepository(session).get_by_id(7) is None
    query = session.execute.call_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert 'EXISTS (SELECT * \nFROM "YeuCauSanXuat" \nWHERE "YeuCauSanXuat".bom_id = "Bom".id)' in sql
    assert '"Bom".id = 7' in sql
    assert "LenhSanXuat" not in sql and '"YeuCauSanXuat".trang_thai' not in sql


# UC-29 D6: Kiểm mặt hàng giữ mọi nhánh khác, bỏ đúng hai bảng lệnh đã gỡ
async def test_item_reference_sql_excludes_order_tables():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock()
    session.execute.return_value.one.return_value = SimpleNamespace(has_bom=True, has_docs=True, has_stock=False)
    result = await SqlAlchemyMatHangRepository(session).get_references(5)
    sql = str(session.execute.call_args.args[0])
    assert session.execute.call_args.args[1] == {"id": 5}
    assert "LenhSanXuat" not in sql and "ChiTietLenhSanXuat" not in sql
    assert set(re.findall(r'FROM "(\w+)"', sql)) == {
        # v4 init.sql: điều chỉnh kho v3 đã gỡ; giữ hàng và nhu cầu linh kiện là tham chiếu mới.
        # PR-10 D2: Bom của chính thành phẩm không tính là tham chiếu công thức.
        "ChiTietBom", "ChiTietPhieuNhap", "ChiTietPhieuXuat",
        "GiaoDichKho", "YeuCauSanXuat", "GiuHang", "NhuCauLinhKien", "MatHang",
    }
    assert 'WHERE id=:id AND so_luong_ton > 0' in sql
    assert (result.has_bom, result.has_docs, result.has_stock) == (True, True, False)
