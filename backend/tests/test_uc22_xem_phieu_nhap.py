"""UC-22 manager-only receipt reads through ASGI, without a database."""

from copy import deepcopy

import pytest

from tests.test_uc20_phieu_nhap_nhap import URL, create_draft


# UC-22 AC-1: Danh sách có cả nháp và hoàn thành, phân biệt được trạng thái
async def test_ac1_list_distinguishes_draft_and_completed(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    completed = await api.client.post(
        created.headers["location"] + "/hoan_tat", json={},
        headers={"If-Match": created.headers["etag"]},
    )
    assert completed.status_code == 200, completed.text
    draft = await create_draft(api)
    before = deepcopy(api.data)
    response = await api.client.get(URL)
    assert response.status_code == 200, response.text
    assert {row["id"]: row["trang_thai"] for row in response.json()["data"]} == {
        created.json()["data"]["id"]: "hoan_thanh", draft.json()["data"]["id"]: "nhap",
    }
    assert response.json()["meta"]["total"] == 2
    assert api.data == before
    api.repo.begin_read_snapshot.assert_awaited_once()


@pytest.mark.parametrize("role", ["quan_tri_vien", "nhan_vien"])
@pytest.mark.parametrize("detail", [False, True])
# UC-22 AC-2: Quản trị viên và nhân viên bị chặn list/detail
async def test_ac2_non_manager_cannot_read_receipts(receipt_api, role, detail):
    api = receipt_api
    created = await create_draft(api)
    response = await api.client.get(
        created.headers["location"] if detail else URL, headers={"x-role": role},
    )
    assert response.status_code == 403, response.text
    api.repo.begin_read_snapshot.assert_not_awaited()
    api.repo.list_receipts.assert_not_awaited()
    api.repo.get_receipt.assert_not_awaited()
