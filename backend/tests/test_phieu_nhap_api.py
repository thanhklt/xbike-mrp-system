"""UC-20..22 / GR-AC HTTP integration with actual v4 PostgreSQL/auth dependencies."""

import json
import os
from pathlib import Path

import pytest

BASE = "/api/v1/phieu_nhap"


async def test_uc20_uc21_gr_ac04_07_08_09_11_17_18_receipt_lifecycle(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    client, auth, scenario = goods_receipt_client, goods_receipt_auth, goods_receipt_scenario
    before = await scenario.snapshot()
    created = await goods_receipt_draft()
    draft = created.json()["data"]
    assert created.headers["location"] == f"{BASE}/{draft['id']}"
    assert draft["tong_tien"] == 625000 and type(draft["chi_tiet"][0]["don_gia_thuc"]) is int
    assert draft["phien_ban"] == 1 and draft["nhan_vien_id"] == 1
    assert draft["hoan_thanh_at"] is None and draft["nguoi_hoan_thanh_id"] is None
    assert draft["created_at"].endswith("Z") and draft["updated_at"].endswith("Z")
    saved = await scenario.snapshot()
    for table in ("MatHang", "GiaoDichKho", "GiuHang", "YeuCauSanXuat", "NhuCauLinhKien"):
        assert saved[table] == before[table]
    assert saved["LichSuThaoTac"][-1]["trang_thai_sau"] == "nhap"
    complete = await client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**auth(2), "If-Match": created.headers["etag"]},
        json={},
    )
    assert complete.status_code == 200, complete.text
    data = complete.json()["data"]
    assert data["trang_thai"] == "hoan_thanh" and data["phien_ban"] == 2
    assert data["nguoi_hoan_thanh_id"] == 2 and data["hoan_thanh_at"].endswith("Z")
    assert data["nhan_vien_id"] == 1 and data["da_ghi_so_truoc_do"] is False
    after = await scenario.snapshot()
    item = next(row for row in after["MatHang"] if row["id"] == scenario.items[0])
    assert (
        item["so_luong_ton"],
        item["so_luong_dang_giu"],
        item["so_luong_con_dung"],
        item["don_gia"],
    ) == (60, 5, 55, 20000)
    ledger = after["GiaoDichKho"][-1]
    assert ledger["loai_giao_dich"] == "nhap_linh_kien" and ledger["so_luong_bien_dong"] == 50
    assert (
        ledger["so_luong_ton_sau"] == 60
        and ledger["chi_tiet_phieu_nhap_id"] == data["chi_tiet"][0]["id"]
    )
    assert data["giao_dich_kho_ids"] == [ledger["id"]]
    for table in ("GiuHang", "YeuCauSanXuat", "NhuCauLinhKien"):
        assert after[table] == before[table]
    assert [
        (row["thao_tac"], row["trang_thai_truoc"], row["trang_thai_sau"])
        for row in after["LichSuThaoTac"]
    ] == [("tao", None, "nhap"), ("hoan_tat", "nhap", "hoan_thanh")]
    replay = await client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**auth(2), "If-Match": created.headers["etag"]},
        json={},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == {**data, "da_ghi_so_truoc_do": True}
    assert replay.headers["etag"] == complete.headers["etag"]
    assert await scenario.snapshot() == after
    history = await client.get("/api/v1/audit", headers=auth())
    assert history.status_code == 200, history.text
    assert any(
        row["thao_tac"] == "hoan_tat" and row["trang_thai_sau"] == "hoan_thanh"
        for row in history.json()["data"]
    )
    if output := os.getenv("GOODS_RECEIPT_HTTP_EVIDENCE"):
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "uc": ["UC-20", "UC-21"],
                    "create": {
                        "request": scenario.payload(),
                        "status": 201,
                        "location": created.headers["location"],
                        "etag": created.headers["etag"],
                        "response": created.json(),
                    },
                    "complete": {
                        "request": {},
                        "status": 200,
                        "etag": complete.headers["etag"],
                        "response": complete.json(),
                    },
                    "replay": {"request": {}, "status": 200, "response": replay.json()},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


async def test_uc20_gr_ac05_06_10_patch_noop_aba_and_delete(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    client, auth, scenario = goods_receipt_client, goods_receipt_auth, goods_receipt_scenario
    created = await goods_receipt_draft()
    path = created.headers["location"]
    initial = await scenario.snapshot()
    noop = await client.patch(
        path, headers={**auth(), "If-Match": created.headers["etag"]}, json={}
    )
    assert noop.status_code == 200 and noop.headers["etag"] == created.headers["etag"]
    assert await scenario.snapshot() == initial
    changed = await client.patch(
        path,
        headers={**auth(2), "If-Match": created.headers["etag"]},
        json={"ghi_chu": "B", "ncc_id": scenario.suppliers[1]},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"]["phien_ban"] == 2
    restored = await client.patch(
        path,
        headers={**auth(), "If-Match": changed.headers["etag"]},
        json={"ghi_chu": "Fixture receipt", "ncc_id": scenario.suppliers[0]},
    )
    assert restored.status_code == 200 and restored.headers["etag"] != created.headers["etag"]
    stale = await client.post(
        path + "/hoan_tat", headers={**auth(), "If-Match": created.headers["etag"]}, json={}
    )
    assert stale.status_code == 412
    replaced = await client.patch(
        path,
        headers={**auth(), "If-Match": restored.headers["etag"]},
        json={
            "ghi_chu": None,
            "chi_tiet": [{"mat_hang_id": scenario.items[1], "so_luong": 3, "don_gia_thuc": 500}],
        },
    )
    assert replaced.status_code == 200, replaced.text
    data = replaced.json()["data"]
    assert data["ghi_chu"] is None and data["tong_tien"] == 1500 and data["phien_ban"] == 4
    assert [row["mat_hang_id"] for row in data["chi_tiet"]] == [scenario.items[1]]
    deleted = await client.delete(path, headers={**auth(), "If-Match": replaced.headers["etag"]})
    assert deleted.status_code == 204 and deleted.content == b""
    assert (await client.get(path, headers=auth())).status_code == 404
    after = await scenario.snapshot()
    for table in ("MatHang", "GiaoDichKho", "GiuHang", "YeuCauSanXuat", "NhuCauLinhKien"):
        assert after[table] == initial[table]
    audit = after["LichSuThaoTac"][-1]
    assert audit["thao_tac"] == "xoa_nhap" and audit["du_lieu_sau"] is None
    assert audit["trang_thai_truoc"] == "nhap" and audit["trang_thai_sau"] is None
    assert audit["du_lieu_truoc"]["ma_phieu_nhap"] == created.json()["data"]["ma_phieu_nhap"]
    recreated = await goods_receipt_draft()
    assert recreated.json()["data"]["ma_phieu_nhap"] > created.json()["data"]["ma_phieu_nhap"]


async def test_uc20_uc22_gr_ac01_all_routes_use_current_db_role(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    client, auth = goods_receipt_client, goods_receipt_auth
    created = await goods_receipt_draft()
    path = created.headers["location"]
    for actor in (3, 4, 5):
        headers = {**auth(actor, roles=["quan_ly"]), "If-Match": created.headers["etag"]}
        for method, url, body in (
            ("GET", BASE, None),
            ("GET", path, None),
            ("POST", BASE, goods_receipt_scenario.payload()),
            ("PATCH", path, {}),
            ("DELETE", path, None),
            ("POST", path + "/hoan_tat", {}),
        ):
            response = await client.request(
                method, url, headers=headers, **({"json": body} if body is not None else {})
            )
            assert response.status_code == 403, response.text
    missing = await client.get(BASE)
    assert missing.status_code == 401 and missing.headers["www-authenticate"] == "Bearer"
    assert (await client.get(BASE, headers=auth(1, credential="old-hash"))).status_code == 401
    assert (await client.get(BASE, headers=auth(1, roles=["nhan_vien"]))).status_code == 200


@pytest.mark.parametrize(
    "case,status",
    [
        ("money_string", 422),
        ("fractional", 422),
        ("bool", 422),
        ("overflow", 422),
        ("duplicate", 422),
        ("empty", 422),
        ("wrong_type", 409),
        ("missing_item", 404),
        ("missing_supplier", 404),
        ("actor", 422),
        ("code", 422),
        ("total", 422),
        ("state", 422),
        ("timestamp", 422),
        ("bad_date", 422),
    ],
)
async def test_uc20_gr_ac02_03_invalid_create_is_atomic(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, case, status
):
    scenario = goods_receipt_scenario
    payload = scenario.payload()
    if case in {"money_string", "fractional", "bool", "overflow"}:
        payload["chi_tiet"][0]["don_gia_thuc"] = {
            "money_string": "12500",
            "fractional": 1.5,
            "bool": True,
            "overflow": 2**63 - 1,
        }[case]
    elif case == "duplicate":
        payload["chi_tiet"].append(payload["chi_tiet"][0].copy())
    elif case == "empty":
        payload["chi_tiet"] = []
    elif case == "wrong_type":
        payload["chi_tiet"][0]["mat_hang_id"] = scenario.output
    elif case == "missing_item":
        payload["chi_tiet"][0]["mat_hang_id"] = 2147483647
    elif case == "missing_supplier":
        payload["ncc_id"] = 2147483647
    elif case == "bad_date":
        payload["ngay_nhap"] = "2026-02-30"
    else:
        payload[
            {
                "actor": "nhan_vien_id",
                "code": "ma_phieu_nhap",
                "total": "tong_tien",
                "state": "trang_thai",
                "timestamp": "hoan_thanh_at",
            }[case]
        ] = 1
    before = await scenario.snapshot()
    response = await goods_receipt_client.post(BASE, headers=goods_receipt_auth(), json=payload)
    assert response.status_code == status, response.text
    assert set(response.json()) == {"error", "meta"} and response.json()["meta"]["request_id"]
    assert await scenario.snapshot() == before


async def test_uc21_uc22_gr_ac10_11_16_22_http_contract(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    client, auth, scenario = goods_receipt_client, goods_receipt_auth, goods_receipt_scenario
    created = await goods_receipt_draft()
    path = created.headers["location"]
    before = await scenario.snapshot()
    for action in ("patch", "delete", "complete"):
        for tag, expected in (
            (None, 428),
            (" ", 428),
            ("*", 412),
            ("W/" + created.headers["etag"], 412),
            ('"abc"', 412),
            ('"' + "0" * 64 + '"', 412),
        ):
            headers = {**auth(), **({"If-Match": tag} if tag is not None else {})}
            method, url, body = (
                ("POST", path + "/hoan_tat", {})
                if action == "complete"
                else (action.upper(), path, {} if action == "patch" else None)
            )
            result = await client.request(
                method, url, headers=headers, **({"json": body} if body is not None else {})
            )
            assert result.status_code == expected, result.text
    repeated = await client.post(
        path + "/hoan_tat",
        headers=[
            *auth().items(),
            ("If-Match", created.headers["etag"]),
            ("If-Match", created.headers["etag"]),
        ],
        json={},
    )
    assert repeated.status_code == 412
    for query in (
        "page=0",
        "page_size=101",
        "q=a&q=b",
        "sort=tong_tien",
        "foo=bar",
        "tu_ngay=2026-02-30",
        "tu_ngay=2026-11-20&den_ngay=2026-11-01",
        "tu_ngay=2026-11-14T00:00:00Z",
    ):
        assert (await client.get(BASE + "?" + query, headers=auth())).status_code == 422
    for field in ("chi_tiet", "ncc_id", "ngay_nhap"):
        assert (
            await client.patch(
                path, headers={**auth(), "If-Match": created.headers["etag"]}, json={field: None}
            )
        ).status_code == 422
    for method, url in (("GET", BASE), ("GET", path), ("DELETE", path)):
        assert (
            await client.request(
                method, url, headers={**auth(), "If-Match": created.headers["etag"]}, json={}
            )
        ).status_code == 422
    assert (await client.get(path + "?foo=bar", headers=auth())).status_code == 422
    assert (
        await client.post(
            path + "/hoan_tat", headers={**auth(), "If-Match": created.headers["etag"]}
        )
    ).status_code == 422
    assert (await client.get(BASE + "/2147483648", headers=auth())).status_code == 404
    assert (await client.get(BASE + "/0", headers=auth())).status_code == 422
    assert (await client.get("/api/v1/receiving", headers=auth())).status_code == 404
    assert (await client.post(path + "/duyet", headers=auth(), json={})).status_code == 404
    assert await scenario.snapshot() == before


async def test_uc20_gr_ac06_completed_receipt_cannot_change(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    created = await goods_receipt_draft()
    path = created.headers["location"]
    complete = await goods_receipt_client.post(
        path + "/hoan_tat",
        headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]},
        json={},
    )
    assert complete.status_code == 200, complete.text
    before = await goods_receipt_scenario.snapshot()
    for method, body in (("PATCH", {"ghi_chu": "Changed"}), ("DELETE", None)):
        response = await goods_receipt_client.request(
            method,
            path,
            headers={**goods_receipt_auth(), "If-Match": complete.headers["etag"]},
            **({"json": body} if body else {}),
        )
        assert response.status_code == 409
    assert await goods_receipt_scenario.snapshot() == before


@pytest.mark.parametrize("price", [0, 2**63 - 1])
async def test_uc20_uc21_gr_ac02_08_money_boundaries_and_code_month(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft, price
):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    payload = goods_receipt_scenario.payload(quantity=1, price=price)
    payload["ngay_nhap"] = "2050-01-01"
    created = await goods_receipt_draft(payload)
    data = created.json()["data"]
    month = (
        datetime.fromisoformat(data["created_at"])
        .astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        .strftime("%Y%m")
    )
    assert data["ma_phieu_nhap"].startswith(f"PN-{month}-")
    assert data["ngay_nhap"] == "2050-01-01" and data["tong_tien"] == price
    result = await goods_receipt_client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]},
        json={},
    )
    assert result.status_code == 200, result.text
    assert result.json()["data"]["tong_tien"] == price
