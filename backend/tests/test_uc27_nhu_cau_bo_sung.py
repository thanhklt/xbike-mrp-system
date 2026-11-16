"""UC-27: stateful read ports, ASGI and compiled SQL; no database connection."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenException, UnauthorizedException
from app.core.exceptions import register_exception_handlers
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_current_user_payload, get_yeu_cau_san_xuat_service
from app.modules.audit.ports import AuditWriter
from app.modules.san_xuat.ports import HangKhaDung, YeuCauSanXuatRepository
from app.modules.san_xuat.repository.yeu_cau_san_xuat import SqlAlchemyYeuCauSanXuatRepository
from app.modules.san_xuat.router import nhu_cau_bo_sung_router
from app.modules.san_xuat.schemas import YeuCauRead
from app.modules.san_xuat.service.yeu_cau_san_xuat import (
    YeuCauSanXuatService,
    tong_hop_nhu_cau_bo_sung,
)

URL = "/api/v1/nhu_cau_bo_sung_linh_kien"
MANAGER = {"sub": "10", "roles": ["quan_ly"]}
NOW = datetime(2026, 11, 16, 8, tzinfo=timezone.utc)
FRAME = HangKhaDung("MH-000002", "Khung", "cái", 0)


def request_record(id_=1, **changes):
    return YeuCauRead(
        id=id_, ma_yeu_cau_san_xuat=f"YCSX-202611-{id_:06d}",
        **{
            "loai_yeu_cau": "xuat_giao", "mat_hang_id": 5, "so_luong": 13,
            "han_hoan_thanh": date(2026, 12, 1), "nhan_vien_id": 10,
            "nhan_vien_duoc_giao_id": 20, "trang_thai": "cho_bo_sung_linh_kien",
            "bom_id": 101, "created_at": NOW - timedelta(days=2), "updated_at": NOW,
            "gui_at": NOW - timedelta(days=1), "completed_at": None,
            "so_luong_dung_thanh_pham": 3, "so_luong_can_san_xuat": 10,
            "kiem_tra_lan_dau_at": NOW, "started_at": None, "huy_at": None,
            "nguoi_huy_id": None, "ly_do_huy": None, "phien_ban": 2, **changes,
        },
    )


@pytest.fixture
async def api():
    stored = {1: request_record(), 2: request_record(2, nhan_vien_duoc_giao_id=22)}
    needs, available = {1: {2: 10}, 2: {2: 10}}, {2: FRAME}
    repo = AsyncMock(spec=YeuCauSanXuatRepository)
    audit = AsyncMock(spec=AuditWriter)
    session = AsyncMock(spec=AsyncSession)

    async def waiting():
        return sorted(
            [row.model_copy(deep=True) for row in stored.values()
             if row.trang_thai == "cho_bo_sung_linh_kien"],
            key=lambda row: (row.kiem_tra_lan_dau_at, row.id),
        )

    async def requirements(ids):
        return {id_: dict(needs[id_]) for id_ in ids if id_ in needs}

    async def availability(ids, *, lock):
        assert lock is False
        return {id_: available[id_] for id_ in ids}

    repo.yeu_cau_cho_bo_sung.side_effect = waiting
    repo.nhu_cau_cua_cac_yeu_cau.side_effect = requirements
    repo.kha_dung.side_effect = availability
    service = YeuCauSanXuatService(
        repo, audit, SqlAlchemyTransaction(session), Mock(), Mock(), Mock(),
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(nhu_cau_bo_sung_router, prefix="/api/v1")

    async def actor(request: Request):
        role = request.headers.get("x-role", "quan_ly")
        if role == "anonymous":
            raise UnauthorizedException()
        return {"sub": "10", "roles": [role]}

    app.dependency_overrides[get_current_user_payload] = actor
    app.dependency_overrides[get_yeu_cau_san_xuat_service] = lambda: service
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test",
    ) as client:
        yield SimpleNamespace(
            client=client, service=service, repo=repo, audit=audit, session=session,
            stored=stored, needs=needs, available=available,
        )


def sql(statement):
    return " ".join(str(statement.compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True},
    )).split())


def assert_no_writes(api):
    assert api.repo.mock_calls == [
        call.yeu_cau_cho_bo_sung(), call.nhu_cau_cua_cac_yeu_cau([1, 2]),
        call.kha_dung([2], lock=False),
    ]
    assert api.audit.mock_calls == []
    assert api.session.mock_calls == []


# UC-27 AC-1: Hai yêu cầu thiếu 10 khung cộng thành 20, đủ dữ liệu từng dòng
async def test_two_requests_aggregate_twenty_frames(api):
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["tong_hop"] == [{
        "mat_hang_id": 2, "ma_mat_hang": "MH-000002", "ten_mat_hang": "Khung",
        "don_vi_tinh": "cái", "tong_can": 20, "so_luong_con_dung": 0,
        "so_luong_thieu": 20, "so_yeu_cau": 2,
    }]
    assert [row["id"] for row in data["yeu_cau"]] == [1, 2]
    for row in data["yeu_cau"]:
        assert row["linh_kien_thieu"] == [{
            "mat_hang_id": 2, "ma_mat_hang": "MH-000002", "ten_mat_hang": "Khung",
            "don_vi_tinh": "cái", "so_luong_can": 10, "so_luong_con_dung": 0,
            "so_luong_thieu": 10,
        }]
        assert row["da_du"] is False
    assert set(response.json()) == {"data", "meta"}
    assert set(response.json()["meta"]) == {"request_id"}
    assert response.json()["meta"]["request_id"]


# UC-27 AC-1: Còn dùng được 5 chỉ trừ một lần ở tổng hợp, mỗi yêu cầu so riêng
async def test_available_five_means_fifteen_total_and_five_each(api):
    api.available[2] = replace(FRAME, so_luong_con_dung=5)
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["tong_hop"][0] == {
        "mat_hang_id": 2, "ma_mat_hang": "MH-000002", "ten_mat_hang": "Khung",
        "don_vi_tinh": "cái", "tong_can": 20, "so_luong_con_dung": 5,
        "so_luong_thieu": 15, "so_yeu_cau": 2,
    }
    assert [row["linh_kien_thieu"][0]["so_luong_thieu"] for row in data["yeu_cau"]] == [5, 5]
    assert [row["linh_kien_thieu"][0]["so_luong_con_dung"] for row in data["yeu_cau"]] == [5, 5]


# UC-27 AC-3: Mốc kiểm tra đầu tăng dần, cùng mốc dùng id; không theo ngày tạo/gửi/hạn
async def test_oldest_first_check_then_id(api):
    api.stored.clear()
    for id_, checked_day, created_day in [(8, 12, 1), (4, 10, 3), (2, 10, 5)]:
        api.stored[id_] = request_record(
            id_, kiem_tra_lan_dau_at=NOW.replace(day=checked_day),
            created_at=NOW.replace(day=created_day), gui_at=NOW.replace(day=created_day + 1),
            han_hoan_thanh=date(2026, 12, created_day),
        )
        api.needs[id_] = {2: 10}
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]["yeu_cau"]] == [2, 4, 8]


# UC-27 AC-3: Repository thật lọc đúng trạng thái, ORDER BY D1 ASC và id ASC, không khóa/phân trang
async def test_repository_waiting_sql_filters_orders_and_maps_records():
    session = AsyncMock(spec=AsyncSession)
    records = Mock()
    records.all.return_value = [request_record(2), request_record(4)]
    session.scalars.return_value = records
    result = await SqlAlchemyYeuCauSanXuatRepository(session).yeu_cau_cho_bo_sung()
    assert result == [request_record(2), request_record(4)]
    statement = sql(session.scalars.call_args.args[0])
    assert statement.split(" WHERE ")[1] == (
        '"YeuCauSanXuat".trang_thai = \'cho_bo_sung_linh_kien\' '
        'ORDER BY "YeuCauSanXuat".kiem_tra_lan_dau_at ASC, "YeuCauSanXuat".id ASC'
    )
    assert 'FROM "YeuCauSanXuat"' in statement
    assert "FOR UPDATE" not in statement and "FOR SHARE" not in statement
    assert "LIMIT" not in statement and "OFFSET" not in statement
    assert session.scalars.await_count == 1


# UC-27 D3: Đã đủ vẫn trong danh sách, so sánh cả bằng và lớn hơn nhu cầu
@pytest.mark.parametrize("remaining", [10, 12, 25])
async def test_replenished_requests_remain_without_missing_lines(api, remaining):
    api.available[2] = replace(FRAME, so_luong_con_dung=remaining)
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [row["id"] for row in data["yeu_cau"]] == [1, 2]
    assert [row["linh_kien_thieu"] for row in data["yeu_cau"]] == [[], []]
    assert [row["da_du"] for row in data["yeu_cau"]] == [True, True]
    assert data["tong_hop"][0]["so_luong_thieu"] == max(0, 20 - remaining)
    assert data["tong_hop"][0]["so_yeu_cau"] == 2
    assert [row.trang_thai for row in api.stored.values()] == ["cho_bo_sung_linh_kien"] * 2


# UC-27 D4: Hàm thuần giữ dòng thiếu 0, đếm đúng số yêu cầu, sắp thiếu giảm dần rồi mã
def test_pure_summary_keeps_zero_shortages_and_orders_by_shortage_then_code():
    records = [request_record(), request_record(2)]
    needs = {1: {2: 10, 3: 2, 4: 8, 6: 1}, 2: {2: 10, 3: 3, 4: 2}}
    available = {
        2: FRAME, 3: HangKhaDung("MH-000003", "Bánh", "cái", 6),
        4: HangKhaDung("MH-000001", "Xích", "bộ", 10),
        6: HangKhaDung("MH-000006", "Ốc", "cái", 0),
    }
    before = deepcopy((records, needs, available))
    result = tong_hop_nhu_cau_bo_sung(records, needs, available)
    assert [(row.mat_hang_id, row.tong_can, row.so_luong_con_dung,
             row.so_luong_thieu, row.so_yeu_cau) for row in result.tong_hop] == [
        (2, 20, 0, 20, 2), (6, 1, 0, 1, 1), (4, 10, 10, 0, 2), (3, 5, 6, 0, 2),
    ]
    assert [[line.mat_hang_id for line in row.linh_kien_thieu] for row in result.yeu_cau] == [[2, 6], [2]]
    assert (records, needs, available) == before


# UC-27 D5: Mỗi yêu cầu trả đủ metadata, số sản xuất đã chốt và cả hai loại yêu cầu
async def test_request_metadata_uses_finalized_production_quantity(api):
    api.stored[2] = request_record(
        2, loai_yeu_cau="nhap_kho", so_luong=10, so_luong_dung_thanh_pham=0,
        nhan_vien_duoc_giao_id=22,
    )
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    for row in response.json()["data"]["yeu_cau"]:
        expected = api.stored[row["id"]].model_dump(mode="json", include={
            "id", "ma_yeu_cau_san_xuat", "mat_hang_id", "loai_yeu_cau",
            "so_luong_can_san_xuat", "han_hoan_thanh", "nhan_vien_duoc_giao_id",
            "kiem_tra_lan_dau_at",
        })
        assert {key: value for key, value in row.items()
                if key not in {"da_du", "linh_kien_thieu"}} == expected
    assert api.stored[1].so_luong != api.stored[1].so_luong_can_san_xuat


# UC-27 A1: Không yêu cầu chờ trả hai mảng rỗng, 200; không đọc nhu cầu hoặc khả dụng
async def test_empty_waiting_list_returns_empty_arrays(api):
    api.stored.clear()
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    assert response.json()["data"] == {"yeu_cau": [], "tong_hop": []}
    assert api.repo.mock_calls == [call.yeu_cau_cho_bo_sung()]
    assert tong_hop_nhu_cau_bo_sung([], api.needs, api.available).model_dump() == {
        "yeu_cau": [], "tong_hop": [],
    }


# UC-27 AC-2: ASGI GET không thay dữ liệu, không gọi audit/transaction/khóa; chỉ ba lần đọc
async def test_get_is_read_only_without_audit_transaction_or_locks(api):
    before = deepcopy((api.stored, api.needs, api.available))
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    assert "etag" not in response.headers
    assert (api.stored, api.needs, api.available) == before
    assert_no_writes(api)


# UC-27 AC-2: Gọi service trực tiếp vẫn chỉ đọc, trả meta tương quan đã truyền vào
async def test_service_is_read_only_and_preserves_request_id(api):
    before = deepcopy((api.stored, api.needs, api.available))
    result = await api.service.xem_nhu_cau_bo_sung(MANAGER, "uc27-read")
    assert result.meta.request_id == "uc27-read"
    assert result.data.tong_hop[0].so_luong_thieu == 20
    assert (api.stored, api.needs, api.available) == before
    assert_no_writes(api)


# UC-27 AC-2: Endpoint chỉ GET, mọi phương thức ghi trả 405 trước khi đọc nghiệp vụ
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_write_methods_are_not_allowed(api, method):
    response = await api.client.request(method, URL, json={})
    assert response.status_code == 405, response.text
    assert response.headers["allow"] == "GET"
    assert api.repo.mock_calls == [] and api.audit.mock_calls == []
    assert api.session.mock_calls == []


# UC-27 D2: NV và Admin bị chặn 403, chưa đăng nhập 401
@pytest.mark.parametrize("role,status", [("nhan_vien", 403), ("quan_tri_vien", 403), ("anonymous", 401)])
async def test_endpoint_permissions(api, role, status):
    response = await api.client.get(URL, headers={"x-role": role})
    assert response.status_code == status, response.text
    assert "error" in response.json()
    assert api.repo.mock_calls == []


# UC-27 D2: Service cũng kiểm quyền trước mọi lần đọc, không chỉ dựa vào router
@pytest.mark.parametrize("roles", [["nhan_vien"], ["quan_tri_vien"], []])
async def test_service_rejects_non_manager(api, roles):
    with pytest.raises(ForbiddenException):
        await api.service.xem_nhu_cau_bo_sung({"sub": "20", "roles": roles}, "uc27-denied")
    assert api.repo.mock_calls == []


# UC-27 D2: Không nhận bộ lọc, sort hoặc phân trang; query lạ trả 422
@pytest.mark.parametrize("params", [{"sort": "id"}, {"page": 1}, {"trang_thai": "da_gui"}])
async def test_endpoint_rejects_query_parameters(api, params):
    response = await api.client.get(URL, params=params)
    assert response.status_code == 422, response.text
    assert api.repo.mock_calls == []


# UC-27 D2: Router mới được đăng ký ở ứng dụng thật, không chỉ ứng dụng test
def test_main_registers_only_get_for_shortages():
    from app.main import app

    operations = app.openapi()["paths"][URL]
    assert set(operations) == {"get"}
    assert "parameters" not in operations["get"]


# UC-27 D4: Nhu cầu của mọi trạng thái khác bị loại và không đọc khả dụng linh kiện riêng của chúng
async def test_other_states_never_contribute_to_shortages(api):
    for id_, state in enumerate(["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"], 3):
        api.stored[id_] = request_record(id_, trang_thai=state)
        api.needs[id_] = {2: 1000, 99: 500}
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert [row["id"] for row in data["yeu_cau"]] == [1, 2]
    assert len(data["tong_hop"]) == 1
    assert (data["tong_hop"][0]["tong_can"], data["tong_hop"][0]["so_yeu_cau"]) == (20, 2)
    api.repo.nhu_cau_cua_cac_yeu_cau.assert_awaited_once_with([1, 2])
    api.repo.kha_dung.assert_awaited_once_with([2], lock=False)


# UC-27 D3: Lần đọc sau dùng còn dùng được hiện tại, không dùng cache lần kiểm tra trước
async def test_next_read_uses_current_availability(api):
    first = await api.client.get(URL)
    assert first.status_code == 200
    assert first.json()["data"]["tong_hop"][0]["so_luong_thieu"] == 20
    api.available[2] = replace(FRAME, so_luong_con_dung=20)
    second = await api.client.get(URL)
    assert second.status_code == 200
    assert second.json()["data"]["tong_hop"][0]["so_luong_thieu"] == 0
    assert [row["da_du"] for row in second.json()["data"]["yeu_cau"]] == [True, True]


# UC-27 D4: Repository thật đọc nhu cầu theo lô và tái sử dụng khả dụng hiện tại, không khóa
async def test_repository_reads_batched_needs_and_unlocked_availability():
    session = AsyncMock(spec=AsyncSession)
    repo = SqlAlchemyYeuCauSanXuatRepository(session)
    session.execute.return_value = [(1, 2, 10), (1, 9, 20), (4, 2, 8)]
    assert await repo.nhu_cau_cua_cac_yeu_cau([1, 4]) == {1: {2: 10, 9: 20}, 4: {2: 8}}
    needs_sql = sql(session.execute.call_args.args[0])
    assert 'FROM "NhuCauLinhKien"' in needs_sql
    assert needs_sql.split(" WHERE ")[1] == (
        '"NhuCauLinhKien".yeu_cau_san_xuat_id IN (1, 4) '
        'ORDER BY "NhuCauLinhKien".yeu_cau_san_xuat_id, "NhuCauLinhKien".mat_hang_id'
    )
    session.execute.return_value = [SimpleNamespace(
        id=2, ma_mat_hang="MH-000002", ten_mat_hang="Khung", don_vi_tinh="cái",
        so_luong_con_dung=5,
    )]
    assert await repo.kha_dung([2], lock=False) == {2: replace(FRAME, so_luong_con_dung=5)}
    availability_sql = sql(session.execute.call_args.args[0])
    assert '"MatHang".so_luong_con_dung' in availability_sql
    assert availability_sql.endswith('WHERE "MatHang".id IN (2) ORDER BY "MatHang".id')
    for statement in (needs_sql, availability_sql):
        assert "FOR UPDATE" not in statement and "FOR SHARE" not in statement
    assert session.execute.await_count == 2


# UC-27 D2: Endpoint mới dùng cùng envelope lỗi hợp đồng như các endpoint sản xuất khác
def test_shortage_path_uses_contract_error_envelope():
    from starlette.requests import Request

    from app.config.settings import settings
    from app.core.exceptions import _uses_contract_envelope

    def request(path):
        return Request({"type": "http", "method": "GET", "path": path, "headers": [], "query_string": b""})

    prefix = settings.api_v1_str
    assert _uses_contract_envelope(request(f"{prefix}/nhu_cau_bo_sung_linh_kien"))
    assert _uses_contract_envelope(request(f"{prefix}/yeu_cau_san_xuat"))
    assert not _uses_contract_envelope(request(f"{prefix}/nhu_cau_bo_sung_linh_kien_khac"))
