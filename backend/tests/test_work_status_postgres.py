"""Employee work labels follow real document transitions and SQL pagination."""

import pytest


@pytest.mark.parametrize("kind", ["xuat_giao", "nhap_kho"])
async def test_work_labels_follow_documents_without_changing_draft_workflow(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, kind,
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source(kind=kind, state="cho_bo_sung_linh_kien")
    request_path = f"/api/v1/yeu_cau_san_xuat/{source}"

    async def work(expected):
        detail = await client.get(request_path, headers=auth())
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["trang_thai_cong_viec"] == expected
        listing = await client.get("/api/v1/yeu_cau_san_xuat", headers=auth(), params={
            "trang_thai_cong_viec": expected, "page_size": 1,
        })
        assert listing.status_code == 200, listing.text
        assert listing.json()["meta"]["total"] == 1
        assert listing.json()["data"][0]["id"] == source
        return detail.headers["etag"]

    async def transition(path, action, response, actor=2):
        result = await client.post(path + action, headers={
            **auth(actor), "If-Match": response.headers["etag"],
        }, json={})
        assert result.status_code == 200, result.text
        return result

    assigned_etag = await work("da_giao")
    issue = await client.post("/api/v1/phieu_xuat", headers=auth(), json={
        "loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source,
    })
    assert issue.status_code == 201, issue.text
    assert await work("da_giao") == assigned_etag
    path = issue.headers["location"]
    pending = await transition(path, "/gui", issue)
    assert await work("cho_duyet_xuat_linh_kien") == assigned_etag
    await transition(path, "/duyet", pending, actor=1)
    ready_etag = await work("san_sang_san_xuat")
    started = await client.post(request_path + "/bat_dau", headers={
        **auth(), "If-Match": ready_etag,
    }, json={})
    assert started.status_code == 200, started.text
    await work("dang_san_xuat")

    completion = await client.post("/api/v1/chung_tu_hoan_thanh_sx", headers=auth(), json={
        "yeu_cau_san_xuat_id": source,
    })
    assert completion.status_code == 201, completion.text
    await work("dang_san_xuat")
    completion_path = completion.headers["location"]
    pending = await transition(completion_path, "/gui", completion)
    await work("cho_duyet_hoan_thanh")
    await transition(completion_path, "/duyet", pending, actor=1)
    if kind == "xuat_giao":
        await work("cho_lap_phieu_xuat")
        issue = await client.post("/api/v1/phieu_xuat", headers=auth(), json={
            "loai_phieu": "xuat_thanh_pham", "yeu_cau_san_xuat_id": source,
        })
        assert issue.status_code == 201, issue.text
        await work("cho_lap_phieu_xuat")
        path = issue.headers["location"]
        pending = await transition(path, "/gui", issue)
        await work("cho_duyet_phieu_xuat")
        await transition(path, "/duyet", pending, actor=1)
    await work("hoan_thanh")

    manager = await client.get(request_path, headers=auth(1))
    assert "trang_thai_cong_viec" not in manager.json()["data"]
    forbidden = await client.get(request_path, headers=auth(3))
    assert forbidden.status_code == 403


async def test_finished_stock_and_cancelled_labels_are_filtered_before_pagination(
    goods_issue_client, goods_issue_auth, goods_issue_scenario,
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    sources = [await scenario.source(production=0, available=7) for _ in range(3)]
    other = await scenario.source(production=0, available=7, assigned=3)
    cancelled = await scenario.source(production=0, available=7)
    await scenario.sql('''UPDATE "YeuCauSanXuat" SET trang_thai='da_huy',
        huy_at=now(),nguoi_huy_id=1,ly_do_huy='Test' WHERE id=:id''', id=cancelled)
    for page in (1, 2, 3):
        result = await client.get("/api/v1/yeu_cau_san_xuat", headers=auth(), params={
            "trang_thai_cong_viec": "cho_lap_phieu_xuat", "page_size": 1, "page": page,
        })
        assert result.status_code == 200, result.text
        assert result.json()["meta"]["total"] == 3
        assert result.json()["data"][0]["id"] == sources[-page]
        assert result.json()["data"][0]["id"] != other
    result = await client.get(f"/api/v1/yeu_cau_san_xuat/{cancelled}", headers=auth())
    assert result.json()["data"]["trang_thai_cong_viec"] == "da_huy"
