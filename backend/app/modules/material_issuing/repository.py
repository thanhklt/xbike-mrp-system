"""SQLAlchemy persistence for material_issuing; no commit or business policy."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.material_issuing.models import MaterialIssueItem, MaterialIssueRequest
from app.modules.material_issuing.schemas import (
    MaterialIssueRequestCreate,
    MaterialIssueRequestResponse,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyMaterialIssuingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[MaterialIssueRequestResponse]:
        return await select_page(
            self.session,
            MaterialIssueRequest,
            MaterialIssueRequestResponse,
            params,
            MaterialIssueRequest.loai_phieu == "xuat_vat_tu",
        )

    async def get_by_id(self, record_id: int) -> MaterialIssueRequestResponse | None:
        return await select_by_id(
            self.session,
            MaterialIssueRequest,
            MaterialIssueRequestResponse,
            record_id,
            MaterialIssueRequest.loai_phieu == "xuat_vat_tu",
        )

    async def add(
        self, payload: MaterialIssueRequestCreate, *, created_at: datetime
    ) -> CreatedRecord[MaterialIssueRequestResponse]:
        record = MaterialIssueRequest(
            **payload.model_dump(exclude={"items"}), created_at=created_at
        )
        record.items = [MaterialIssueItem(**item.model_dump()) for item in payload.items]
        return await flush_created_record(
            self.session, record, MaterialIssueRequestResponse, children=record.items
        )
