from datetime import datetime
from typing import List
from pydantic import BaseModel


class MRPShortageItem(BaseModel):
    part_id: int
    part_number: str
    part_name: str
    gross_requirement: float
    current_stock: float
    allocated_stock: float
    net_requirement: float
    suggested_action: str
    supplier_lead_time_days: int


class MRPRunResult(BaseModel):
    plan_run_id: str
    run_timestamp: datetime
    total_parts_analyzed: int
    shortages_detected: int
    items: List[MRPShortageItem]


class DashboardMetrics(BaseModel):
    active_work_orders: int
    total_parts_in_catalog: int
    critical_shortages_count: int
    today_dispatches_count: int
    warehouse_capacity_utilization_pct: float
