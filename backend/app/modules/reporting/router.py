from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.catalog.models import Part
from app.modules.material_issuing.models import IssueNote
from app.modules.production.models import WorkOrder
from app.modules.reporting.schemas import DashboardMetrics
from app.shared.database_queries import workflow_not_implemented

router = APIRouter(
    prefix="/reporting", tags=["Reporting"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/dashboard-metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(db: Annotated[AsyncSession, Depends(get_db)]):
    # The source schema has no warehouse capacity or reservation records.
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return DashboardMetrics(
        active_work_orders=await db.scalar(
            select(func.count())
            .select_from(WorkOrder)
            .where(WorkOrder.trang_thai.in_(["da_gui", "dang_thuc_hien"]))
        ),
        total_parts_in_catalog=await db.scalar(select(func.count()).select_from(Part)),
        critical_shortages_count=None,
        today_dispatches_count=await db.scalar(
            select(func.count())
            .select_from(IssueNote)
            .where(
                IssueNote.loai_phieu == "xuat_thanh_pham",
                IssueNote.trang_thai == "da_duyet",
                IssueNote.created_at >= start,
                IssueNote.created_at < start + timedelta(days=1),
            )
        ),
        warehouse_capacity_utilization_pct=None,
    )


@router.post("/run-mrp")
async def execute_mrp_calculation(
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    workflow_not_implemented()
