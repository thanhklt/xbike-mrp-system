export type ItemKind = "nguyen_vat_lieu" | "linh_kien" | "ban_thanh_pham" | "thanh_pham";
export type IssueStatus = "cho_duyet" | "da_duyet" | "tu_choi";
export type IssueKind = "xuat_vat_tu" | "xuat_thanh_pham";
export type OrderKind = "bike" | "wheel";
export type RequestStatus =
  "nhap" | "da_gui" | "cho_bo_sung_vat_tu" | "dang_thuc_hien" | "hoan_thanh" | "da_huy";
export type OrderStatus = "nhap" | "da_gui" | "dang_thuc_hien" | "hoan_thanh" | "da_huy";
export interface Employee {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly role: "quan_ly" | "nhan_vien";
  readonly active: boolean;
}
export interface Supplier {
  readonly id: string;
  readonly code: string;
  readonly name: string;
}
export const employees: readonly Employee[] = [
  { id: "manager-binh", code: "NV-000001", name: "Trần Thanh Bình", role: "quan_ly", active: true },
  { id: "employee-an", code: "NV-000002", name: "Nguyễn Minh An", role: "nhan_vien", active: true },
  { id: "employee-nam", code: "NV-000003", name: "Lê Hoàng Nam", role: "nhan_vien", active: true },
  { id: "employee-huy", code: "NV-000004", name: "Phạm Quốc Huy", role: "nhan_vien", active: true },
];
export const currentManager = employees[0];
export const suppliers: readonly Supplier[] = [
  { id: "supplier-an-phat", code: "NCC-000001", name: "Công ty Linh kiện An Phát" },
  { id: "supplier-thanh-cong", code: "NCC-000002", name: "Công ty Cơ khí Thành Công" },
  { id: "supplier-viet-nhat", code: "NCC-000003", name: "Công ty Phụ tùng Việt Nhật" },
];
export interface Item {
  readonly id: string;
  readonly code: string;
  readonly sku: string;
  readonly name: string;
  readonly unit: string;
  readonly kind: ItemKind;
  readonly active: boolean;
  readonly stock: number;
  readonly stockUpdatedAt: string | null;
  readonly price: number;
}
export interface Bom {
  readonly id: string;
  readonly outputId: string;
  readonly version: number;
  readonly active: boolean;
  readonly lines: readonly { readonly itemId: string; readonly quantity: number }[];
}
export interface DocumentLine {
  readonly itemId: string;
  readonly quantity: number;
  readonly price: number;
}
export interface ReceiptInput {
  readonly id?: string;
  readonly date: string;
  readonly supplierId: string;
  readonly note: string;
  readonly lines: readonly DocumentLine[];
}
export interface Receipt extends ReceiptInput {
  readonly id: string;
  readonly code: string;
  readonly creatorId: string;
  readonly createdAt: string;
  readonly status: "nhap" | "hoan_thanh";
  readonly posting?: readonly StockPosting[];
}
export interface RequestInput {
  readonly productId: string;
  readonly quantity: number;
  readonly assigneeId: string | null;
}
export interface MaterialDemand {
  readonly itemId: string;
  readonly perUnit: number;
  readonly required: number;
  readonly available: number;
  readonly missing: number;
}
export interface ProductionPlan {
  readonly requested: number;
  readonly availableProducts: number;
  readonly useProducts: number;
  readonly bikesToMake: number;
  readonly wheelsRequired: number;
  readonly useWheels: number;
  readonly wheelsToMake: number;
  readonly bikeMaterials: readonly MaterialDemand[];
  readonly wheelMaterials: readonly MaterialDemand[];
  readonly bikeBomId: string | null;
  readonly wheelBomId: string | null;
}
export interface ProductionRequest extends RequestInput {
  readonly id: string;
  readonly code: string;
  readonly creatorId: string;
  readonly createdAt: string;
  readonly status: RequestStatus;
  readonly plan: ProductionPlan | null;
}
export interface RequestPreview {
  readonly requestId: string;
  readonly plan: ProductionPlan;
  readonly token: string;
  readonly createdAt: string;
}
export interface OrderDemand {
  readonly itemId: string;
  readonly perUnit: number;
  readonly required: number;
}
export interface WorkOrder {
  readonly id: string;
  readonly code: string;
  readonly requestId: string;
  readonly kind: OrderKind;
  readonly quantity: number;
  readonly assigneeId: string | null;
  readonly bomId: string;
  readonly parentOrderId: string | null;
  readonly outputId: string;
  readonly createdAt: string;
  readonly status: OrderStatus;
  readonly demand: readonly OrderDemand[];
}
export interface StockPosting {
  readonly itemId: string;
  readonly before: number;
  readonly after: number;
}
export interface IssueLine {
  readonly itemId: string;
  readonly quantity: number;
  readonly price: number | null;
}
export interface Issue {
  readonly id: string;
  readonly code: string;
  readonly kind: IssueKind;
  readonly orderId: string | null;
  readonly requestId: string | null;
  readonly creatorId: string;
  readonly createdAt: string;
  readonly status: IssueStatus;
  readonly reason?: string;
  readonly lines: readonly IssueLine[];
  readonly posting?: readonly StockPosting[];
}
export interface Workspace {
  readonly employees: readonly Employee[];
  readonly suppliers: readonly Supplier[];
  readonly boms: readonly Bom[];
  readonly items: readonly Item[];
  readonly receipts: readonly Receipt[];
  readonly requests: readonly ProductionRequest[];
  readonly orders: readonly WorkOrder[];
  readonly issues: readonly Issue[];
}
