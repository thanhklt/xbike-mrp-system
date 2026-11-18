"""UC-33: ASGI/service contracts and compiled PostgreSQL, without a database."""

from copy import deepcopy
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenException
from app.modules.san_xuat.models import ChungTuHoanThanhSx
from app.modules.san_xuat.repository.chung_tu_hoan_thanh_sx import (
    SqlAlchemyChungTuHoanThanhRepository,
)
from app.modules.san_xuat.schemas import ChungTuListItem, ChungTuListQuery, ChungTuRead
from app.shared.records import RecordPage
from tests import test_uc30_chung_tu_hoan_thanh as uc30

completion_api = uc30.api
URL = uc30.URL
MANAGER = {"sub": "10", "roles": ["quan_ly"]}
HEADERS = {"x-role": "quan_ly", "x-user": "10"}


@pytest.fixture
def api(completion_api):
    rows = []
    # completion_id: assigned_request_employee_id
    assigned_owners = {2: 20, 9: 20, 4: 20, 3: 21, 8: 20, 1: 21}
    for id_, item, employee, kind, state, instant in [
        (2, 5, 20, "xuat_giao", "cho_duyet", "2026-11-15T17:00:00+00:00"),
        (9, 5, 20, "xuat_giao", "nhap", None),
        (4, 6, 20, "nhap_kho", "da_duyet", "2026-11-16T17:00:00+00:00"),
        (3, 5, 21, "nhap_kho", "tu_choi", "2026-11-16T16:59:59+00:00"),
        (8, 5, 20, "xuat_giao", "cho_duyet", "2026-11-15T17:00:00+00:00"),
        (1, 6, 21, "nhap_kho", "cho_duyet", "2026-11-15T16:59:59+00:00"),
    ]:
        rows.append(ChungTuListItem(
            id=id_, ma_phieu=f"HTSX-202611-{id_:06d}", yeu_cau_san_xuat_id=id_ + 100,
            so_luong_hoan_thanh=id_ + 10, nhan_vien_id=employee, trang_thai=state,
            finish_time=datetime.fromisoformat(instant) if instant else None,
            created_at=uc30.NOW, updated_at=uc30.NOW, nguoi_xu_ly_id=None,
            xu_ly_at=None, ly_do_tu_choi=None, phien_ban=2,
            ma_yeu_cau_san_xuat=f"YCSX-202611-{id_ + 100:06d}",
            mat_hang_id=item, loai_yeu_cau=kind,
        ))

    async def listing(params):
        matches = [row for row in rows if row.trang_thai != "nhap"]
        for field in ("mat_hang_id", "nhan_vien_id", "trang_thai", "loai_yeu_cau"):
            value = getattr(params, field)
            if value is not None:
                matches = [row for row in matches if getattr(row, field) == value]
        zone = ZoneInfo("Asia/Ho_Chi_Minh")
        if params.tu_ngay:
            start = datetime.combine(params.tu_ngay, time.min, zone)
            matches = [row for row in matches if row.finish_time >= start]
        if params.den_ngay:
            end = datetime.combine(params.den_ngay, time.min, zone) + timedelta(days=1)
            matches = [row for row in matches if row.finish_time < end]
        matches.sort(key=lambda row: (row.finish_time, row.id), reverse=True)
        offset = (params.page - 1) * params.page_size
        return RecordPage(matches[offset:offset + params.page_size], len(matches))

    async def listing_my(params, employee_id):
        # Filtered by assigned request owner, not creator
        matches = [row for row in rows if assigned_owners.get(row.id) == employee_id]
        for field in ("mat_hang_id", "trang_thai", "loai_yeu_cau"):
            value = getattr(params, field)
            if value is not None:
                matches = [row for row in matches if getattr(row, field) == value]
        zone = ZoneInfo("Asia/Ho_Chi_Minh")
        if params.tu_ngay:
            start = datetime.combine(params.tu_ngay, time.min, zone)
            matches = [row for row in matches if row.finish_time and row.finish_time >= start]
        if params.den_ngay:
            end = datetime.combine(params.den_ngay, time.min, zone) + timedelta(days=1)
            matches = [row for row in matches if row.finish_time and row.finish_time < end]
        matches.sort(key=lambda row: (row.finish_time or datetime.min.replace(tzinfo=zone), row.id), reverse=True)
        offset = (params.page - 1) * params.page_size
        return RecordPage(matches[offset:offset + params.page_size], len(matches))

    completion_api.rows = rows
    completion_api.repo.list_entries.side_effect = listing
    completion_api.repo.list_my_entries.side_effect = listing_my
    return completion_api


async def repository_query(params, total=5, rows=()):
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = total
    session.execute.return_value = Mock()
    session.execute.return_value.all.return_value = rows
    result = await SqlAlchemyChungTuHoanThanhRepository(session).list_entries(params)
    queries = [session.scalar.call_args.args[0]]
    if session.execute.await_count:
        queries.append(session.execute.call_args.args[0])
    sql = [" ".join(str(query.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    )).split()) for query in queries]
    return result, sql, session


# UC-33 AC-1: Sản phẩm và nhân viên phải cùng khớp; SQL và port nhận cả hai tiêu chí
async def test_product_and_employee_filters_are_combined(api):
    response = await api.client.get(URL, headers=HEADERS, params={
        "mat_hang_id": 5, "nhan_vien_id": 20,
    })
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]] == [8, 2]
    assert {(row["mat_hang_id"], row["nhan_vien_id"]) for row in response.json()["data"]} == {(5, 20)}
    params = api.repo.list_entries.call_args.args[0]
    assert params == ChungTuListQuery(mat_hang_id=5, nhan_vien_id=20)
    _, statements, _ = await repository_query(params)
    for sql in statements:
        assert 'JOIN "YeuCauSanXuat" ON "ChungTuHoanThanhSx".yeu_cau_san_xuat_id = "YeuCauSanXuat".id' in sql
        assert 'AND "YeuCauSanXuat".mat_hang_id = 5' in sql
        assert 'AND "ChungTuHoanThanhSx".nhan_vien_id = 20' in sql


# UC-33 AC-2: Lọc Chờ duyệt chỉ trả các chứng từ Chờ duyệt từ dữ liệu nhiều trạng thái
async def test_pending_status_filter(api):
    response = await api.client.get(URL, headers=HEADERS, params={"trang_thai": "cho_duyet"})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [8, 2, 1]
    assert {row["trang_thai"] for row in response.json()["data"]} == {"cho_duyet"}
    _, statements, _ = await repository_query(api.repo.list_entries.call_args.args[0])
    for sql in statements:
        assert 'AND "ChungTuHoanThanhSx".trang_thai = \'cho_duyet\'' in sql


# UC-33 R2: Loại yêu cầu qua JOIN và khoảng ngày finish_time gồm đúng hai biên giờ VN
async def test_type_and_vietnam_finish_date_boundaries(api):
    response = await api.client.get(URL, headers=HEADERS, params={
        "tu_ngay": "2026-11-16", "den_ngay": "2026-11-16",
    })
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [3, 8, 2]
    typed = await api.client.get(URL, headers=HEADERS, params={
        "tu_ngay": "2026-11-16", "den_ngay": "2026-11-16", "loai_yeu_cau": "nhap_kho",
    })
    assert typed.status_code == 200
    assert [row["id"] for row in typed.json()["data"]] == [3]
    _, statements, _ = await repository_query(api.repo.list_entries.call_args.args[0])
    for sql in statements:
        assert '"YeuCauSanXuat".loai_yeu_cau = \'nhap_kho\'' in sql
        assert '"ChungTuHoanThanhSx".finish_time >= \'2026-11-15 17:00:00+00:00\'' in sql
        assert '"ChungTuHoanThanhSx".finish_time < \'2026-11-16 17:00:00+00:00\'' in sql
        assert '"ChungTuHoanThanhSx".created_at >=' not in sql


# UC-33 D2: Đủ mọi trường ChungTuRead và ba trường JOIN; meta và ánh xạ ORM chính xác
async def test_row_contract_and_repository_mapping(api):
    response = await api.client.get(URL, headers=HEADERS)
    assert response.status_code == 200
    expected = sorted(api.rows[:1] + api.rows[2:], key=lambda row: (row.finish_time, row.id), reverse=True)
    assert response.json()["data"] == [row.model_dump(mode="json") for row in expected]
    assert set(response.json()["data"][0]) == set(ChungTuRead.model_fields) | {
        "ma_yeu_cau_san_xuat", "mat_hang_id", "loai_yeu_cau",
    }
    assert response.json()["meta"] == {
        "request_id": response.json()["meta"]["request_id"],
        "page": 1, "page_size": 20, "total": 5, "total_pages": 1,
    }
    assert str(UUID(response.json()["meta"]["request_id"])) == response.json()["meta"]["request_id"]
    row = expected[0]
    record = ChungTuHoanThanhSx(**{key: getattr(row, key) for key in ChungTuRead.model_fields})
    result, _, _ = await repository_query(ChungTuListQuery(), rows=[(
        record, row.ma_yeu_cau_san_xuat, row.mat_hang_id, row.loai_yeu_cau,
    )])
    assert result.items == [row] and result.total == 5


# UC-33 D4: Nháp không xuất hiện và không được đếm cả khi bỏ lọc hoặc lọc theo từng trường
@pytest.mark.parametrize("filters,total", [
    ({}, 5), ({"mat_hang_id": 5}, 3), ({"nhan_vien_id": 20}, 3),
    ({"loai_yeu_cau": "xuat_giao"}, 2),
])
async def test_draft_is_always_excluded_from_rows_and_total(api, filters, total):
    response = await api.client.get(URL, headers=HEADERS, params=filters)
    assert response.status_code == 200
    assert len(response.json()["data"]) == total
    assert response.json()["meta"]["total"] == total
    assert all(row["trang_thai"] != "nhap" and row["id"] != 9 for row in response.json()["data"])
    _, statements, _ = await repository_query(ChungTuListQuery(**filters))
    for sql in statements:
        assert '"ChungTuHoanThanhSx".trang_thai != \'nhap\'' in sql


# UC-33 D6: finish_time DESC rồi id DESC, phân trang và trang vượt tổng không truy vấn dòng
async def test_sort_pagination_and_out_of_range_page(api):
    response = await api.client.get(URL, headers=HEADERS)
    assert [row["id"] for row in response.json()["data"]] == [4, 3, 8, 2, 1]
    response = await api.client.get(URL, headers=HEADERS, params={"page": 2, "page_size": 2})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [8, 2]
    assert {key: value for key, value in response.json()["meta"].items() if key != "request_id"} == {
        "page": 2, "page_size": 2, "total": 5, "total_pages": 3,
    }
    _, statements, _ = await repository_query(ChungTuListQuery(page=2, page_size=2))
    assert 'ORDER BY "ChungTuHoanThanhSx".finish_time DESC, "ChungTuHoanThanhSx".id DESC LIMIT 2 OFFSET 2' in statements[1]
    response = await api.client.get(URL, headers=HEADERS, params={"page": 10**20})
    assert response.status_code == 200 and response.json()["data"] == []
    assert response.json()["meta"]["total"] == 5
    result, _, session = await repository_query(ChungTuListQuery(page=10**20))
    assert result == RecordPage([], 5)
    session.execute.assert_not_awaited()


# UC-33 A1: Không khớp trả 200 data rỗng, total và total_pages đều 0, không select dòng
async def test_no_matches_returns_empty_page(api):
    response = await api.client.get(URL, headers=HEADERS, params={"mat_hang_id": 99})
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["total"] == response.json()["meta"]["total_pages"] == 0
    result, _, session = await repository_query(ChungTuListQuery(mat_hang_id=99), total=0)
    assert result == RecordPage([], 0)
    session.execute.assert_not_awaited()


# UC-33 AC-3: Router và service chặn NV/Admin trước truy vấn, chưa đăng nhập trả 401
@pytest.mark.parametrize("role,status", [("nhan_vien", 403), ("quan_tri_vien", 403), ("anonymous", 401)])
async def test_only_manager_can_list(api, role, status):
    response = await api.client.get(URL, headers={"x-role": role})
    assert response.status_code == status
    assert response.json()["error"]["code"] == ("chua_xac_thuc" if status == 401 else "khong_co_quyen")
    with pytest.raises(ForbiddenException):
        await api.service.danh_sach(ChungTuListQuery(), {"sub": "20", "roles": [role]}, "direct")
    api.repo.list_entries.assert_not_awaited()


# UC-33 R2: Nháp/trạng thái lạ, ngày đảo, ID không dương, phân trang và query dư bị 422
@pytest.mark.parametrize("params", [
    {"trang_thai": "nhap"}, {"trang_thai": "unknown"}, {"loai_yeu_cau": "unknown"},
    {"tu_ngay": "2026-11-17", "den_ngay": "2026-11-16"}, {"tu_ngay": "bad-date"},
    {"mat_hang_id": 0}, {"nhan_vien_id": -1}, {"page": 0}, {"page_size": 0},
    {"page_size": 101}, {"sort": "-id"}, {"q": "HTSX"}, {"force": "true"},
    [("mat_hang_id", "5"), ("mat_hang_id", "6")],
])
async def test_invalid_query_is_rejected(api, params):
    response = await api.client.get(URL, headers=HEADERS, params=params)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    api.repo.list_entries.assert_not_awaited()


# UC-33 D1: Strip chuỗi, giới hạn page_size 100 và ID vượt INT32 không khớp thay vì lỗi DB
async def test_stripping_page_size_and_oversized_ids(api):
    params = ChungTuListQuery.model_validate({"page_size": 100, "trang_thai": " cho_duyet ", "loai_yeu_cau": " xuat_giao "})
    assert params.trang_thai == "cho_duyet" and params.loai_yeu_cau == "xuat_giao"
    result = await api.service.danh_sach(params, MANAGER, "direct")
    assert [row.id for row in result.data] == [8, 2]
    assert result.meta.page_size == 100 and result.meta.request_id == "direct"
    response = await api.client.get(URL, headers=HEADERS, params={
        "page_size": 100, "trang_thai": " cho_duyet ", "loai_yeu_cau": " xuat_giao ",
    })
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [8, 2]
    for field in ("mat_hang_id", "nhan_vien_id"):
        response = await api.client.get(URL, headers=HEADERS, params={field: 2**31})
        assert response.status_code == 200 and response.json()["data"] == []
        _, statements, _ = await repository_query(ChungTuListQuery(**{field: 2**31}), total=0)
        assert "WHERE false" in statements[0]


# UC-33 D1: Danh sách chỉ đọc, không ETag, audit, transaction hoặc ghi tài nguyên
async def test_list_is_read_only(api):
    before = deepcopy(api.data)
    response = await api.client.get(URL, headers=HEADERS)
    assert response.status_code == 200
    assert "etag" not in response.headers
    assert api.data == before
    api.audit.append.assert_not_awaited()
    api.session.commit.assert_not_awaited()
    api.session.rollback.assert_not_awaited()
    api.repo.add.assert_not_awaited()
    api.repo.update.assert_not_awaited()
    api.repo.get_for_update.assert_not_awaited()
    api.requests.update.assert_not_awaited()


# -------------------------------------------------------------------------
# Employee own completion list: GET /api/v1/chung_tu_hoan_thanh_sx/cua_toi
# -------------------------------------------------------------------------
async def test_employee_can_list_own_completions_including_draft(api):
    # Employee 20 has 4 completions: id 2 (cho_duyet), 9 (nhap), 4 (da_duyet), 8 (cho_duyet)
    res = await api.client.get(f"{URL}/cua_toi", headers={"x-role": "nhan_vien", "x-user": "20"})
    assert res.status_code == 200, res.text
    ids = [row["id"] for row in res.json()["data"]]
    assert 9 in ids  # Draft is visible!
    assert set(ids) == {2, 9, 4, 8}
    assert res.json()["meta"]["total"] == 4


async def test_employee_isolation_completions(api):
    # Employee 21 only sees their own completions (id 3 and 1)
    res = await api.client.get(f"{URL}/cua_toi", headers={"x-role": "nhan_vien", "x-user": "21"})
    assert res.status_code == 200
    ids = [row["id"] for row in res.json()["data"]]
    assert set(ids) == {1, 3}
    assert 9 not in ids


@pytest.mark.parametrize("role", ["quan_ly", "quan_tri_vien"])
async def test_non_employee_cannot_access_cua_toi(api, role):
    res = await api.client.get(f"{URL}/cua_toi", headers={"x-role": role, "x-user": "10"})
    assert res.status_code == 403


async def test_cua_toi_forbids_nhan_vien_id_query_param(api):
    res = await api.client.get(
        f"{URL}/cua_toi",
        headers={"x-role": "nhan_vien", "x-user": "20"},
        params={"nhan_vien_id": 21},
    )
    assert res.status_code == 422


async def test_cua_toi_assigned_vs_creator(api):
    # Completion 10 was created by employee 99, but YCSX was assigned to employee 20
    custom_row = ChungTuListItem(
        id=10,
        ma_phieu="HTSX-202611-000010",
        yeu_cau_san_xuat_id=110,
        so_luong_hoan_thanh=5,
        nhan_vien_id=99,  # Creator is 99
        trang_thai="cho_duyet",
        finish_time=datetime.fromisoformat("2026-11-15T17:00:00+00:00"),
        created_at=uc30.NOW,
        updated_at=uc30.NOW,
        nguoi_xu_ly_id=None,
        xu_ly_at=None,
        ly_do_tu_choi=None,
        phien_ban=1,
        ma_yeu_cau_san_xuat="YCSX-202611-000110",
        mat_hang_id=5,
        loai_yeu_cau="xuat_giao",
    )

    async def mock_list_my(params, employee_id):
        if employee_id == 20:
            return RecordPage([custom_row], 1)
        return RecordPage([], 0)

    api.repo.list_my_entries.side_effect = mock_list_my
    res = await api.client.get(f"{URL}/cua_toi", headers={"x-role": "nhan_vien", "x-user": "20"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == 10
    assert data[0]["nhan_vien_id"] == 99  # Creator is 99, but assigned owner 20 sees it!

    # Employee 99 (who is creator but not assigned owner) does NOT see it
    res_creator = await api.client.get(f"{URL}/cua_toi", headers={"x-role": "nhan_vien", "x-user": "99"})
    assert res_creator.status_code == 200
    assert res_creator.json()["data"] == []


async def test_cua_toi_oversized_id_returns_empty_list(api):
    res = await api.client.get(
        f"{URL}/cua_toi",
        headers={"x-role": "nhan_vien", "x-user": "20"},
        params={"mat_hang_id": 2**31},
    )
    assert res.status_code == 200
    assert res.json()["data"] == []


@pytest.mark.parametrize(
    "bad_param",
    [
        {"den_ngay": "9999-12-31"},
        {"mat_hang_id": 0},
        {"mat_hang_id": -1},
        {"q": "text"},
        {"tu_ngay": "2026-11-20", "den_ngay": "2026-11-10"},
        {"trang_thai": "bad_status"},
    ],
)
async def test_cua_toi_strict_validation(api, bad_param):
    res = await api.client.get(
        f"{URL}/cua_toi",
        headers={"x-role": "nhan_vien", "x-user": "20"},
        params=bad_param,
    )
    assert res.status_code == 422


async def test_cua_toi_rejects_repeated_query_and_body(api):
    # Repeated query
    res = await api.client.get(
        f"{URL}/cua_toi?trang_thai=nhap&trang_thai=cho_duyet",
        headers={"x-role": "nhan_vien", "x-user": "20"},
    )
    assert res.status_code == 422

    # Body on GET
    res_body = await api.client.request(
        "GET",
        f"{URL}/cua_toi",
        headers={"x-role": "nhan_vien", "x-user": "20"},
        content=b'{"extra": "body"}',
    )
    assert res_body.status_code == 422
