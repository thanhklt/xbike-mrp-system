"""UC-25: request listing through stateful ports, ASGI and compiled PostgreSQL SQL."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from test_uc23_lap_gui_yeu_cau_san_xuat import EMPLOYEE, MANAGER, URL
from test_uc23_lap_gui_yeu_cau_san_xuat import api as api

from app.core.errors import ForbiddenException
from app.modules.san_xuat.ports import ProductionIssues
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.schemas import YeuCauListQuery, YeuCauRead
from app.modules.san_xuat.service import generate_yeu_cau_etag
from app.shared.records import RecordPage

EMPLOYEE_HEADERS = {"x-role": "nhan_vien", "x-actor": "20"}
STATES = ["nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"]


@pytest.fixture
def listing_api(api):
    # Insertion order differs from both creation time and deadline; IDs 2/8 tie on both.
    for id_, state, assignee, kind, created_day, due_day in [
        (8, "da_gui", 20, "nhap_kho", 5, 1),
        (1, "nhap", 20, "xuat_giao", 3, 3),
        (6, "da_huy", 20, "nhap_kho", 4, 2),
        (3, "cho_bo_sung_linh_kien", 22, "xuat_giao", 2, 2),
        (5, "hoan_thanh", 22, "nhap_kho", 6, 1),
        (2, "da_gui", 20, "xuat_giao", 5, 1),
        (7, "da_gui", 22, "nhap_kho", 5, 3),
        (4, "dang_thuc_hien", 20, "nhap_kho", 1, 2),
    ]:
        created_at = datetime(2026, 11, created_day, tzinfo=timezone.utc)
        api.stored[id_] = YeuCauRead(
            id=id_, ma_yeu_cau_san_xuat=f"YCSX-202611-{id_:06d}",
            loai_yeu_cau=kind, han_hoan_thanh=date(2026, 12, due_day),
            mat_hang_id=1, so_luong=10, nhan_vien_id=10, nhan_vien_duoc_giao_id=assignee,
            trang_thai=state, created_at=created_at, updated_at=created_at,
            completed_at=created_at if state == "hoan_thanh" else None,
            bom_id=None if state == "nhap" else 102,
            gui_at=None if state == "nhap" else created_at,
            so_luong_dung_thanh_pham=None, so_luong_can_san_xuat=None,
            kiem_tra_lan_dau_at=None, started_at=None, huy_at=None, nguoi_huy_id=None,
            ly_do_huy=None, phien_ban=1,
        )

    async def listing(params, actor_id):
        rows = [
            row for row in api.stored.values()
            if actor_id is None or (row.nhan_vien_duoc_giao_id == actor_id and row.trang_thai != "nhap")
        ]
        for field in ("trang_thai", "mat_hang_id", "nhan_vien_duoc_giao_id", "loai_yeu_cau"):
            value = getattr(params, field)
            if value is not None:
                rows = [row for row in rows if getattr(row, field) == value]
        rows.sort(
            key=lambda row: (getattr(row, params.sort.removeprefix("-")), row.id),
            reverse=params.sort.startswith("-"),
        )
        offset = (params.page - 1) * params.page_size
        return RecordPage(rows[offset:offset + params.page_size], len(rows))

    api.repo.list_entries.side_effect = listing
    return api


async def repository_sql(params, actor_id):
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 8
    records = Mock()
    records.all.return_value = []
    session.scalars.return_value = records
    await SqlAlchemyYeuCauSanXuatRepository(session).list_entries(params, actor_id)
    return tuple(
        " ".join(str(statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
        )).split())
        for statement in (session.scalar.call_args.args[0], session.scalars.call_args.args[0])
    )


# UC-25 AC-1: QLK thấy đủ sáu trạng thái, loại, hạn và metadata chính xác
async def test_manager_sees_all_states_with_type_deadline_and_pagination(listing_api):
    response = await listing_api.client.get(URL)
    assert response.status_code == 200, response.text
    rows = response.json()["data"]
    assert [row["id"] for row in rows] == [5, 8, 7, 2, 6, 1, 3, 4]
    assert {row["trang_thai"] for row in rows} == set(STATES)
    for row in rows:
        stored = listing_api.stored[row["id"]]
        assert (row["trang_thai"], row["loai_yeu_cau"], row["han_hoan_thanh"]) == (
            stored.trang_thai, stored.loai_yeu_cau, stored.han_hoan_thanh.isoformat(),
        )
    assert response.json()["meta"] == {
        "request_id": response.json()["meta"]["request_id"],
        "page": 1, "page_size": 20, "total": 8, "total_pages": 1,
    }
    paged = await listing_api.client.get(URL, params={"page": 2, "page_size": 3})
    assert paged.status_code == 200
    assert [row["id"] for row in paged.json()["data"]] == [2, 6, 1]
    assert {key: value for key, value in paged.json()["meta"].items() if key != "request_id"} == {
        "page": 2, "page_size": 3, "total": 8, "total_pages": 3,
    }


# UC-25 AC-1: SQL QLK không lọc nhân viên/trạng thái và không JOIN trạng thái nhân viên
async def test_manager_sql_has_no_employee_or_status_restriction():
    for sql in await repository_sql(YeuCauListQuery(sort="-created_at"), None):
        assert " WHERE " not in sql
        assert " JOIN " not in sql
        assert 'FROM "YeuCauSanXuat"' in sql


# UC-25 AC-2: NV chỉ thấy yêu cầu của mình; tham số người khác không vượt phạm vi
async def test_employee_scope_cannot_be_overridden_by_assignee_filter(listing_api):
    response = await listing_api.client.get(URL, headers=EMPLOYEE_HEADERS)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [8, 2, 6, 4]
    assert {row["nhan_vien_duoc_giao_id"] for row in response.json()["data"]} == {20}
    filtered = await listing_api.client.get(
        URL, headers=EMPLOYEE_HEADERS, params={"nhan_vien_duoc_giao_id": 22},
    )
    assert filtered.status_code == 200
    assert filtered.json()["data"] == [] and filtered.json()["meta"]["total"] == 0
    params, actor_id = listing_api.repo.list_entries.call_args.args
    assert actor_id == 20 and params.nhan_vien_duoc_giao_id == 22
    for sql in await repository_sql(params, actor_id):
        assert '"YeuCauSanXuat".nhan_vien_duoc_giao_id = 20' in sql
        assert 'AND "YeuCauSanXuat".nhan_vien_duoc_giao_id = 22' in sql
        assert '"YeuCauSanXuat".trang_thai != \'nhap\'' in sql


# UC-25 A2: NV mở thẳng yêu cầu đã gửi của người khác bị 403 ở router và service
async def test_employee_opening_another_assignees_request_is_forbidden(listing_api):
    response = await listing_api.client.get(f"{URL}/3", headers=EMPLOYEE_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    with pytest.raises(ForbiddenException):
        await listing_api.service.get_entry(3, EMPLOYEE, "uc25-other")
    own = await listing_api.client.get(f"{URL}/2", headers=EMPLOYEE_HEADERS)
    assert own.status_code == 200 and own.json()["data"]["id"] == 2


# UC-25 AC-3: Không gửi sort, cả NV và QLK đều mới nhất trước; id phụ cùng chiều ở SQL
@pytest.mark.parametrize("actor,headers,sort,ids,direction", [
    (EMPLOYEE, EMPLOYEE_HEADERS, "-created_at", [8, 2, 6, 4], "DESC"),
    (MANAGER, {}, "-created_at", [5, 8, 7, 2, 6, 1, 3, 4], "DESC"),
])
async def test_default_sort_is_chosen_by_role_without_mutating_query(
    listing_api, actor, headers, sort, ids, direction,
):
    params = YeuCauListQuery()
    assert params.sort is None
    result = await listing_api.service.list_entries(params, actor, "uc25-default")
    assert params.sort is None
    assert [row.id for row in result.data] == ids
    response = await listing_api.client.get(URL, headers=headers)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == ids
    forwarded, actor_id = listing_api.repo.list_entries.call_args.args
    assert forwarded.sort == sort
    assert actor_id == (20 if actor == EMPLOYEE else None)
    _, sql = await repository_sql(forwarded, actor_id)
    assert f'ORDER BY "YeuCauSanXuat".created_at {direction}, "YeuCauSanXuat".id {direction}' in sql


# UC-25 AC-4: Cả hai vai trò sắp theo hạn tăng/giảm, cùng hạn thì id cùng chiều
@pytest.mark.parametrize("headers,ascending", [
    ({}, [2, 5, 8, 3, 4, 6, 1, 7]),
    (EMPLOYEE_HEADERS, [2, 8, 4, 6]),
])
@pytest.mark.parametrize("descending", [False, True])
async def test_deadline_sort_with_same_direction_id_tiebreaker(listing_api, headers, ascending, descending):
    sort = "-han_hoan_thanh" if descending else "han_hoan_thanh"
    response = await listing_api.client.get(URL, headers=headers, params={"sort": sort})
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]] == (ascending[::-1] if descending else ascending)
    params, actor_id = listing_api.repo.list_entries.call_args.args
    assert params.sort == sort
    _, sql = await repository_sql(params, actor_id)
    direction = "DESC" if descending else "ASC"
    assert f'ORDER BY "YeuCauSanXuat".han_hoan_thanh {direction}, "YeuCauSanXuat".id {direction}' in sql


# UC-25 A3: Lọc đúng từng loại ở cả hai vai trò và áp dụng trước COUNT/phân trang
@pytest.mark.parametrize("headers,kind,ids", [
    ({}, "nhap_kho", [5, 8, 7, 6, 4]),
    (EMPLOYEE_HEADERS, "nhap_kho", [8, 6, 4]),
    ({}, "xuat_giao", [2, 1, 3]),
    (EMPLOYEE_HEADERS, "xuat_giao", [2]),
])
async def test_type_filter_respects_role_and_count(listing_api, headers, kind, ids):
    response = await listing_api.client.get(URL, headers=headers, params={"loai_yeu_cau": kind})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == ids
    assert {row["loai_yeu_cau"] for row in response.json()["data"]} == {kind}
    assert response.json()["meta"]["total"] == len(ids)
    params, actor_id = listing_api.repo.list_entries.call_args.args
    assert params.loai_yeu_cau == kind
    for sql in await repository_sql(params, actor_id):
        assert f'"YeuCauSanXuat".loai_yeu_cau = \'{kind}\'' in sql
    paged = await listing_api.client.get(
        URL, headers=headers, params={"loai_yeu_cau": kind, "page_size": 1},
    )
    assert paged.status_code == 200
    assert [row["id"] for row in paged.json()["data"]] == ids[:1]
    assert paged.json()["meta"]["total"] == len(ids)


# UC-25 A3: Loại hoặc sort ngoài whitelist trả 422 trước khi gọi repository
@pytest.mark.parametrize("headers", [{}, EMPLOYEE_HEADERS])
@pytest.mark.parametrize("params,field", [
    ({"loai_yeu_cau": "other"}, "loai_yeu_cau"),
    ({"sort": "other"}, "sort"),
])
async def test_invalid_type_or_sort_is_rejected(listing_api, headers, params, field):
    response = await listing_api.client.get(URL, headers=headers, params=params)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    assert {detail["field"] for detail in response.json()["error"]["details"]} == {field}
    listing_api.repo.list_entries.assert_not_awaited()


# UC-25 AC-5: Nháp được giao vẫn ẩn, kể cả lọc nhap; chi tiết trả 404, SQL lọc trước COUNT
async def test_assigned_draft_is_hidden_in_list_filter_and_detail(listing_api):
    for params, ids in [({}, [8, 2, 6, 4]), ({"trang_thai": "nhap"}, [])]:
        response = await listing_api.client.get(URL, headers=EMPLOYEE_HEADERS, params=params)
        assert response.status_code == 200
        assert [row["id"] for row in response.json()["data"]] == ids
        assert response.json()["meta"]["total"] == len(ids)
    response = await listing_api.client.get(f"{URL}/1", headers=EMPLOYEE_HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "khong_tim_thay"
    for sql in await repository_sql(YeuCauListQuery(sort="created_at", trang_thai="nhap"), 20):
        assert '"YeuCauSanXuat".trang_thai != \'nhap\'' in sql
        assert '"YeuCauSanXuat".trang_thai = \'nhap\'' in sql
        assert '"YeuCauSanXuat".nhan_vien_duoc_giao_id = 20' in sql


# UC-25 R5: Khóa nhân viên được giao không làm yêu cầu biến mất khỏi danh sách QLK
async def test_locking_assignee_preserves_manager_list(listing_api):
    before = await listing_api.client.get(URL)
    assert before.status_code == 200
    assert listing_api.employees[20].trang_thai == "hoat_dong"
    listing_api.employees[20].trang_thai = "bi_khoa"
    after = await listing_api.client.get(URL)
    assert after.status_code == 200
    assert after.json()["data"] == before.json()["data"]
    assert {row["id"] for row in after.json()["data"] if row["nhan_vien_duoc_giao_id"] == 20} == {1, 2, 4, 6, 8}
    listing_api.employee_repo.get_for_share.assert_not_awaited()


# UC-25 D6: Danh sách/chi tiết không có tiến độ xuất, không gọi cổng phiếu xuất hoặc ghi dữ liệu
@pytest.mark.parametrize("headers", [{}, EMPLOYEE_HEADERS])
async def test_list_and_detail_remove_export_progress_without_issue_calls(listing_api, headers):
    before = dict(listing_api.stored)
    removed = {"so_luong_da_xuat", "so_luong_con_phai_xuat"}
    assert removed.isdisjoint(YeuCauRead.model_fields)
    assert not hasattr(ProductionIssues, "tong_da_xuat_thanh_pham")
    response = await listing_api.client.get(URL, headers=headers)
    assert response.status_code == 200 and response.json()["data"]
    for row in response.json()["data"]:
        assert removed.isdisjoint(row)
    detail = await listing_api.client.get(f"{URL}/2", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"] == listing_api.stored[2].model_dump(mode="json")
    assert removed.isdisjoint(detail.json()["data"])
    assert detail.headers["etag"] == generate_yeu_cau_etag(listing_api.stored[2])
    assert listing_api.issues.mock_calls == []
    assert listing_api.stored == before and not listing_api.history and not listing_api.pending
    listing_api.repo.update.assert_not_awaited()
    listing_api.audit.append.assert_not_awaited()
    listing_api.session.commit.assert_not_awaited()


# UC-25 AC-1: Chỉ NV/QLK được đọc; vai trò khác bị 403 ở ASGI và service
@pytest.mark.parametrize("roles", [["quan_tri_vien"], []])
async def test_other_roles_cannot_list_or_open_requests(listing_api, roles):
    headers = {"x-role": roles[0] if roles else ""}
    for path in (URL, f"{URL}/2"):
        response = await listing_api.client.get(path, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "khong_co_quyen"
    actor = {"sub": "10", "roles": roles}
    with pytest.raises(ForbiddenException):
        await listing_api.service.list_entries(YeuCauListQuery(), actor, "uc25-role")
    with pytest.raises(ForbiddenException):
        await listing_api.service.get_entry(2, actor, "uc25-role")
    listing_api.repo.list_entries.assert_not_awaited()
