"""UC-21 ASGI acceptance and SQL contract checks without a database."""

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException
from app.modules.inventory.ports import StockReceiptLine
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from tests.test_uc20_phieu_nhap_nhap import create_draft


async def complete(api, created, tag=None):
    return await api.client.post(
        created.headers["location"] + "/hoan_tat", json={},
        headers={"If-Match": tag if tag is not None else created.headers["etag"]},
    )


# UC-21 AC-2: Hoàn tất cộng tồn 10 + 50 thành 60, ghi đúng dòng và tồn sau
async def test_ac2_completion_posts_exact_lines_and_balance(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    response = await complete(api, created)
    assert response.status_code == 200, response.text
    record = response.json()["data"]
    assert record["trang_thai"] == "hoan_thanh" and record["phien_ban"] == 2
    assert record["nguoi_hoan_thanh_id"] == 10 and record["hoan_thanh_at"]
    assert api.data["stock"][1] == 60
    lines, actor, at = api.inventory.receive_receipt.call_args.args
    assert lines == [StockReceiptLine(record["chi_tiet"][0]["id"], 1, 50)]
    assert actor == 10 and at.isoformat().replace("+00:00", "Z") == record["hoan_thanh_at"]
    movement = api.data["ledger"][0]
    assert movement["quantity"] == 50 and movement["balance"] == 60
    assert movement["source"] == record["chi_tiet"][0]["id"]
    assert record["giao_dich_kho_ids"] == [movement["id"]]
    assert record["da_ghi_so_truoc_do"] is False


# UC-21 AC-3: Gửi lại ETag nháp cũ chỉ cộng một lần
async def test_ac3_replay_accepts_old_draft_etag_without_second_posting(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    first = await complete(api, created)
    assert first.status_code == 200, first.text
    before = deepcopy(api.data)
    replay = await complete(api, created)
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == {**first.json()["data"], "da_ghi_so_truoc_do": True}
    assert replay.headers["etag"] == first.headers["etag"] != created.headers["etag"]
    api.inventory.receive_receipt.assert_awaited_once()
    api.inventory.lock_receipt_stock.assert_awaited_once()
    assert api.data == before and api.data["stock"][1] == 60


# UC-21 AC-4: Không gọi hoặc đổi yêu cầu sản xuất khi hoàn tất nhập
async def test_ac4_no_production_request_access_or_state_change(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    before = deepcopy(api.data["production"])
    response = await complete(api, created)
    assert response.status_code == 200, response.text
    assert api.data["production"] == before
    assert api.data["production"][7]["trang_thai"] == "cho_bo_sung_linh_kien"
    assert len(api.sql_calls) == 2
    assert api.sql_calls[0][0].startswith('UPDATE "MatHang"')
    assert api.sql_calls[1][0].startswith('INSERT INTO "GiaoDichKho"')
    assert [call[0] for call in api.repo.mock_calls] == [
        "lock_supplier", "lock_parts", "add_draft", "lock_receipt", "receipt_postings", "mark_completed",
    ]


# UC-21 AC-5: Phiếu bị sửa khi xác nhận trả 412, không ghi tồn
async def test_ac5_stale_confirmation_does_not_post_stock(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    changed = await api.client.patch(
        created.headers["location"], json={"ghi_chu": "Edited elsewhere"},
        headers={"If-Match": created.headers["etag"]},
    )
    assert changed.status_code == 200, changed.text
    before = deepcopy(api.data)
    response = await complete(api, created)
    assert response.status_code == 412, response.text
    assert response.json()["error"]["code"] == "du_lieu_da_thay_doi"
    assert api.data == before and api.data["stock"][1] == 10
    api.inventory.receive_receipt.assert_not_awaited()
    api.repo.mark_completed.assert_not_awaited()


# UC-21 R5: Audit hoàn tất lưu trạng thái nháp trước và hoàn thành sau
async def test_r5_completion_audit_records_actor_and_states(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    response = await complete(api, created)
    assert response.status_code == 200, response.text
    entry = api.data["audit"][-1]
    assert entry["thao_tac"] == "hoan_tat" and entry["nhan_vien_id"] == 10
    assert (entry["trang_thai_truoc"], entry["trang_thai_sau"]) == ("nhap", "hoan_thanh")
    assert entry["du_lieu_truoc"]["trang_thai"] == "nhap"
    assert entry["du_lieu_sau"]["trang_thai"] == "hoan_thanh"


# UC-21 R2: D6, UPDATE không có dòng báo xung đột trước khi INSERT ledger
async def test_d6_missing_update_result_is_conflict():
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    with pytest.raises(ConflictException):
        await SqlAlchemyInventoryRepository(session).receive_receipt(
            [StockReceiptLine(101, 1, 50)], 10, datetime.now(timezone.utc),
        )
    session.scalar.assert_awaited_once()
    assert str(session.scalar.call_args.args[0]).startswith('UPDATE "MatHang"')
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()


# UC-21 R2: D6, xung đột repository qua HTTP trả 409 và rollback trạng thái
async def test_d6_repository_conflict_rolls_back_completion(receipt_api):
    api = receipt_api
    created = await create_draft(api)
    before = deepcopy(api.data)
    api.session.scalar.side_effect = None
    api.session.scalar.return_value = None
    response = await complete(api, created)
    assert response.status_code == 409, response.text
    assert api.data == before
    api.session.rollback.assert_awaited_once()


@pytest.mark.parametrize("tag,status", [(None, 428), ("*", 412), ('"abc"', 412)])
# UC-21 R2: Gửi lại hoàn tất vẫn bắt buộc If-Match đúng định dạng
async def test_replay_still_requires_a_formatted_validator(receipt_api, tag, status):
    api = receipt_api
    created = await create_draft(api)
    assert (await complete(api, created)).status_code == 200
    before = deepcopy(api.data)
    response = await api.client.post(
        created.headers["location"] + "/hoan_tat", json={},
        headers={"If-Match": tag} if tag is not None else {},
    )
    assert response.status_code == status, response.text
    assert api.data == before
    api.inventory.receive_receipt.assert_awaited_once()
