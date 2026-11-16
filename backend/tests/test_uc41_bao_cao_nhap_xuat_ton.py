"""UC-41: biên kỳ, service và HTTP/JWT thật trên sổ kho giả, không chạm DB ứng dụng."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

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
from app.modules.reporting.schemas import NhapXuatTonQuery, NhapXuatTonRow
from app.modules.reporting.service import LOCAL_TZ, BaoCaoService, bien_ky

URL = "/api/v1/bao_cao/nhap_xuat_ton"
JANUARY = {"ky": "thang", "nam": 2026, "thang": 1}


def item(id_, kind="linh_kien", active=True):
    return dict(
        id=id_, ma_mat_hang=f"MH-{id_:06d}", ten_mat_hang=f"Mặt hàng {id_}",
        loai_mat_hang=kind, don_vi_tinh="cái", is_active=active, so_luong_ton=0,
    )


class MemoryLedger:
    def __init__(self):
        self.items = [item(2, "thanh_pham"), item(1), item(3, "thanh_pham", False)]
        self.movements = []
        self.documents = []
        self.calls = []

    def post(self, id_, delta, at, balance):
        self.movements.append(dict(
            id=len(self.movements) + 1, mat_hang_id=id_, so_luong_bien_dong=delta,
            so_luong_ton_sau=balance, posted_at=at,
        ))
        next(i for i in self.items if i["id"] == id_)["so_luong_ton"] = balance

    async def nhap_xuat_ton(self, tu_utc, den_utc, mat_hang_id, loai_mat_hang):
        self.calls.append((tu_utc, den_utc, mat_hang_id, loai_mat_hang))
        rows = []
        for i in sorted(self.items, key=lambda i: (i["loai_mat_hang"], i["ma_mat_hang"])):
            if mat_hang_id is not None and i["id"] != mat_hang_id:
                continue
            if loai_mat_hang is not None and i["loai_mat_hang"] != loai_mat_hang:
                continue
            ledger = sorted(
                (m for m in self.movements if m["mat_hang_id"] == i["id"]),
                key=lambda m: (m["posted_at"], m["id"]),
            )
            before = [m for m in ledger if m["posted_at"] < tu_utc]
            until = [m for m in ledger if m["posted_at"] < den_utc]
            during = [m["so_luong_bien_dong"] for m in ledger
                      if tu_utc <= m["posted_at"] < den_utc]
            rows.append(NhapXuatTonRow(
                mat_hang_id=i["id"],
                **{k: i[k] for k in ("ma_mat_hang", "ten_mat_hang", "loai_mat_hang", "don_vi_tinh")},
                ton_dau_ky=before[-1]["so_luong_ton_sau"] if before else 0,
                nhap_trong_ky=sum(n for n in during if n > 0),
                xuat_trong_ky=sum(-n for n in during if n < 0),
                ton_cuoi_ky=until[-1]["so_luong_ton_sau"] if until else 0,
            ))
        return rows


@pytest.fixture
def ledger():
    return MemoryLedger()


@pytest.fixture(scope="module")
def password_hash():
    return get_password_hash("UC41-password")


@pytest.fixture
async def api(ledger, password_hash):
    credentials = {
        id_: EmployeeCredentials(
            id=id_, vai_tro_id=id_, ma_nhan_vien=f"NV-{id_:06d}",
            ten_dang_nhap=f"report-{id_}", ho_ten=None, ma_vai_tro=role,
            trang_thai="hoat_dong", roles=[role], password_hash=password_hash,
            ngay_sinh=None, so_dien_thoai=None, email=None, ngay_vao_lam=None,
            he_so_luong=None,
        )
        for id_, role in enumerate(("quan_ly", "nhan_vien", "quan_tri_vien"), 1)
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
        yield SimpleNamespace(client=client, headers=headers, ledger=ledger, app=app)
    audit.append.assert_not_called()
    transaction.__aenter__.assert_not_called()


async def read(api, params=None):
    response = await api.client.get(URL, params=params or JANUARY, headers=api.headers[1])
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"success", "data", "message"}
    assert body["success"] is True
    assert body["message"]
    return body["data"]


# UC-41 AC-1: Tồn cuối kỳ khớp tồn thực tế
async def test_current_period_matches_stock_and_balance_equation(api):
    now = datetime.now(LOCAL_TZ)
    tu, _ = bien_ky("thang", now.year, now.month)
    for id_, start in ((1, 20), (2, 10)):
        api.ledger.post(id_, start, tu - timedelta(seconds=1), start)
        api.ledger.post(id_, 8, tu, start + 8)
        api.ledger.post(id_, -3, tu, start + 5)
        api.ledger.post(id_, 2, tu, start + 7)
        api.ledger.post(id_, -1, tu, start + 6)
    result = await read(api, {"ky": "thang", "nam": now.year, "thang": now.month})
    assert [r["mat_hang_id"] for r in result["mat_hang"]] == [1, 2, 3]
    stocks = {i["id"]: i["so_luong_ton"] for i in api.ledger.items}
    for r in result["mat_hang"]:
        assert r["ton_cuoi_ky"] == stocks[r["mat_hang_id"]]
        assert r["ton_cuoi_ky"] == r["ton_dau_ky"] + r["nhap_trong_ky"] - r["xuat_trong_ky"]
    assert result["mat_hang"][0]["nhap_trong_ky"] == 10
    assert result["mat_hang"][0]["xuat_trong_ky"] == 4


# UC-41 AC-2: Không tính chứng từ chưa ghi nhận
async def test_unposted_documents_do_not_change_ledger_report(api):
    api.ledger.post(1, 7, datetime(2026, 1, 2, tzinfo=LOCAL_TZ), 7)
    before = await read(api)
    api.ledger.documents.extend([
        {"type": "phieu_nhap", "state": "nhap", "quantity": 100},
        {"type": "phieu_xuat", "state": "cho_duyet", "quantity": 200},
        {"type": "phieu_xuat", "state": "tu_choi", "quantity": 300},
        {"type": "hoan_thanh", "state": "tu_choi", "quantity": 400},
    ])
    after = await read(api)
    assert after == before
    assert (after["mat_hang"][0]["nhap_trong_ky"], after["mat_hang"][0]["xuat_trong_ky"]) == (7, 0)


# UC-41 AC-3: Kỳ tính theo giờ Việt Nam
async def test_january_2330_receipt_is_not_february_movement(api):
    api.ledger.post(1, 9, datetime(2026, 1, 31, 23, 30, tzinfo=LOCAL_TZ), 9)
    jan = await read(api)
    feb = await read(api, {"ky": "thang", "nam": 2026, "thang": 2})
    assert jan["tu_thoi_diem"] == "2026-01-01T00:00:00+07:00"
    assert jan["den_thoi_diem"] == "2026-02-01T00:00:00+07:00"
    assert jan["mat_hang"][0]["nhap_trong_ky"] == 9
    assert feb["mat_hang"][0]["nhap_trong_ky"] == 0
    assert feb["mat_hang"][0]["ton_dau_ky"] == 9
    assert api.ledger.calls[0][:2] == (
        datetime(2025, 12, 31, 17, tzinfo=timezone.utc),
        datetime(2026, 1, 31, 17, tzinfo=timezone.utc),
    )
    assert api.ledger.calls[0][0].tzinfo is timezone.utc


# UC-41 AC-3: Kỳ tính theo giờ Việt Nam
@pytest.mark.parametrize("query,start,end", [
    (JANUARY, "2025-12-31T17:00:00+00:00", "2026-01-31T17:00:00+00:00"),
    ({"ky": "quy", "nam": 2026, "quy": 1}, "2025-12-31T17:00:00+00:00", "2026-03-31T17:00:00+00:00"),
    ({"ky": "nam", "nam": 2026}, "2025-12-31T17:00:00+00:00", "2026-12-31T17:00:00+00:00"),
    ({"ky": "thang", "nam": 2026, "thang": 12}, "2026-11-30T17:00:00+00:00", "2026-12-31T17:00:00+00:00"),
    ({"ky": "thang", "nam": 2024, "thang": 2}, "2024-01-31T17:00:00+00:00", "2024-02-29T17:00:00+00:00"),
])
def test_period_boundaries(query, start, end):
    tu, den = bien_ky(**query)
    assert tu.astimezone(timezone.utc).isoformat() == start
    assert den.astimezone(timezone.utc).isoformat() == end


# UC-41 AC-4: Tồn đầu kỳ nối tiếp
@pytest.mark.parametrize("first,second", [
    (JANUARY, {"ky": "thang", "nam": 2026, "thang": 2}),
    ({"ky": "quy", "nam": 2026, "quy": 1}, {"ky": "quy", "nam": 2026, "quy": 2}),
])
async def test_adjacent_periods_carry_closing_stock(api, first, second):
    boundary, _ = bien_ky(**second)
    for id_ in (1, 2):
        api.ledger.post(id_, 20, datetime(2026, 1, 2, tzinfo=LOCAL_TZ), 20)
        api.ledger.post(id_, -4, boundary - timedelta(microseconds=1), 16)
        api.ledger.post(id_, 7, boundary, 23)
    previous = (await read(api, first))["mat_hang"]
    following = (await read(api, second))["mat_hang"]
    assert [r["ton_cuoi_ky"] for r in previous] == [16, 16, 0]
    assert [r["ton_dau_ky"] for r in following] == [16, 16, 0]
    assert [r["nhap_trong_ky"] for r in following] == [7, 7, 0]


# UC-41 A1: Không có mặt hàng thỏa bộ lọc
@pytest.mark.parametrize("filters", [
    {"mat_hang_id": 999}, {"mat_hang_id": 1, "loai_mat_hang": "thanh_pham"},
])
async def test_unmatched_filters_return_empty_200(api, filters):
    assert (await read(api, {**JANUARY, **filters}))["mat_hang"] == []
    assert api.ledger.calls[-1][2:] == (filters["mat_hang_id"], filters.get("loai_mat_hang"))


# UC-41 A2: Mặt hàng không có biến động trong kỳ
async def test_unchanged_and_never_traded_inactive_items_remain_visible(api):
    api.ledger.post(1, 12, datetime(2025, 12, 1, tzinfo=LOCAL_TZ), 12)
    rows = (await read(api))["mat_hang"]
    assert [r["mat_hang_id"] for r in rows] == [1, 2, 3]
    assert [(r["ton_dau_ky"], r["nhap_trong_ky"], r["xuat_trong_ky"], r["ton_cuoi_ky"])
            for r in rows] == [(12, 0, 0, 12), (0, 0, 0, 0), (0, 0, 0, 0)]


# UC-41 A3: Người không có quyền
@pytest.mark.parametrize("actor,status", [(2, 403), (3, 403), (None, 401)])
async def test_unauthorized_requests_never_read_report(api, actor, status):
    response = await api.client.get(URL, params=JANUARY, headers=api.headers.get(actor, {}))
    assert response.status_code == status
    assert api.ledger.calls == []


# UC-41 R2: Lọc theo mặt hàng và loại, kết hợp AND
@pytest.mark.parametrize("filters,ids", [
    ({"loai_mat_hang": "thanh_pham"}, [2, 3]),
    ({"mat_hang_id": 1}, [1]),
    ({"mat_hang_id": 2, "loai_mat_hang": "thanh_pham"}, [2]),
])
async def test_filters_reach_repository(api, filters, ids):
    rows = (await read(api, {**JANUARY, **filters}))["mat_hang"]
    assert [r["mat_hang_id"] for r in rows] == ids
    assert api.ledger.calls[-1][2:] == (filters.get("mat_hang_id"), filters.get("loai_mat_hang"))


# UC-41 R1: Kỳ và bộ lọc không hợp lệ trả 422 trước khi đọc dữ liệu
@pytest.mark.parametrize("params", [
    {}, {"nam": 2026}, {"ky": "nam"}, {"ky": "tuan", "nam": 2026},
    {"ky": "thang", "nam": 2026}, {"ky": "quy", "nam": 2026},
    {"ky": "nam", "nam": 2026, "thang": 1},
    {"ky": "nam", "nam": 2026, "quy": 1},
    {**JANUARY, "quy": 1}, {"ky": "quy", "nam": 2026, "quy": 1, "thang": 1},
    {**JANUARY, "thang": 0}, {**JANUARY, "thang": 13},
    {"ky": "quy", "nam": 2026, "quy": 0}, {"ky": "quy", "nam": 2026, "quy": 5},
    {**JANUARY, "nam": 1}, {**JANUARY, "nam": 9999},
    {**JANUARY, "mat_hang_id": 0}, {**JANUARY, "mat_hang_id": -1},
    {**JANUARY, "loai_mat_hang": "ban_thanh_pham"}, {**JANUARY, "extra": "bad"},
])
async def test_invalid_queries_return_422_without_repository(api, params):
    response = await api.client.get(URL, params=params, headers=api.headers[1])
    assert response.status_code == 422, response.text
    assert api.ledger.calls == []


# UC-41 A2: Kỳ tương lai được phép và giữ số dư hiện tại
async def test_future_period_carries_current_stock(api):
    api.ledger.post(1, 17, datetime(2026, 1, 1, tzinfo=LOCAL_TZ), 17)
    rows = (await read(api, {"ky": "nam", "nam": 9998}))["mat_hang"]
    assert (rows[0]["ton_dau_ky"], rows[0]["ton_cuoi_ky"]) == (17, 17)
    assert (rows[0]["nhap_trong_ky"], rows[0]["xuat_trong_ky"]) == (0, 0)
    assert bien_ky("nam", 2)[0].astimezone(timezone.utc).year == 1


# UC-41 AC-1: Tồn lấy từ snapshot cuối, xử lý trùng posted_at bằng id
async def test_last_snapshot_wins_even_when_not_sum_of_history(ledger):
    before = datetime(2025, 12, 31, tzinfo=LOCAL_TZ)
    ledger.post(1, 10, before, 50)
    ledger.post(1, -2, before, 48)
    result = await BaoCaoService(ledger).nhap_xuat_ton(NhapXuatTonQuery(**JANUARY))
    assert result.data.mat_hang[0].ton_dau_ky == 48
    assert result.data.mat_hang[0].ton_cuoi_ky == 48


# UC-41 AC-2: Repository chỉ SELECT sổ và mặt hàng với bind params, không commit/audit
async def test_sql_repository_is_read_only_and_maps_records():
    record = NhapXuatTonRow(1, "MH-000001", "Frame", "linh_kien", "cái", 5, 3, 2, 6)
    session = AsyncMock()
    result = Mock()
    result.mappings.return_value = [asdict(record)]
    session.execute.return_value = result
    tu, den = (dt.astimezone(timezone.utc) for dt in bien_ky(**JANUARY))
    rows = await SqlAlchemyBaoCaoRepository(session).nhap_xuat_ton(tu, den, 1, "linh_kien")
    assert rows == [record]
    statement, params = session.execute.call_args.args
    sql = str(statement)
    assert sql.count('FROM "GiaoDichKho"') == 3
    assert 'FROM "MatHang"' in sql
    assert sql.count("ORDER BY g.posted_at DESC, g.id DESC LIMIT 1") == 2
    assert "g.posted_at >= :tu_utc AND g.posted_at < :den_utc" in sql
    assert 'ORDER BY m.loai_mat_hang, m.ma_mat_hang' in sql
    assert not any(word in sql for word in ("PhieuNhap", "PhieuXuat", "ChungTu", "INSERT", "UPDATE", "DELETE", "is_active"))
    assert params == {"tu_utc": tu, "den_utc": den, "mat_hang_id": 1, "loai_mat_hang": "linh_kien"}
    assert session.mock_calls == [call.execute(statement, params), call.execute().mappings()]
    session.commit.assert_not_called()
    session.flush.assert_not_called()
    session.add.assert_not_called()


# UC-41 A3: Router đã đăng ký trong ứng dụng và chỉ cho phép GET
def test_application_registers_report_get_route():
    operation = application.openapi()["paths"][URL]
    assert set(operation) == {"get"}
    assert operation["get"]["summary"] == "UC-41: Xem báo cáo nhập-xuất-tồn"
