"""Dashboard policy; unavailable metrics and MRP retain existing behavior."""

from datetime import datetime, timedelta

from app.core.errors import WorkflowNotImplemented
from app.modules.reporting.ports import ReportingRepository
from app.modules.reporting.schemas import DashboardMetrics


class ReportingService:
    def __init__(self, repository: ReportingRepository):
        self.repository = repository

    async def get_dashboard_metrics(self) -> DashboardMetrics:
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return DashboardMetrics(
            active_work_orders=await self.repository.count_active_work_orders(),
            total_parts_in_catalog=await self.repository.count_catalog_parts(),
            critical_shortages_count=None,
            today_dispatches_count=await self.repository.count_dispatches(
                start, start + timedelta(days=1)
            ),
            warehouse_capacity_utilization_pct=None,
        )

    async def execute_mrp_calculation(self) -> None:
        raise WorkflowNotImplemented()
