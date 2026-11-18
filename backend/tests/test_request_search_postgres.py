"""UC-25 name/code search on real PostgreSQL, including role scope and pagination."""


async def test_product_search_ignores_case_accents_and_preserves_scope(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    await scenario.sql(
        'UPDATE "MatHang" SET ten_mat_hang=:name WHERE id=:id',
        name="Xe Đạp Địa Hình 100%_A/B",
        id=scenario.output_id,
    )
    own = await scenario.source()
    other = await scenario.source(assigned=3)
    draft = await scenario.source(state="nhap")
    url = "/api/v1/yeu_cau_san_xuat"
    before = await scenario.snapshot()
    for query in ("dia hinh", "ĐỊA HÌNH", "đạp", "  XE ĐẠP  ", "Địa Hình"):
        response = await client.get(url, headers=auth(), params={"q": query, "page_size": 1})
        assert response.status_code == 200, response.text
        result = response.json()
        # The scenario also contains one existing stock-production request assigned to this user.
        assert result["meta"]["total"] == 2 and result["meta"]["total_pages"] == 2
        second = await client.get(
            url, headers=auth(), params={"q": query, "page_size": 1, "page": 2}
        )
        ids = {row["id"] for row in result["data"] + second.json()["data"]}
        assert own in ids and other not in ids and draft not in ids
    manager = await client.get(url, headers=auth(1), params={"q": "DIA HINH"})
    assert manager.status_code == 200 and manager.json()["meta"]["total"] == 4
    record = await client.get(f"{url}/{own}", headers=auth())
    code = record.json()["data"]["ma_yeu_cau_san_xuat"]
    by_code = await client.get(url, headers=auth(), params={"q": code.lower()})
    assert [row["id"] for row in by_code.json()["data"]] == [own]
    assert await scenario.snapshot() == before


async def test_search_wildcards_are_literal_and_blank_query_is_unfiltered(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    client, auth, scenario = goods_issue_client, goods_issue_auth, goods_issue_scenario
    await scenario.sql(
        'UPDATE "MatHang" SET ten_mat_hang=:name WHERE id=:id',
        name="Xe 100%_A/B",
        id=scenario.output_id,
    )
    await scenario.source()
    url = "/api/v1/yeu_cau_san_xuat"
    baseline = (await client.get(url, headers=auth())).json()["meta"]["total"]
    for query, total in (
        ("%", baseline),
        ("_A/", baseline),
        ("%_A/B", baseline),
        ("100X", 0),
        ("__", 0),
        ("   ", baseline),
        ("'; DROP TABLE x; --", 0),
    ):
        response = await client.get(url, headers=auth(), params={"q": query})
        assert response.status_code == 200, response.text
        assert response.json()["meta"]["total"] == total, query
