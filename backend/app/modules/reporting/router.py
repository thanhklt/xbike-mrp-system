import uuid
from datetime import datetime, timezone
from fastapi import APIRouter

from app.modules.reporting.schemas import DashboardMetrics, MRPRunResult, MRPShortageItem

router = APIRouter(prefix="/reporting", tags=["Reporting & MRP Analytics"])


@router.get("/dashboard-metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics():
    """Retrieve top-level KPI metrics for the executive manufacturing dashboard."""
    return DashboardMetrics(
        active_work_orders=8,
        total_parts_in_catalog=142,
        critical_shortages_count=2,
        today_dispatches_count=12,
        warehouse_capacity_utilization_pct=73.5,
    )


@router.post("/run-mrp", response_model=MRPRunResult)
async def execute_mrp_calculation():
    """Trigger MRP calculation engine across open demand and BOM explosion."""
    run_id = f"MRP-{uuid.uuid4().hex[:8].upper()}"
    return MRPRunResult(
        plan_run_id=run_id,
        run_timestamp=datetime.now(timezone.utc),
        total_parts_analyzed=142,
        shortages_detected=2,
        items=[
            MRPShortageItem(
                part_id=3,
                part_number="XB-RAW-RIM-700C",
                part_name="Double-wall Alloy Rim 700c",
                gross_requirement=150.0,
                current_stock=120.0,
                allocated_stock=40.0,
                net_requirement=70.0,
                suggested_action="Issue Purchase Order for 100 PCS to Apex Precision Alloy",
                supplier_lead_time_days=10,
            ),
            MRPShortageItem(
                part_id=4,
                part_number="XB-RAW-CHN-11S",
                part_name="11-Speed Bicycle Chain",
                gross_requirement=100.0,
                current_stock=88.0,
                allocated_stock=15.0,
                net_requirement=27.0,
                suggested_action="Issue Purchase Order for 50 PCS to Shimano",
                supplier_lead_time_days=7,
            ),
        ],
    )
