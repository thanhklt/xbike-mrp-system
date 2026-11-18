"""UC-42: service và HTTP/JWT thật trên sổ giả, không dùng DB ứng dụng."""

from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, get_password_hash, password_version
from app.dependencies import get_auth_service, get_bao_cao_service
from app.main import app as application
from app.modules.audit.service import AuditService
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.schemas import EmployeeCredentials
from app.modules.nhan_vien.service import NhanVienService
from app.modules.reporting.repository import SqlAlchemyBaoCaoRepository
from app.modules.reporting.router import router
from app.modules.reporting.schemas import BienDongKhoQuery, BienDongKhoRow
from app.modules.reporting.service import BaoCaoService, bien_ngay
from app.shared.records import RecordPage

URL = "/api/v1/bao_cao/bien_dong_kho"
AT = datetime(2026, 1, 31, 16, 30, tzinfo=timezone.utc)
KINDS = ("nhap_linh_kien", "xuat_linh_kien", "nhap_san_pham_san_xuat", "xuat_thanh_pham")


def movement(id_, kind="nhap_linh_kien", item=1, actor=1, at=AT):
    source = ("phieu_nhap", "PN") if kind == KINDS[0] else (
        ("chung_tu_hoan_thanh_sx", "HTSX") if kind == KINDS[2] else ("phieu_xuat", "PX")
    )
    return BienDongKhoRow(
        id_, at, kind, 10 if kind.startswith("nhap") else -3, 20 + id_,
        item, f"MH-{item:06d}", "Khung xe" if item == 1 else "Xe đạp", "cái",
        source[0], 100 + id_, f"{source[1]}-202601-{100 + id_:06d}",
        actor, f"NV-{actor:06d}", "Người ghi nhận" if actor == 1 else None,
    )


class MemoryLedger:
    def __init__(self):
        self.movements = [movement(1), movement(2, KINDS[1]),
                          movement(3, KINDS[2], item=2), movement(4, KINDS[3], item=2)]
        self.documents = []
        self.calls = []

    async def bien_dong_kho(self, tu, den, item, kind, actor, offset, limit):
        self.calls.append((tu, den, item, kind, actor, offset, limit))
        rows = sorted((r for r in self.movements
                       if (tu is None or r.posted_at >= tu)
                       and (den is None or r.posted_at < den)
                       and (item is None or r.mat_hang_id == item)
                       and (kind is None or r.loai_giao_dich == kind)
                       and (actor is None or r.nhan_vien_id == actor)),
                      key=lambda r: (r.posted_at, r.id), reverse=True)
        return RecordPage(rows[offset:offset + limit], len(rows))


@pytest.fixture
def ledger():
    return MemoryLedger()


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash("UC42-password")


@pytest.fixture
async def api(ledger, password_hash):
    credentials = {
        id_: EmployeeCredentials(
            id=id_, vai_tro_id=id_, ma_nhan_vien=f"NV-{id_:06d}",
            ten_dang_nhap=f"report-{id_}", ho_ten=None, ma_vai_tro=role,
            trang_thai="hoat_dong", roles=[role], password_hash=password_hash,
            ngay_sinh=None, so_dien_thoai=None, email=None, ngay_vao_lam=None,
            he_so_luong=None,
        ) for id_, role in enumerate(("quan_ly", "nhan_vien", "quan_tri_vien"), 1)
    }
    employees, audit, transaction = AsyncMock(), AsyncMock(), AsyncMock()
    employees.get_credentials_by_id.side_effect = credentials.get
    auth = AuthService(NhanVienService(employees, AuditService(audit), transaction))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_auth_service] = lambda: auth
    app.dependency_overrides[get_bao_cao_service] = lambda: BaoCaoService(ledger)
    headers = {
        id_: {"Authorization": "Bearer " + create_access_token(
            id_, user.roles, credential_version=password_version(user.password_hash),
            session_version=user.phien_ban_dang_nhap,
        )} for id_, user in credentials.items()
    }
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test",
    ) as client:
        yield SimpleNamespace(client=client, headers=headers, ledger=ledger)
    audit.append.assert_not_called()
    transaction.__aenter__.assert_not_called()


async def read(api, params=None):
    response = await api.client.get(URL, params=params or {}, headers=api.headers[1])
    assert response.status_code == 200, response.text
    assert "etag" not in response.headers
    body = response.json()
    assert set(body) == {"success", "data", "pagination", "message"}
    assert body["success"] is True
    assert body["message"]
    return body


# UC-42 AC-1: Xem biến động theo mặt hàng kèm chứng từ đầu phiếu và số dư
async def test_item_history_contains_source_headers_and_signed_snapshots(api):
    api.ledger.movements[0] = replace(api.ledger.movements[0], posted_at=AT - timedelta(days=1))
    body = await read(api, {"mat_hang_id": 1})
    assert [r["id"] for r in body["data"]] == [2, 1]
    for row, expected in zip(body["data"], reversed(api.ledger.movements[:2]), strict=True):
        assert row == {
            "id": expected.id, "posted_at": expected.posted_at.isoformat().replace("+00:00", "Z"),
            "loai_giao_dich": expected.loai_giao_dich,
            "so_luong_bien_dong": expected.so_luong_bien_dong,
            "so_luong_ton_sau": expected.so_luong_ton_sau,
            "mat_hang": {"id": 1, "ma_mat_hang": "MH-000001", "ten_mat_hang": "Khung xe", "don_vi_tinh": "cái"},
            "chung_tu": {"loai": expected.chung_tu_loai, "id": expected.chung_tu_id, "ma": expected.chung_tu_ma},
            "nhan_vien": {"id": 1, "ma_nhan_vien": "NV-000001", "ho_ten": "Người ghi nhận"},
        }
    assert body["pagination"]["total_items"] == 2


# UC-42 AC-2: Không gồm phiếu xuất bị từ chối chưa có dòng sổ
async def test_rejected_unposted_issue_never_appears(api):
    before = await read(api)
    api.ledger.documents.append({"id": 999, "ma": "PX-202601-000999", "trang_thai": "tu_choi"})
    after = await read(api)
    assert after == before
    assert len(after["data"]) == 4
    assert all(r["chung_tu"]["ma"] != "PX-202601-000999" for r in after["data"])


# UC-42 AC-3: Lọc nhập kho chỉ hiện biến động từ phiếu nhập
async def test_receipt_type_filters_all_four_kinds(api):
    assert {r["loai_giao_dich"] for r in (await read(api))["data"]} == set(KINDS)
    body = await read(api, {"loai_giao_dich": "nhap_linh_kien"})
    assert [r["id"] for r in body["data"]] == [1]
    assert {r["chung_tu"]["loai"] for r in body["data"]} == {"phieu_nhap"}
    assert api.ledger.calls[-1] == (None, None, None, "nhap_linh_kien", None, 0, 20)


# UC-42 R1: Lọc AND theo mặt hàng, loại, người ghi nhận và ngày
async def test_combined_filters_use_ledger_actor(api):
    api.ledger.movements.extend([
        movement(5, actor=2), movement(6, at=AT + timedelta(days=1)),
        movement(7, item=2), movement(8, KINDS[1]),
    ])
    body = await read(api, {"mat_hang_id": 1, "loai_giao_dich": KINDS[0], "nhan_vien_id": 1,
                            "tu_ngay": "2026-01-31", "den_ngay": "2026-01-31"})
    assert [r["id"] for r in body["data"]] == [1]
    assert api.ledger.calls[-1] == (*bien_ngay(date(2026, 1, 31), date(2026, 1, 31)), 1, KINDS[0], 1, 0, 20)
    actor = await read(api, {"nhan_vien_id": 2})
    assert [r["id"] for r in actor["data"]] == [5]
    assert actor["data"][0]["nhan_vien"] == {"id": 2, "ma_nhan_vien": "NV-000002", "ho_ten": None}


# UC-42 R3: Ngày Việt Nam bao gồm 23:30, loại 00:10 ngày kế tiếp
async def test_vietnam_day_includes_late_evening_and_excludes_next_day(api):
    start = datetime(2026, 1, 30, 17, tzinfo=timezone.utc)
    end = datetime(2026, 1, 31, 17, tzinfo=timezone.utc)
    api.ledger.movements = [movement(1, at=AT), movement(2, at=end + timedelta(minutes=10)),
                            movement(3, at=start), movement(4, at=end),
                            movement(5, at=start - timedelta(microseconds=1))]
    body = await read(api, {"tu_ngay": "2026-01-31", "den_ngay": "2026-01-31"})
    assert [r["id"] for r in body["data"]] == [1, 3]
    assert api.ledger.calls[-1][:2] == (start, end)


# UC-42 R3: Cho phép bỏ một hoặc cả hai biên ngày
@pytest.mark.parametrize("tu,den,expected", [
    (None, None, (None, None)),
    (date(2026, 1, 31), None, (datetime(2026, 1, 30, 17, tzinfo=timezone.utc), None)),
    (None, date(2026, 1, 31), (None, datetime(2026, 1, 31, 17, tzinfo=timezone.utc))),
])
async def test_open_date_boundaries_reach_repository(ledger, tu, den, expected):
    assert bien_ngay(tu, den) == expected
    await BaoCaoService(ledger).bien_dong_kho(BienDongKhoQuery(tu_ngay=tu, den_ngay=den))
    assert ledger.calls[-1][:2] == expected


# UC-42 R3: Chặn ngày cực trị gây tràn và khoảng đảo
@pytest.mark.parametrize("tu,den", [(date.min, None), (None, date.max), (date(2026, 2, 1), date(2026, 1, 1))])
def test_pure_date_boundary_rejects_invalid_ranges(tu, den):
    with pytest.raises(ValidationError):
        bien_ngay(tu, den)


# UC-42 A1: Không có biến động thỏa tiêu chí trả danh sách trống
@pytest.mark.parametrize("params", [{"mat_hang_id": 999}, {"nhan_vien_id": 999}, {"mat_hang_id": 1, "loai_giao_dich": KINDS[2]}])
async def test_unmatched_filters_return_empty_page(api, params):
    body = await read(api, params)
    assert body["data"] == []
    assert body["pagination"] == {"page": 1, "page_size": 20, "total_items": 0, "total_pages": 0, "has_next": False, "has_prev": False}


# UC-42 A2: Nhân viên, quản trị viên và người chưa đăng nhập bị chặn trước repository
@pytest.mark.parametrize("actor,status", [(2, 403), (3, 403), (None, 401)])
async def test_forbidden_actors_never_read_ledger(api, actor, status):
    response = await api.client.get(URL, headers=api.headers.get(actor, {}))
    assert response.status_code == status
    assert api.ledger.calls == []


# UC-42 A2: Gỡ GET lịch sử cũ khỏi ứng dụng; router inventory v3 không còn endpoint nào
async def test_legacy_get_removed_from_real_application():
    paths = application.openapi()["paths"]
    assert set(paths[URL]) == {"get"}
    assert not [path for path in paths if path.startswith("/api/v1/inventory")]
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/v1/inventory/movements")
    assert response.status_code in (404, 405)


# UC-42 R1: Phân trang cố định mới nhất trước, trùng thời điểm lấy id giảm dần
async def test_pagination_and_tied_timestamp_order(api):
    first = await read(api, {"page_size": 2})
    second = await read(api, {"page": 2, "page_size": 2})
    assert [r["id"] for r in first["data"]] == [4, 3]
    assert [r["id"] for r in second["data"]] == [2, 1]
    assert first["pagination"] == {"page": 1, "page_size": 2, "total_items": 4, "total_pages": 2, "has_next": True, "has_prev": False}
    assert second["pagination"] == {"page": 2, "page_size": 2, "total_items": 4, "total_pages": 2, "has_next": False, "has_prev": True}
    assert api.ledger.calls[-1][-2:] == (2, 2)
    beyond = await read(api, {"page": 3, "page_size": 2})
    assert beyond["data"] == []
    assert beyond["pagination"]["total_items"] == 4


# UC-42 R1: Query không hợp lệ trả 422 trước khi đọc sổ
@pytest.mark.parametrize("params", [
    {"tu_ngay": "2026-02-01", "den_ngay": "2026-01-31"},
    {"tu_ngay": "0001-01-01"}, {"den_ngay": "9999-12-31"},
    {"tu_ngay": "31/01/2026"}, {"den_ngay": "2026-02-30"},
    {"tu_ngay": "20260131"}, {"tu_ngay": "2026-01-31T00:00:00Z"},
    {"den_ngay": "0"}, {"loai_giao_dich": "nhap_vat_tu"},
    {"page_size": 101}, {"page_size": 0}, {"page": 0},
    {"extra": "bad"}, {"sort_by": "id"}, {"sort": "-id"}, {"q": "khung"},
    {"mat_hang_id": 0}, {"mat_hang_id": -1}, {"nhan_vien_id": 0},
])
async def test_invalid_queries_return_422_without_repository(api, params):
    response = await api.client.get(URL, params=params, headers=api.headers[1])
    assert response.status_code == 422, response.text
    assert api.ledger.calls == []


# UC-42 AC-2: SQL chỉ SELECT sổ, JOIN hiển thị, COUNT cùng lọc và không phụ thuộc trạng thái
@pytest.mark.parametrize("filtered", [False, True])
async def test_sql_is_read_only_with_matching_count_filters(filtered):
    record = movement(1)
    session = AsyncMock()
    page, count = Mock(), Mock()
    page.mappings.return_value = [asdict(record)]
    count.scalar_one.return_value = 7
    session.execute.side_effect = [page, count]
    tu, den = bien_ngay(date(2026, 1, 31), date(2026, 1, 31)) if filtered else (None, None)
    item, kind, actor = (1, KINDS[0], 2) if filtered else (None, None, None)
    result = await SqlAlchemyBaoCaoRepository(session).bien_dong_kho(tu, den, item, kind, actor, 2, 2)
    assert result == RecordPage([record], 7)
    (statement, params), (count_statement, count_params) = [c.args for c in session.execute.call_args_list]
    sql, count_sql = str(statement), str(count_statement)
    assert sql.split("WHERE", 1)[1].split("ORDER BY", 1)[0].strip() == count_sql.split("WHERE", 1)[1].strip()
    assert 'SELECT COUNT(*) FROM "GiaoDichKho" g' in count_sql
    assert "ORDER BY g.posted_at DESC, g.id DESC LIMIT :limit OFFSET :offset" in sql
    for table in ("MatHang", "NhanVien", "ChiTietPhieuNhap", "PhieuNhap", "ChiTietPhieuXuat", "PhieuXuat", "ChungTuHoanThanhSx"):
        assert f'LEFT JOIN "{table}"' in sql
    assert "COALESCE(pn.id, px.id, ht.id) AS chung_tu_id" in sql
    assert "g.nhan_vien_id = :nhan_vien_id" in sql
    for query in (sql, count_sql):
        assert not any(word in query for word in ("trang_thai", "is_active", "INSERT", "UPDATE", "DELETE"))
        assert "g.posted_at >= :tu_utc" in query
        assert "g.posted_at < :den_utc" in query
    assert count_params == {"tu_utc": tu, "den_utc": den, "mat_hang_id": item, "loai_giao_dich": kind, "nhan_vien_id": actor}
    assert params == {**count_params, "offset": 2, "limit": 2}
    assert session.mock_calls == [call.execute(statement, params), call.execute(count_statement, count_params)]
    session.commit.assert_not_called()
    session.flush.assert_not_called()
    session.add.assert_not_called()
