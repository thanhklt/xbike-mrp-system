export type UserRole = "ADMIN" | "MANAGER" | "WAREHOUSE" | "PRODUCTION" | "QUALITY" | "AUDITOR";

export type ItemType = "RAW_MATERIAL" | "SUB_ASSEMBLY" | "FINISHED_GOOD";

export type PartCategory =
  | "FRAME"
  | "FORK"
  | "WHEEL"
  | "DRIVETRAIN"
  | "BRAKE"
  | "COCKPIT"
  | "ELECTRICAL"
  | "ACCESSORY"
  | "HARDWARE";

export type UnitOfMeasure = "PCS" | "SET" | "KG" | "METER" | "LITER";

export type WorkOrderStatus =
  | "DRAFT"
  | "PLANNED"
  | "RELEASED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED";

export type MaterialIssueStatus =
  | "REQUESTED"
  | "APPROVED"
  | "PICKING"
  | "ISSUED"
  | "CANCELLED";

export type StockMovementType =
  | "RECEIPT"
  | "ISSUANCE_TO_PRODUCTION"
  | "PRODUCTION_RECEIPT"
  | "DISPATCH"
  | "SCRAP"
  | "ADJUSTMENT";

export interface PaginationMetadata {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: PaginationMetadata;
  message: string;
}

export interface Part {
  id: number;
  part_number: string;
  name: string;
  description?: string;
  item_type: ItemType;
  category: PartCategory;
  unit: UnitOfMeasure;
  lead_time_days: number;
  safety_stock: number;
  standard_cost: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Supplier {
  id: number;
  code: string;
  name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  payment_terms_days: number;
  lead_time_days: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BOMItem {
  id: number;
  component_part_id: number;
  component_part_number?: string;
  component_name?: string;
  unit?: string;
  quantity_required: number;
  scrap_factor_percent: number;
  notes?: string;
}

export interface BOMHeader {
  id: number;
  product_part_id: number;
  product_name?: string;
  product_part_number?: string;
  bom_code: string;
  version: string;
  description?: string;
  is_active: boolean;
  items: BOMItem[];
  created_at: string;
  updated_at: string;
}

export interface StockLevel {
  id: number;
  part_id: number;
  part_number: string;
  part_name: string;
  warehouse_code: string;
  bin_location: string;
  quantity_on_hand: number;
  quantity_allocated: number;
  quantity_reserved: number;
  quantity_available: number;
  updated_at: string;
}

export interface WorkOrder {
  id: number;
  work_order_number: string;
  product_part_id: number;
  product_part_number?: string;
  product_name?: string;
  bom_id: number;
  quantity_planned: number;
  quantity_completed: number;
  quantity_scrapped: number;
  status: WorkOrderStatus;
  scheduled_start?: string;
  scheduled_finish?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardMetrics {
  active_work_orders: number;
  total_parts_in_catalog: number;
  critical_shortages_count: number;
  today_dispatches_count: number;
  warehouse_capacity_utilization_pct: number;
}
