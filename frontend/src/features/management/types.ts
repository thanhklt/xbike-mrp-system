export type ItemKind = "material" | "component" | "product";
export type IssueStatus = "pending" | "approved" | "rejected";
export type OrderKind = "bike" | "wheel";

export interface Item {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly unit: string;
  readonly kind: ItemKind;
  readonly stock: number;
  readonly price: number;
}

export interface DocumentLine {
  readonly itemId: string;
  readonly quantity: number;
  readonly price: number;
}

export interface ReceiptInput {
  readonly id?: string;
  readonly date: string;
  readonly supplier: string;
  readonly note: string;
  readonly lines: readonly DocumentLine[];
}

export interface Receipt extends ReceiptInput {
  readonly id: string;
  readonly code: string;
  readonly status: "draft" | "confirmed";
  readonly posting?: readonly StockPosting[];
}

export interface RequestInput {
  readonly productId: string;
  readonly quantity: number;
  readonly reference: string;
  readonly assignee: string;
  readonly note: string;
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
}

export interface ProductionRequest extends RequestInput {
  readonly id: string;
  readonly code: string;
  readonly plan: ProductionPlan;
}

export interface WorkOrderInput {
  readonly requestId: string;
  readonly kind: OrderKind;
  readonly quantity: number;
  readonly assignee: string;
  readonly note: string;
}

export interface WorkOrder extends WorkOrderInput {
  readonly id: string;
  readonly code: string;
  readonly outputId: string;
}

export interface StockPosting {
  readonly itemId: string;
  readonly before: number;
  readonly after: number;
}

export interface Issue {
  readonly id: string;
  readonly code: string;
  readonly kind: ItemKind;
  readonly source: string;
  readonly author: string;
  readonly date: string;
  readonly note: string;
  readonly status: IssueStatus;
  readonly reason?: string;
  readonly lines: readonly DocumentLine[];
  readonly posting?: readonly StockPosting[];
}

export interface Workspace {
  readonly items: readonly Item[];
  readonly receipts: readonly Receipt[];
  readonly requests: readonly ProductionRequest[];
  readonly orders: readonly WorkOrder[];
  readonly issues: readonly Issue[];
}

export const employees = ["Nguyễn Minh An", "Lê Hoàng Nam", "Phạm Quốc Huy"] as const;
export const suppliers = [
  "Công ty Linh kiện An Phát",
  "Công ty Cơ khí Thành Công",
  "Công ty Phụ tùng Việt Nhật",
] as const;
