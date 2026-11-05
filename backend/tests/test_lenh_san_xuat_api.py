"""Seven order APIs against real PostgreSQL in the disposable issue-test schema."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, event, inspect, text
from test_phieu_xuat_api import context as issue_context  # noqa: F401

from app.core.security import create_access_token, password_version
from app.modules.audit.service import AuditService
from app.modules.san_xuat.models import ChiTietLenhSanXuat, LenhSanXuat

BASE = "/api/v1/lenh_san_xuat"


async def test_order_mapping_matches_bootstrap_postgresql(context):
    async with context[3].connect() as connection:
        for model in (LenhSanXuat, ChiTietLenhSanXuat):
            table = model.__table__
            reflected = await connection.run_sync(
                lambda sync, name=table.name: {
                    "columns": inspect(sync).get_columns(name),
                    "pk": inspect(sync).get_pk_constraint(name),
                    "fks": inspect(sync).get_foreign_keys(name),
                    "checks": inspect(sync).get_check_constraints(name),
                    "indexes": inspect(sync).get_indexes(name),
                    "uniques": inspect(sync).get_unique_constraints(name),
                }
            )
            assert {column["name"] for column in reflected["columns"]} == set(table.columns.keys())
            for column in reflected["columns"]:
                declared = table.c[column["name"]]
                assert column["type"].compile(dialect=connection.dialect) == declared.type.compile(
                    dialect=connection.dialect
                )
                assert column["nullable"] == declared.nullable
                assert bool(column.get("identity")) == (declared.identity is not None)
                if declared.identity is not None:
                    assert column["identity"]["always"] == declared.identity.always
                elif declared.server_default is None:
                    assert column["default"] is None
                else:
                    assert column["default"].split("::", 1)[0] == str(declared.server_default.arg)
            assert reflected["pk"]["constrained_columns"] == [
                column.name for column in table.primary_key
            ]
            actual_fks = {
                (
                    tuple(fk["constrained_columns"]),
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                    fk["options"].get("deferrable"),
                    # PostgreSQL reflection omits the default INITIALLY IMMEDIATE.
                    fk["options"].get("initially", "IMMEDIATE"),
                )
                for fk in reflected["fks"]
            }
            expected_fks = {
                (
                    tuple(column.name for column in fk.columns),
                    fk.referred_table.name,
                    tuple(element.column.name for element in fk.elements),
                    fk.deferrable,
                    fk.initially,
                )
                for fk in table.foreign_key_constraints
            }
            assert actual_fks == expected_fks
            assert {item["name"] for item in reflected["checks"]} == {
                constraint.name
                for constraint in table.constraints
                if isinstance(constraint, CheckConstraint)
            }
            for index in table.indexes:
                actual = next(item for item in reflected["indexes"] if item["name"] == index.name)
                assert actual["column_names"] == [column.name for column in index.columns]
                assert actual["unique"] == index.unique
            assert {tuple(item["column_names"]) for item in reflected["uniques"]} == {
                tuple(column.name for column in constraint.columns)
                for constraint in table.constraints
                if isinstance(constraint, UniqueConstraint)
            }


async def test_orders_created_from_request_plan_are_readable_and_assignable(context):
    client, _, headers, _ = context
    request = await client.post(
        "/api/v1/yeu_cau_san_xuat",
        headers=headers(),
        json={"mat_hang_id": 1, "so_luong": 20, "nhan_vien_duoc_giao_id": 3},
    )
    assert request.status_code == 201, request.text
    url = request.headers["location"]
    preview = await client.post(url + "/tinh_ke_hoach", headers=headers(), json={})
    assert preview.status_code == 200, preview.text
    assert preview.json()["data"]["du_dieu_kien_gui"] is True
    sent = await client.post(
        url + "/gui",
        headers={**headers(), "If-Match": request.headers["etag"]},
        json={"ke_hoach_token": preview.json()["data"]["ke_hoach_token"]},
    )
    assert sent.status_code == 200, sent.text
    generated = sent.json()["data"]["ke_hoach"]["lenh"]
    assert generated
    listed = await call(
        context, "GET", params={"yeu_cau_san_xuat_id": request.json()["data"]["id"]}
    )
    assert {row["id"] for row in listed.json()["data"]} == {row["id"] for row in generated}
    for order in generated:
        detail = await call(context, "GET", f"/{order['id']}")
        assert detail.json()["data"] == order
    root = next(order for order in generated if order["lenh_san_xuat_cha_id"] is None)
    await call(
        context,
        "PATCH",
        f"/{root['id']}",
        etag=await version(context, root["id"]),
        json={"nhan_vien_id": 3},
    )
    await call(context, "GET", f"/{root['id']}", actor=3)


@pytest.fixture
async def context(issue_context):  # noqa: F811 -- pytest injects the imported isolated DB fixture.
    client, sessions, headers, engine = issue_context
    async with sessions.begin() as session:
        for order_id, employee, status in [
            (201, None, "nhap"),
            (202, 3, "da_gui"),
            (203, 5, "da_gui"),
        ]:
            await session.execute(
                text("""INSERT INTO "LenhSanXuat" (id,ma_lenh_san_xuat,yeu_cau_san_xuat_id,mat_hang_id,bom_id,so_luong,nhan_vien_id,trang_thai,created_at)
                VALUES (:id,:code,100,1,1,2,:employee,:status,'2026-11-04T00:30:00Z')"""),
                {
                    "id": order_id,
                    "code": f"LSX-202611-{order_id:06}",
                    "employee": employee,
                    "status": status,
                },
            )
            await session.execute(
                text(
                    'INSERT INTO "ChiTietLenhSanXuat" (lenh_san_xuat_id,mat_hang_id,so_luong_can) VALUES (:id,8,4)'
                ),
                {"id": order_id},
            )
    return issue_context


async def call(context, method, suffix="", expected=200, actor=2, etag=None, **kwargs):
    client, _, headers, _ = context
    auth = headers(actor)
    if etag is not None:
        auth["If-Match"] = etag
    response = await client.request(method, BASE + suffix, headers=auth, **kwargs)
    assert response.status_code == expected, response.text
    return response


async def version(context, order_id=201, actor=2):
    return (await call(context, "GET", f"/{order_id}", actor=actor)).headers["etag"]


async def scalar(context, sql, **params):
    async with context[1]() as session:
        return await session.scalar(text(sql), params)


async def mutate(context, sql, **params):
    async with context[1].begin() as session:
        await session.execute(text(sql), params)


async def stock_state(context):
    async with context[1]() as session:
        return (
            (
                await session.execute(
                    text('SELECT id,so_luong_ton,ton_kho_updated_at FROM "MatHang" ORDER BY id')
                )
            ).all(),
            await session.scalar(text('SELECT count(*) FROM "GiaoDichKho"')),
        )


async def supply(context, order_id=202, quantity=4):
    client, _, headers, _ = context
    created = await client.post(
        "/api/v1/phieu_xuat",
        headers=headers(),
        json={
            "loai_phieu": "xuat_vat_tu",
            "lenh_san_xuat_id": order_id,
            "chi_tiet": [{"mat_hang_id": 8, "so_luong": quantity}],
        },
    )
    assert created.status_code == 201, created.text
    url = created.headers["location"]
    sent = await client.post(
        url + "/gui", headers={**headers(), "If-Match": created.headers["etag"]}, json={}
    )
    assert sent.status_code == 200, sent.text
    approved = await client.post(
        url + "/duyet", headers={**headers(), "If-Match": sent.headers["etag"]}, json={}
    )
    assert approved.status_code == 200, approved.text
    return approved


async def test_list_scope_filters_and_read_do_not_change_stock(context):
    before = await stock_state(context)
    result = await call(
        context, "GET", params={"yeu_cau_san_xuat_id": 100, "sort": "id", "page_size": 2}
    )
    assert [row["id"] for row in result.json()["data"]] == [100, 201]
    assert result.json()["meta"]["total"] == 4
    worker = await call(context, "GET", actor=3, params={"yeu_cau_san_xuat_id": 100, "sort": "id"})
    assert [row["id"] for row in worker.json()["data"]] == [100, 202]
    empty = await call(context, "GET", actor=3, params={"nhan_vien_id": 5})
    assert empty.json()["data"] == []
    detail = await call(context, "GET", "/202", actor=3)
    assert detail.json()["data"]["nhu_cau_truc_tiep"][0]["so_luong_can"] == 4
    assert detail.headers["etag"].startswith('"')
    assert "request_id" in detail.json()["meta"]
    assert "mat_khau" not in detail.text
    assert await stock_state(context) == before


@pytest.mark.parametrize("path", ["/202", "/202/vat_tu"])
async def test_scope_not_found_and_roles(context, path):
    await call(context, "GET", path, actor=1, expected=403)
    await call(context, "GET", path, actor=5, expected=403)
    await call(context, "GET", path.replace("202", "2147483647"), actor=5, expected=404)


@pytest.mark.parametrize(
    "query",
    [
        {"page": 0},
        {"page_size": 101},
        {"sort": "bom_id"},
        {"trang_thai": "pending"},
        {"q": "x", "unknown": "x"},
        {"tu_ngay": "2026-11-05", "den_ngay": "2026-11-04"},
        {"den_ngay": "9999-12-31"},
        {"tu_ngay": "20261104"},
        {"nhan_vien_id": True},
        {"yeu_cau_san_xuat_id": 2**31},
    ],
)
async def test_invalid_queries(context, query):
    response = await call(context, "GET", params=query, expected=422)
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"


async def test_repeated_queries_and_detail_query(context):
    await call(context, "GET", "?sort=id&sort=-id", expected=422)
    await call(context, "GET", "/202?page=1", expected=422)
    await call(context, "GET", "/202/vat_tu?x=1", expected=422)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"nhan_vien_id": True},
        {"nhan_vien_id": "3"},
        {"nhan_vien_id": 0},
        {"nhan_vien_id": 1.5},
        {"nhan_vien_id": 3, "so_luong": 5},
        {"bom_id": 1},
        {"nhan_vien_id": 2**31},
    ],
)
async def test_patch_rejects_other_fields_and_bad_ids(context, body):
    await call(context, "PATCH", "/201", json=body, etag=await version(context), expected=422)


@pytest.mark.parametrize(
    "etag,expected", [(None, 428), ("", 428), ('"old"', 412), ("*", 412), ('W/"old"', 412)]
)
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("PATCH", "/201", {"nhan_vien_id": 3}),
        ("POST", "/201/gui", {}),
        ("POST", "/202/bat_dau", {}),
        ("POST", "/201/huy", {"ly_do": "Hủy thử"}),
    ],
)
async def test_write_preconditions(context, etag, expected, method, path, body):
    actor = 3 if "bat_dau" in path else 2
    await call(context, method, path, json=body, etag=etag, expected=expected, actor=actor)


async def test_assign_nullable_and_send_without_stock_requirement(context):
    before = await stock_state(context)
    original = (await call(context, "GET", "/201")).json()["data"]
    assigned = await call(
        context, "PATCH", "/201", json={"nhan_vien_id": 3}, etag=await version(context)
    )
    await call(context, "GET", "/201", actor=3)
    cleared = await call(
        context, "PATCH", "/201", json={"nhan_vien_id": None}, etag=assigned.headers["etag"]
    )
    await call(context, "GET", "/201", actor=3, expected=403)
    await call(context, "POST", "/201/gui", json={}, etag=cleared.headers["etag"], expected=409)
    assigned = await call(
        context, "PATCH", "/201", json={"nhan_vien_id": 3}, etag=cleared.headers["etag"]
    )
    # Stock is irrelevant to sending, and no material has yet been issued.
    sent = await call(context, "POST", "/201/gui", json={}, etag=assigned.headers["etag"])
    assert sent.json()["data"]["trang_thai"] == "da_gui"
    for field in ("bom_id", "mat_hang_id", "so_luong", "lenh_san_xuat_cha_id", "nhu_cau_truc_tiep"):
        assert sent.json()["data"][field] == original[field]
    await call(
        context,
        "PATCH",
        "/201",
        json={"nhan_vien_id": None},
        etag=sent.headers["etag"],
        expected=409,
    )
    await call(context, "POST", "/201/gui", json={}, etag=sent.headers["etag"], expected=409)
    assert await stock_state(context) == before


@pytest.mark.parametrize("employee,expected", [(1, 409), (2, 409), (4, 409), (9999, 404)])
async def test_invalid_assignee(context, employee, expected):
    await call(
        context,
        "PATCH",
        "/201",
        json={"nhan_vien_id": employee},
        etag=await version(context),
        expected=expected,
    )


async def test_start_requires_actual_approved_allocation_and_updates_request_only(context):
    first = await version(context, 202, actor=3)
    before = await stock_state(context)
    material = await call(context, "GET", "/202/vat_tu", actor=3)
    assert material.headers["etag"] == first
    assert material.json()["data"]["du_dieu_kien_bat_dau"] is False
    await call(context, "POST", "/202/bat_dau", actor=3, etag=first, json={}, expected=409)
    assert await stock_state(context) == before
    await supply(context, quantity=2)
    material = await call(context, "GET", "/202/vat_tu", actor=3)
    assert material.json()["data"]["chi_tiet"][0]["so_luong_da_cap"] == 2
    await call(
        context,
        "POST",
        "/202/bat_dau",
        actor=3,
        etag=material.headers["etag"],
        json={},
        expected=409,
    )
    await supply(context, quantity=2)
    material = await call(context, "GET", "/202/vat_tu", actor=3)
    assert material.json()["data"]["du_dieu_kien_bat_dau"] is True
    before = await stock_state(context)
    started = await call(
        context, "POST", "/202/bat_dau", actor=3, etag=material.headers["etag"], json={}
    )
    assert started.json()["data"]["trang_thai"] == "dang_thuc_hien"
    assert started.json()["data"]["started_at"].endswith("Z")
    assert (
        await scalar(
            context,
            """SELECT jsonb_array_length(du_lieu_sau->'lenh_san_xuat_ids') FROM "LichSuThaoTac" WHERE loai_doi_tuong='yeu_cau_san_xuat' AND doi_tuong_id=100 AND thao_tac='sua' ORDER BY id DESC LIMIT 1""",
        )
        == 4
    )
    assert (
        await scalar(context, 'SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=100')
        == "dang_thuc_hien"
    )
    assert await stock_state(context) == before
    await call(
        context,
        "POST",
        "/202/bat_dau",
        actor=3,
        etag=started.headers["etag"],
        json={},
        expected=409,
    )
    await call(
        context,
        "POST",
        "/202/huy",
        etag=started.headers["etag"],
        json={"ly_do": "Đã cấp"},
        expected=409,
    )


@pytest.mark.parametrize(
    "actor,path",
    [
        (1, "/201/gui"),
        (3, "/201/gui"),
        (1, "/201/huy"),
        (3, "/201/huy"),
        (2, "/202/bat_dau"),
        (5, "/202/bat_dau"),
    ],
)
async def test_action_roles_and_ownership(context, actor, path):
    await call(
        context,
        "POST",
        path,
        actor=actor,
        etag='"old"',
        json={"ly_do": "Hủy"} if path.endswith("huy") else {},
        expected=403,
    )


async def test_cancel_requires_reason_and_no_active_child_or_posting(context):
    await call(
        context, "POST", "/201/huy", json={"ly_do": "  "}, etag=await version(context), expected=422
    )
    await mutate(
        context,
        'INSERT INTO "ChiTietLenhSanXuat" (lenh_san_xuat_id,mat_hang_id,so_luong_can) VALUES (201,5,2)',
    )
    await mutate(
        context,
        """INSERT INTO "LenhSanXuat" (id,ma_lenh_san_xuat,yeu_cau_san_xuat_id,lenh_san_xuat_cha_id,mat_hang_id,bom_id,so_luong) VALUES (204,'LSX-202611-000204',100,201,5,5,2)""",
    )
    await call(
        context,
        "POST",
        "/201/huy",
        json={"ly_do": "Hủy cha"},
        etag=await version(context),
        expected=409,
    )
    child = await call(
        context,
        "POST",
        "/204/huy",
        json={"ly_do": "  Không còn nhu cầu  "},
        etag=await version(context, 204),
    )
    assert child.json()["data"]["trang_thai"] == "da_huy"
    before = await stock_state(context)
    canceled = await call(
        context, "POST", "/201/huy", json={"ly_do": "Hủy sau con"}, etag=await version(context)
    )
    assert canceled.json()["data"]["trang_thai"] == "da_huy"
    assert (
        await scalar(
            context,
            """SELECT ly_do FROM "LichSuThaoTac" WHERE loai_doi_tuong='lenh_san_xuat' AND doi_tuong_id=204 AND thao_tac='huy' """,
        )
        == "Không còn nhu cầu"
    )
    assert await stock_state(context) == before
    await call(
        context,
        "POST",
        "/100/huy",
        etag=await version(context, 100),
        json={"ly_do": "Đã ghi đầu ra"},
        expected=409,
    )


async def test_concurrent_send_same_version_writes_one_audit(context):
    assigned = await call(
        context, "PATCH", "/201", etag=await version(context), json={"nhan_vien_id": 3}
    )
    results = await asyncio.gather(
        *(
            context[0].post(
                BASE + "/201/gui",
                headers={**context[2](), "If-Match": assigned.headers["etag"]},
                json={},
            )
            for _ in range(2)
        )
    )
    assert sorted(result.status_code for result in results) == [200, 412]
    assert (
        await scalar(
            context,
            """SELECT count(*) FROM "LichSuThaoTac" WHERE loai_doi_tuong='lenh_san_xuat' AND doi_tuong_id=201 AND thao_tac='gui' """,
        )
        == 1
    )


async def test_audit_failure_rolls_back_assignment(context, monkeypatch):
    async def fail(*args, **kwargs):
        raise RuntimeError("injected audit failure")

    before = await version(context)
    monkeypatch.setattr(AuditService, "append", fail)
    await call(context, "PATCH", "/201", etag=before, json={"nhan_vien_id": 3}, expected=500)
    assert await scalar(context, 'SELECT nhan_vien_id FROM "LenhSanXuat" WHERE id=201') is None
    assert await version(context) == before


async def test_schema_auth_and_unsupported_methods(context):
    response = await context[0].get(BASE)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "chua_xac_thuc"
    await call(context, "POST", json={}, expected=405)
    await call(context, "POST", "/202/hoan_tat", json={}, expected=404)
    for suffix, methods in [
        ("", {"get"}),
        ("/{id}", {"get", "patch"}),
        ("/{id}/vat_tu", {"get"}),
        ("/{id}/gui", {"post"}),
        ("/{id}/bat_dau", {"post"}),
        ("/{id}/huy", {"post"}),
    ]:
        schema = (await context[0].get("/api/v1/openapi.json")).json()
        assert set(schema["paths"][BASE + suffix]) == methods


async def test_every_filter_and_local_day_boundaries(context):
    await mutate(
        context,
        """UPDATE "LenhSanXuat" SET created_at=CASE id WHEN 201 THEN '2026-11-03T17:00:00Z'::timestamptz WHEN 202 THEN '2026-11-04T16:59:59Z'::timestamptz ELSE '2026-11-04T17:00:00Z'::timestamptz END WHERE id IN (201,202,203)""",
    )
    result = await call(
        context,
        "GET",
        params={"q": "00020", "tu_ngay": "2026-11-04", "den_ngay": "2026-11-04", "sort": "id"},
    )
    assert [row["id"] for row in result.json()["data"]] == [201, 202]
    for query in [{"nhan_vien_id": 5}, {"trang_thai": "da_gui", "mat_hang_id": 1, "q": "000203"}]:
        result = await call(context, "GET", params=query)
        assert [row["id"] for row in result.json()["data"]] == [203]
    result = await call(context, "GET", params={"q": "%"})
    assert result.json()["data"] == []
    result = await call(
        context,
        "GET",
        params={"q": "00020", "sort": "-ma_lenh_san_xuat", "page": 2, "page_size": 2},
    )
    assert [row["id"] for row in result.json()["data"]] == [201]
    assert result.json()["meta"]["total_pages"] == 2
    result = await call(context, "GET", params={"page": 10**30})
    assert result.json()["data"] == []


async def test_current_database_role_active_and_password_version(context):
    # Forging a role claim never changes database authorization.
    response = await context[0].get(BASE, headers=context[2](3, roles=["quan_ly"]))
    assert response.status_code == 200
    assert all(row["nhan_vien_id"] == 3 for row in response.json()["data"])
    await mutate(context, """UPDATE "NhanVien" SET trang_thai='bi_khoa' WHERE id=3""")
    await call(context, "GET", "/202", actor=3, expected=403)
    await mutate(context, """UPDATE "NhanVien" SET trang_thai='hoat_dong' WHERE id=3""")
    invalid = create_access_token(3, roles=["nhan_vien"], credential_version="old-password-version")
    response = await context[0].get(BASE, headers={"Authorization": f"Bearer {invalid}"})
    assert response.status_code == 401
    hashed = await scalar(context, 'SELECT mat_khau FROM "NhanVien" WHERE id=3')
    expired = create_access_token(
        3,
        roles=["nhan_vien"],
        credential_version=password_version(hashed),
        expires_delta=timedelta(seconds=-1),
    )
    response = await context[0].get(BASE, headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    await mutate(context, """UPDATE "NhanVien" SET vai_tro_id=2 WHERE id=3""")
    response = await context[0].get(BASE, headers=context[2](3))
    assert any(row["id"] == 201 for row in response.json()["data"])


@pytest.mark.parametrize(
    "path,body",
    [
        ("/201/gui", {"x": 1}),
        ("/202/bat_dau", {"nhan_vien_id": 3}),
        ("/201/huy", {}),
        ("/201/huy", {"ly_do": None}),
    ],
)
async def test_action_body_and_queries_strict(context, path, body):
    await call(
        context,
        "POST",
        path,
        actor=3 if "bat_dau" in path else 2,
        json=body,
        etag=await version(context, 202 if "bat_dau" in path else 201),
        expected=422,
    )
    await call(
        context, "POST", path + "?x=1", actor=3 if "bat_dau" in path else 2, json={}, expected=422
    )


async def test_pending_issue_is_not_supplied_and_waiting_request_stays_waiting(context):
    client, _, headers, _ = context
    created = await client.post(
        "/api/v1/phieu_xuat",
        headers=headers(),
        json={
            "loai_phieu": "xuat_vat_tu",
            "lenh_san_xuat_id": 202,
            "chi_tiet": [{"mat_hang_id": 8, "so_luong": 4}],
        },
    )
    assert created.status_code == 201
    material = await call(context, "GET", "/202/vat_tu", actor=3)
    assert material.json()["data"]["chi_tiet"][0]["so_luong_da_cap"] == 0
    await supply(context)
    await mutate(
        context, """UPDATE "YeuCauSanXuat" SET trang_thai='cho_bo_sung_vat_tu' WHERE id=100"""
    )
    started = await call(
        context, "POST", "/202/bat_dau", actor=3, etag=await version(context, 202, 3), json={}
    )
    assert started.json()["data"]["trang_thai"] == "dang_thuc_hien"
    assert (
        await scalar(context, 'SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=100')
        == "cho_bo_sung_vat_tu"
    )


async def test_closed_request_invalid_assignee_and_repeated_headers(context):
    assigned = await call(
        context, "PATCH", "/201", etag=await version(context), json={"nhan_vien_id": 3}
    )
    await mutate(context, """UPDATE "NhanVien" SET trang_thai='bi_khoa' WHERE id=3""")
    await call(context, "POST", "/201/gui", etag=assigned.headers["etag"], json={}, expected=409)
    await mutate(context, """UPDATE "YeuCauSanXuat" SET trang_thai='da_huy' WHERE id=100""")
    await call(context, "POST", "/201/gui", etag=await version(context), json={}, expected=409)
    response = await context[0].patch(
        BASE + "/201",
        headers=[*context[2]().items(), ("If-Match", "a"), ("If-Match", "b")],
        json={"nhan_vien_id": None},
    )
    assert response.status_code == 422


async def test_concurrent_start_only_one_transition(context):
    await supply(context)
    token = await version(context, 202, 3)
    results = await asyncio.gather(
        *(
            context[0].post(
                BASE + "/202/bat_dau", headers={**context[2](3), "If-Match": token}, json={}
            )
            for _ in range(2)
        )
    )
    assert sorted(result.status_code for result in results) == [200, 412]
    assert (
        await scalar(
            context,
            """SELECT count(*) FROM "LichSuThaoTac" WHERE loai_doi_tuong='lenh_san_xuat' AND doi_tuong_id=202 AND thao_tac='bat_dau' """,
        )
        == 1
    )


async def test_commit_failure_rolls_back_order_request_and_audits(context):
    await supply(context)
    token = await version(context, 202, 3)
    before = await scalar(context, 'SELECT count(*) FROM "LichSuThaoTac"')

    def fail(connection):
        raise RuntimeError("injected commit failure")

    event.listen(context[3].sync_engine, "commit", fail)
    try:
        await call(context, "POST", "/202/bat_dau", actor=3, etag=token, json={}, expected=500)
    finally:
        event.remove(context[3].sync_engine, "commit", fail)
    assert await scalar(context, 'SELECT trang_thai FROM "LenhSanXuat" WHERE id=202') == "da_gui"
    assert await scalar(context, 'SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=100') == "da_gui"
    assert await scalar(context, 'SELECT count(*) FROM "LichSuThaoTac"') == before


async def test_started_order_completes_only_through_approved_output(context):
    await supply(context)
    await call(
        context, "POST", "/202/bat_dau", actor=3, etag=await version(context, 202, 3), json={}
    )
    client, _, headers, _ = context
    result = await client.post(
        "/api/v1/chung_tu_hoan_thanh_sx",
        headers=headers(3),
        json={
            "lenh_san_xuat_id": 202,
            "so_luong_hoan_thanh": 2,
            "finish_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert result.status_code == 201, result.text
    url = result.headers["location"]
    sent = await client.post(
        url + "/gui", headers={**headers(3), "If-Match": result.headers["etag"]}, json={}
    )
    assert sent.status_code == 200, sent.text
    result = await client.post(
        url + "/duyet", headers={**headers(), "If-Match": sent.headers["etag"]}, json={}
    )
    assert result.status_code == 200, result.text
    order = await call(context, "GET", "/202")
    assert order.json()["data"]["trang_thai"] == "hoan_thanh"
    assert order.json()["data"]["so_luong_da_hoan_thanh"] == 2
    assert order.json()["data"]["so_luong_con_phai_hoan_thanh"] == 0
