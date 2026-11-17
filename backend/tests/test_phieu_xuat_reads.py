"""Employee source lookup and preview against real PostgreSQL, without writes."""

import pytest

BASE = "/api/v1/phieu_xuat"


async def test_lookup_empty_existing_completed_and_no_writes(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source()
    url = f"{BASE}/theo_yeu_cau/{source}"
    assert (await client.get(url, headers=auth())).status_code == 200
    assert (await client.get(url, headers=auth())).json()["data"] == []
    created, _, source = await goods_issue_pending()
    await scenario.sql(
        "UPDATE \"YeuCauSanXuat\" SET trang_thai='hoan_thanh',completed_at=now() WHERE id=:id",
        id=source,
    )
    before = await scenario.snapshot()
    response = await client.get(f"{BASE}/theo_yeu_cau/{source}", headers=auth())
    assert response.status_code == 200, response.text
    assert response.json()["data"] == [
        {
            key: created.json()["data"][key]
            for key in ("id", "ma_phieu_xuat", "loai_phieu", "trang_thai")
        }
        | {"trang_thai": "cho_duyet"}
    ]
    assert await scenario.snapshot() == before


@pytest.mark.parametrize("kind", ["xuat_linh_kien", "xuat_thanh_pham"])
async def test_preview_matches_server_create_without_writing(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, kind
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source(production=7 if kind == "xuat_linh_kien" else 0, available=3)
    before = await scenario.snapshot()
    response = await client.get(
        f"{BASE}/xem_truoc/{source}", params={"loai_phieu": kind}, headers=auth()
    )
    assert response.status_code == 200, response.text
    lines = response.json()["data"]["chi_tiet"]
    assert lines and await scenario.snapshot() == before
    created = await client.post(
        BASE, headers=auth(), json={"loai_phieu": kind, "yeu_cau_san_xuat_id": source}
    )
    assert created.status_code == 201, created.text
    assert [
        {key: line[key] for key in ("mat_hang_id", "so_luong")}
        for line in created.json()["data"]["chi_tiet"]
    ] == lines
    assert (
        await client.get(f"{BASE}/xem_truoc/{source}", params={"loai_phieu": kind}, headers=auth())
    ).status_code == 409


async def test_read_permissions_validation_and_changed_source(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    source = await scenario.source()
    for suffix in (f"theo_yeu_cau/{source}", f"xem_truoc/{source}?loai_phieu=xuat_linh_kien"):
        url = f"{BASE}/{suffix}"
        assert (await client.get(url)).status_code == 401
        assert (await client.get(url, headers=auth(3))).status_code == 403
        assert (await client.get(url, headers=auth(4))).status_code == 403
    assert (await client.get(f"{BASE}/theo_yeu_cau/{source}", headers=auth(1))).status_code == 200
    assert (
        await client.get(f"{BASE}/xem_truoc/{source}?loai_phieu=xuat_linh_kien", headers=auth(1))
    ).status_code == 403
    for suffix in ("theo_yeu_cau/2147483648", "xem_truoc/2147483648?loai_phieu=xuat_linh_kien"):
        assert (await client.get(f"{BASE}/{suffix}", headers=auth())).status_code == 404
    for suffix in (
        f"theo_yeu_cau/{source}?extra=1",
        f"xem_truoc/{source}?loai_phieu=bad",
        f"xem_truoc/{source}?loai_phieu=xuat_linh_kien&extra=1",
        f"xem_truoc/{source}?loai_phieu=xuat_linh_kien&loai_phieu=xuat_linh_kien",
    ):
        assert (await client.get(f"{BASE}/{suffix}", headers=auth())).status_code == 422
    preview = await client.get(
        f"{BASE}/xem_truoc/{source}?loai_phieu=xuat_linh_kien", headers=auth()
    )
    assert preview.status_code == 200
    await scenario.sql(
        "UPDATE \"YeuCauSanXuat\" SET trang_thai='da_huy',huy_at=now(),nguoi_huy_id=1,ly_do_huy='Test cancellation' WHERE id=:id",
        id=source,
    )
    before = await scenario.snapshot()
    result = await client.post(
        BASE, headers=auth(), json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source}
    )
    assert result.status_code == 409
    assert await scenario.snapshot() == before
