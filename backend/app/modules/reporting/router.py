from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user_payload, get_reporting_service, require_roles
from app.modules.reporting.schemas import DashboardMetrics
from app.modules.reporting.service import ReportingService

router = APIRouter(
    prefix="/reporting", tags=["Reporting"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/dashboard-metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    service: Annotated[ReportingService, Depends(get_reporting_service)],
):
    return await service.get_dashboard_metrics()


@router.post("/run-mrp")
async def execute_mrp_calculation(
    service: Annotated[ReportingService, Depends(get_reporting_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    await service.execute_mrp_calculation()
