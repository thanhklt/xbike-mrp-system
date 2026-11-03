"""The public audit service delegates writes and leaves transaction ownership to receipts."""

from typing import Annotated

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_audit_service
from app.main import app
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.schemas import CreationAudit
from app.modules.audit.service import AuditService
from app.modules.catalog.models import Part
from app.modules.inventory.models import StockMovement
from app.modules.phieu_nhap.models import GoodsReceiptNote, ReceiptItem
from tests.test_auth_api import auth_context as auth_context
from tests.test_phieu_nhap_actions import action_context as action_context
from tests.test_phieu_nhap_api import BASE, BODY
from tests.test_phieu_nhap_api import receipt_context as receipt_context


@pytest.mark.parametrize("fail", [False, True])
async def test_audit_service_delegates_write_and_propagates_failure(fail):
    entries = []

    class AuditRepository:
        async def append(self, entry):
            entries.append(entry)
            if fail:
                raise RuntimeError("injected audit failure")

    entry = CreationAudit(
        nhan_vien_id=2,
        loai_doi_tuong="phieu_nhap",
        doi_tuong_id=1,
        du_lieu_sau={"trang_thai": "nhap"},
    )
    service = AuditService(AuditRepository())
    if fail:
        with pytest.raises(RuntimeError, match="injected audit failure"):
            await service.append(entry)
    else:
        await service.append(entry)
    assert entries == [entry]


@pytest.mark.parametrize(
    "method,operation,status",
    [
        ("post", "tao", 201),
        ("patch", "sua", 200),
        ("delete", "xoa_nhap", 204),
        ("complete", "hoan_tat", 200),
    ],
)
@pytest.mark.parametrize("fail", [False, True])
async def test_receipt_routes_use_audit_service_in_same_transaction(
    action_context, method, operation, status, fail
):
    client, sessions, headers, record, etag = action_context
    observed = []

    class ObservedAuditService(AuditService):
        async def append(self, entry):
            observed.append(entry.thao_tac)
            await super().append(entry)
            if fail:
                raise RuntimeError("private audit service failure")

    def audit_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ObservedAuditService(SqlAlchemyAuditRepository(db))

    path = f"{BASE}/{record['id']}"
    if method == "post":
        url, verb, options = BASE, "post", {"json": BODY}
    elif method == "complete":
        url, verb, options = path + "/hoan_tat", "post", {"json": {}}
    elif method == "patch":
        url, verb, options = (
            path,
            "patch",
            {"json": {"chi_tiet": [{**BODY["chi_tiet"][0], "so_luong": 4}]}},
        )
    else:
        url, verb, options = path, "delete", {}
    app.dependency_overrides[get_audit_service] = audit_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as http:
            response = await http.request(
                verb, url, headers={**headers, "If-Match": etag}, **options
            )
        assert response.status_code == (500 if fail else status), response.text
        assert "private" not in response.text
    finally:
        app.dependency_overrides.pop(get_audit_service, None)
    assert observed == [operation]
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == (
            1 if fail else 2
        )
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == int(
            method == "complete" and not fail
        )
        assert (await db.get(Part, 1)).so_luong_ton == (
            3 if method == "complete" and not fail else 0
        )
        if fail:
            assert await db.scalar(select(func.count()).select_from(GoodsReceiptNote)) == 1
            assert await db.scalar(select(func.count()).select_from(ReceiptItem)) == 1
    if fail:
        detail = await client.get(path, headers=headers)
        assert detail.json()["data"] == record
        assert detail.headers["etag"] == etag


async def test_audit_read_endpoint_still_lists_receipt_history(action_context):
    client, _, headers, record, _ = action_context
    response = await client.get("/api/v1/audit", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["pagination"]["total_items"] == 1
    assert response.json()["data"][0]["doi_tuong_id"] == record["id"]
    assert response.json()["data"][0]["thao_tac"] == "tao"
