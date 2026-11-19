"""UC-34..40 HTTP/auth contract using actual PostgreSQL v4 and dependencies."""

import json
import os
from pathlib import Path

import pytest

BASE = "/api/v1/phieu_xuat"


async def test_uc34_uc35_gi_ac03_08_14_17_component_lifecycle(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    initial = await scenario.snapshot()
    created, pending, source = await goods_issue_pending()
    draft = created.json()["data"]
    assert created.headers["location"] == f"{BASE}/{draft['id']}"
    assert [(line["mat_hang_id"], line["so_luong"]) for line in draft["chi_tiet"]] == list(
        zip(scenario.component_ids, (7, 14), strict=True)
    )
    assert draft["tong_tien"] is None and all(
        line["don_gia_thuc"] is None for line in draft["chi_tiet"]
    )
    assert draft["nhan_vien_id"] == 2 and "lenh_san_xuat_id" not in draft
    assert draft["created_at"].endswith("Z") and draft["updated_at"].endswith("Z")
    before = await scenario.snapshot()
    assert before["GiaoDichKho"] == initial["GiaoDichKho"]
    assert [row["so_luong_ton"] for row in before["MatHang"]] == [100, 100, 100]
    await scenario.sql(
        'UPDATE "MatHang" SET don_gia=20000 WHERE id=:id', id=scenario.component_ids[0]
    )
    approved = await client.post(
        created.headers["location"] + "/duyet",
        headers={**auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert approved.status_code == 200, approved.text
    resource = approved.json()["data"]
    assert resource["trang_thai"] == "da_duyet" and resource["tong_tien"] == 210000
    assert resource["nguoi_xu_ly_id"] == 1 and resource["phien_ban"] == 3
    after = await scenario.snapshot()
    assert [(row["so_luong_ton"], row["so_luong_dang_giu"]) for row in after["MatHang"]] == [
        (93, 0),
        (86, 0),
        (100, 0),
    ]
    assert [row["so_luong_ton_sau"] for row in after["GiaoDichKho"][-2:]] == [93, 86]
    assert all(
        row["trang_thai"] == "da_xuat" and row["phieu_xuat_id"] == draft["id"]
        for row in after["GiuHang"]
    )
    assert (
        next(row for row in after["YeuCauSanXuat"] if row["id"] == source)["trang_thai"]
        == "dang_thuc_hien"
    )
    assert [
        (row["thao_tac"], row["trang_thai_truoc"], row["trang_thai_sau"])
        for row in after["LichSuThaoTac"]
    ] == [("tao", None, "nhap"), ("gui", "nhap", "cho_duyet"), ("duyet", "cho_duyet", "da_duyet")]
    await scenario.sql('UPDATE "MatHang" SET don_gia=1 WHERE id=:id', id=scenario.component_ids[0])
    replay_before = await scenario.snapshot()
    replay = await client.post(
        created.headers["location"] + "/duyet",
        headers={**auth(1), "If-Match": created.headers["etag"]},
        json={},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == {**resource, "da_ghi_so_truoc_do": True}
    assert replay.headers["etag"] == approved.headers["etag"]
    assert await scenario.snapshot() == replay_before
    if output := os.getenv("GOODS_ISSUE_HTTP_EVIDENCE"):
        # An explicit artifact path contains only request bodies and safe response data, never JWT.
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(
            json.dumps(
                {
                    "uc": ["UC-34", "UC-35"],
                    "create": {
                        "request": {"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source},
                        "status": 201,
                        "location": created.headers["location"],
                        "etag": created.headers["etag"],
                        "response": created.json(),
                    },
                    "submit": {
                        "request": {},
                        "status": 200,
                        "etag": pending.headers["etag"],
                        "response": pending.json(),
                    },
                    "approve": {
                        "request": {},
                        "status": 200,
                        "etag": approved.headers["etag"],
                        "response": approved.json(),
                    },
                    "replay": {"status": 200, "response": replay.json()},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


@pytest.mark.parametrize("kind", ["xuat_linh_kien", "xuat_thanh_pham"])
async def test_uc36_uc39_gi_ac07_10_11_12_reject_resubmit(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending, kind
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    created, pending, _ = await goods_issue_pending(
        kind=kind, production=7, available=3 if kind == "xuat_thanh_pham" else 0
    )
    path = created.headers["location"]
    before = await scenario.snapshot()
    blank = await client.post(
        path + "/tu_choi",
        headers={**auth(1), "If-Match": pending.headers["etag"]},
        json={"ly_do": "  "},
    )
    assert blank.status_code == 422
    rejected = await client.post(
        path + "/tu_choi",
        headers={**auth(1), "If-Match": pending.headers["etag"]},
        json={"ly_do": "  Check receipt  "},
    )
    assert rejected.status_code == 200, rejected.text
    data = rejected.json()["data"]
    assert data["ly_do_tu_choi"] == "Check receipt" and data["nguoi_xu_ly_id"] == 1
    detail = await client.get(path, headers=auth())
    assert detail.json()["data"] == data and detail.headers["etag"] == rejected.headers["etag"]
    resent = await client.post(
        path + "/gui", headers={**auth(), "If-Match": rejected.headers["etag"]}, json={}
    )
    assert resent.status_code == 200, resent.text
    current = resent.json()["data"]
    assert current["phien_ban"] == 4 and current["trang_thai"] == "cho_duyet"
    assert (
        current["ly_do_tu_choi"] is None
        and current["nguoi_xu_ly_id"] is None
        and current["xu_ly_at"] is None
    )
    assert current["chi_tiet"] == pending.json()["data"]["chi_tiet"]
    stale = await client.post(
        path + "/duyet", headers={**auth(1), "If-Match": pending.headers["etag"]}, json={}
    )
    assert stale.status_code == 412
    after = await scenario.snapshot()
    for table in ("MatHang", "GiuHang", "GiaoDichKho", "YeuCauSanXuat"):
        assert after[table] == before[table]
    assert [row["thao_tac"] for row in after["LichSuThaoTac"]] == [
        "tao",
        "gui",
        "tu_choi",
        "gui_lai",
    ]
    assert after["LichSuThaoTac"][-1]["du_lieu_truoc"]["ly_do_tu_choi"] == "Check receipt"
    history = await client.get("/api/v1/audit?sort_order=asc", headers=auth(1))
    assert history.status_code == 200, history.text
    resent_audit = next(row for row in history.json()["data"] if row["thao_tac"] == "gui_lai")
    assert resent_audit["trang_thai_truoc"] == "tu_choi"
    assert resent_audit["trang_thai_sau"] == "cho_duyet"


@pytest.mark.parametrize("production,available", [(0, 10), (7, 3)])
async def test_uc37_uc38_gi_ac05_09_20_finished_goods(
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
    production,
    available,
):
    scenario = goods_issue_scenario
    created, pending, source = await goods_issue_pending(
        kind="xuat_thanh_pham", production=production, available=available
    )
    await scenario.sql('UPDATE "MatHang" SET is_active=false WHERE id=:id', id=scenario.output_id)
    approved = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["chi_tiet"][0]["so_luong"] == 10
    state = (await scenario.sql('SELECT * FROM "YeuCauSanXuat" WHERE id=:id', id=source))[0]
    assert (
        state["trang_thai"] == "hoan_thanh"
        and state["completed_at"] is not None
        and state["phien_ban"] == 2
    )
    item = (await scenario.sql('SELECT * FROM "MatHang" WHERE id=:id', id=scenario.output_id))[0]
    assert item["so_luong_ton"] == 90 and item["so_luong_dang_giu"] == 0
    audits = await scenario.sql('SELECT * FROM "LichSuThaoTac" ORDER BY id')
    assert [(row["loai_doi_tuong"], row["thao_tac"]) for row in audits][-2:] == [
        ("yeu_cau_san_xuat", "hoan_tat"),
        ("phieu_xuat", "duyet"),
    ]


async def test_uc34_uc40_gi_ac01_02_db_auth_scope(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    client, auth = goods_issue_client, goods_issue_auth
    created, _, source = await goods_issue_pending()
    path = created.headers["location"]
    for actor, expected in ((1, 200), (2, 403), (3, 403), (4, 403), (5, 403)):
        result = await client.get(BASE, headers=auth(actor))
        assert result.status_code == expected, result.text
    assert (await client.get(BASE)).status_code == 401
    assert (await client.get(path, headers=auth(2))).status_code == 200
    assert (await client.get(path, headers=auth(3))).status_code == 403
    assert (await client.get(path, headers=auth(4))).status_code == 403
    assert (await client.get(path, headers=auth(2, credential="old-hash"))).status_code == 401
    for actor in (1, 3, 4):
        result = await client.post(
            BASE,
            headers=auth(actor),
            json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source},
        )
        assert result.status_code == 403
    manager_send = await client.post(
        path + "/gui",
        headers={**auth(1), "If-Match": created.headers["etag"]},
        json={},
    )
    assert manager_send.status_code == 403
    # Role is read from DB even when the signed token claims admin.
    assert (
        await client.post(
            path + "/duyet",
            headers={**auth(2, roles=["quan_ly"]), "If-Match": created.headers["etag"]},
            json={},
        )
    ).status_code == 403


@pytest.mark.parametrize("production,available", [(0, 10), (7, 3)])
async def test_uc37_uc38_manager_creates_sends_and_approves_finished_goods(
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    production,
    available,
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source(production=production, available=available)
    await scenario.hold(source, scenario.output_id, available, "thanh_pham_co_san")
    payload = {"loai_phieu": "xuat_thanh_pham", "yeu_cau_san_xuat_id": source}
    if production:
        premature = await client.post(BASE, headers=auth(1), json=payload)
        assert premature.status_code == 409
        completion = await scenario.completion(source, production)
        await scenario.hold(source, scenario.output_id, production, "thanh_pham_san_xuat", completion)

    assert (await client.post(BASE, headers=auth(4), json=payload)).status_code == 403
    assert (await client.post(BASE, headers=auth(3), json=payload)).status_code == 403
    initial = await scenario.snapshot()
    created = await client.post(BASE, headers=auth(1), json=payload)
    assert created.status_code == 201, created.text
    path = created.headers["location"]
    draft = created.json()["data"]
    assert draft["nhan_vien_id"] == 1 and draft["trang_thai"] == "nhap"
    assert draft["chi_tiet"][0]["so_luong"] == 10
    assert (await client.post(BASE, headers=auth(1), json=payload)).status_code == 409
    assert (await client.post(path + "/gui", headers=auth(1), json={})).status_code == 428

    sent = await client.post(
        path + "/gui", headers={**auth(1), "If-Match": created.headers["etag"]}, json={}
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["data"]["trang_thai"] == "cho_duyet"
    pending = await scenario.snapshot()
    for table in ("MatHang", "GiuHang", "GiaoDichKho", "YeuCauSanXuat"):
        assert pending[table] == initial[table]

    approved = await client.post(
        path + "/duyet", headers={**auth(1), "If-Match": sent.headers["etag"]}, json={}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["trang_thai"] == "da_duyet"
    after = await scenario.snapshot()
    assert after["MatHang"][-1]["so_luong_ton"] == 90
    assert after["MatHang"][-1]["so_luong_dang_giu"] == 0
    request = next(row for row in after["YeuCauSanXuat"] if row["id"] == source)
    assert request["trang_thai"] == "hoan_thanh" and request["completed_at"] is not None
    assert len(after["GiaoDichKho"]) == len(initial["GiaoDichKho"]) + 1
    assert after["GiaoDichKho"][-1]["so_luong_bien_dong"] == -10
    assert [row["thao_tac"] for row in after["LichSuThaoTac"]] == ["tao", "gui", "hoan_tat", "duyet"]


@pytest.mark.parametrize(
    "extra",
    [
        {"chi_tiet": []},
        {"don_gia_thuc": 1},
        {"nhan_vien_id": 1},
        {"lenh_san_xuat_id": 1},
        {"trang_thai": "da_duyet"},
        {"ma_phieu_xuat": "PX-202611-000001"},
    ],
)
async def test_uc34_gi_ac03_06_forbid_client_content(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, extra
):
    source = await goods_issue_scenario.source()
    result = await goods_issue_client.post(
        BASE,
        headers=goods_issue_auth(),
        json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source, **extra},
    )
    assert result.status_code == 422
    assert await goods_issue_scenario.scalar('SELECT count(*) FROM "PhieuXuat"') == 0


async def test_uc40_gi_ac06_12_18_19_http_contract(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    created, pending, _ = await goods_issue_pending()
    path = created.headers["location"]
    before = await scenario.snapshot()
    for method in ("PATCH", "DELETE"):
        assert (await client.request(method, path, headers=auth())).status_code == 405
    assert (await client.post(path + "/ve_nhap", headers=auth(), json={})).status_code == 404
    for headers, status in (
        ({}, 428),
        ({"If-Match": " "}, 428),
        ({"If-Match": "*"}, 412),
        ({"If-Match": "W/" + pending.headers["etag"]}, 412),
        ({"If-Match": '"abc"'}, 412),
        ({"If-Match": '"' + "0" * 64 + '"'}, 412),
    ):
        result = await client.post(path + "/duyet", headers={**auth(1), **headers}, json={})
        assert result.status_code == status, result.text
    result = await client.post(
        path + "/duyet",
        headers=[
            *auth(1).items(),
            ("If-Match", pending.headers["etag"]),
            ("If-Match", pending.headers["etag"]),
        ],
        json={},
    )
    assert result.status_code == 412
    for query in (
        "page=0",
        "page_size=101",
        "q=a&q=b",
        "lenh_san_xuat_id=1",
        "sort=tong_tien",
        "tu_ngay=2026-02-30",
        "tu_ngay=2026-11-20&den_ngay=2026-11-01",
        "foo=bar",
    ):
        assert (await client.get(BASE + "?" + query, headers=auth(1))).status_code == 422
    assert (await client.get(path + "?foo=bar", headers=auth())).status_code == 422
    assert (await client.request("GET", path, headers=auth(), json={})).status_code == 422
    assert (await client.request("GET", BASE, headers=auth(1), json={})).status_code == 422
    for suffix in ("/0", "/2147483648", "/999999999999999999999999999"):
        assert (await client.get(BASE + suffix, headers=auth())).status_code == (
            422 if suffix == "/0" else 404
        )
    filtered = await client.get(
        BASE + "?loai_phieu=xuat_linh_kien&trang_thai=cho_duyet&nhan_vien_id=2&page_size=1",
        headers=auth(1),
    )
    assert filtered.status_code == 200 and filtered.json()["meta"]["total"] == 1
    assert filtered.json()["data"][0] == pending.json()["data"]
    assert "request_id" in filtered.json()["meta"]
    assert (await client.get(BASE + "?q=%25", headers=auth(1))).json()["data"] == []
    assert (await client.get(BASE + "?page=9999999999999999999999", headers=auth(1))).json()[
        "data"
    ] == []
    assert await scenario.snapshot() == before
