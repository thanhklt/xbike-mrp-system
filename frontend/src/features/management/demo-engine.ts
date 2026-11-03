import { initialWorkspace } from "./demo-data.ts";
import { calculatePlan, itemById } from "./planning.ts";
import { employees, suppliers } from "./types.ts";
import type {
  DocumentLine,
  ProductionRequest,
  Receipt,
  ReceiptInput,
  RequestInput,
  WorkOrder,
  WorkOrderInput,
  Workspace,
} from "./types.ts";

export class DemoError extends Error {}

function requireQuantity(quantity: number): void {
  if (!Number.isSafeInteger(quantity) || quantity <= 0 || quantity > 1000000) {
    throw new DemoError("Số lượng phải là số nguyên từ 1 đến 1.000.000.");
  }
}

export class DemoEngine {
  private state: Workspace = initialWorkspace();

  snapshot(): Workspace {
    return structuredClone(this.state);
  }

  reset(): Workspace {
    this.state = initialWorkspace();
    return this.snapshot();
  }

  private validateLines(lines: readonly DocumentLine[]): void {
    if (!lines.length) throw new DemoError("Cần ít nhất một dòng nguyên vật liệu.");
    if (new Set(lines.map((line) => line.itemId)).size !== lines.length)
      throw new DemoError("Mỗi nguyên vật liệu chỉ được chọn một lần.");
    for (const line of lines) {
      requireQuantity(line.quantity);
      if (!Number.isSafeInteger(line.price) || line.price < 0 || line.price > 1000000000)
        throw new DemoError("Đơn giá phải là số nguyên không âm, tối đa 1 tỷ đồng.");
      if (itemById(this.state.items, line.itemId).kind !== "material")
        throw new DemoError("Phiếu nhập này chỉ nhận nguyên vật liệu.");
    }
    if (!Number.isSafeInteger(lines.reduce((sum, line) => sum + line.price * line.quantity, 0)))
      throw new DemoError("Tổng tiền vượt giới hạn cho phép.");
  }

  private receiptRecord(input: ReceiptInput): Receipt {
    this.validateLines(input.lines);
    if (!suppliers.some((name) => name === input.supplier))
      throw new DemoError("Vui lòng chọn nhà cung cấp.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(input.date) || !Number.isFinite(Date.parse(input.date)))
      throw new DemoError("Ngày nhập không hợp lệ.");
    const previous = input.id
      ? this.state.receipts.find((receipt) => receipt.id === input.id)
      : undefined;
    if (input.id && !previous) throw new DemoError("Không tìm thấy phiếu nhập.");
    const sequence = this.state.receipts.length + 31;
    return {
      ...structuredClone(input),
      id: previous?.id ?? `receipt-${sequence}`,
      code: previous?.code ?? `PN-2026-${sequence.toString().padStart(3, "0")}`,
      status: previous?.status ?? "draft",
    };
  }

  private storeReceipt(receipt: Receipt): void {
    this.state = {
      ...this.state,
      receipts: [...this.state.receipts.filter((entry) => entry.id !== receipt.id), receipt],
    };
  }

  saveReceipt(input: ReceiptInput): Receipt {
    const receipt = this.receiptRecord(input);
    if (receipt.status === "confirmed") throw new DemoError("Phiếu đã xác nhận không thể sửa.");
    this.storeReceipt(receipt);
    return structuredClone(receipt);
  }

  confirmReceipt(input: ReceiptInput): Receipt {
    const previous = this.state.receipts.find((entry) => entry.id === input.id);
    if (previous?.status === "confirmed") return structuredClone(previous);
    const draft = this.receiptRecord(input);
    const posting = draft.lines.map((line) => {
      const before = itemById(this.state.items, line.itemId).stock;
      return { itemId: line.itemId, before, after: before + line.quantity };
    });
    const receipt: Receipt = { ...draft, status: "confirmed", posting };
    const quantities = new Map(receipt.lines.map((line) => [line.itemId, line.quantity]));
    const items = this.state.items.map((item) => ({
      ...item,
      stock: item.stock + (quantities.get(item.id) ?? 0),
    }));
    this.state = { ...this.state, items };
    this.storeReceipt(receipt);
    return structuredClone(receipt);
  }

  createRequest(input: RequestInput): ProductionRequest {
    requireQuantity(input.quantity);
    if (itemById(this.state.items, input.productId).kind !== "product")
      throw new DemoError("Vui lòng chọn thành phẩm hợp lệ.");
    if (!employees.some((name) => name === input.assignee))
      throw new DemoError("Vui lòng chọn nhân viên phụ trách.");
    const sequence = this.state.requests.length + 48;
    const request = {
      ...input,
      id: `request-${sequence}`,
      code: `YC-2026-${sequence.toString().padStart(3, "0")}`,
      plan: calculatePlan(this.state.items, input.productId, input.quantity),
    };
    this.state = { ...this.state, requests: [...this.state.requests, request] };
    return structuredClone(request);
  }

  createOrder(input: WorkOrderInput): WorkOrder {
    requireQuantity(input.quantity);
    const request = this.state.requests.find((entry) => entry.id === input.requestId);
    if (!request) throw new DemoError("Vui lòng chọn yêu cầu thành phẩm.");
    if (!employees.some((name) => name === input.assignee))
      throw new DemoError("Vui lòng chọn nhân viên thực hiện.");
    if (input.kind !== "bike" && input.kind !== "wheel")
      throw new DemoError("Loại lệnh không hợp lệ.");
    const planned = input.kind === "bike" ? request.plan.bikesToMake : request.plan.wheelsToMake;
    const ordered = this.state.orders
      .filter((order) => order.requestId === request.id && order.kind === input.kind)
      .reduce((sum, order) => sum + order.quantity, 0);
    if (input.quantity > planned - ordered)
      throw new DemoError(`Số lượng vượt phần nhu cầu chưa tạo lệnh (${planned - ordered}).`);
    const sequence = this.state.orders.length + 110;
    const order: WorkOrder = {
      ...input,
      id: `order-${sequence}`,
      code: `LSX-2026-${sequence}`,
      outputId: input.kind === "bike" ? request.productId : "wheel",
    };
    this.state = { ...this.state, orders: [...this.state.orders, order] };
    return structuredClone(order);
  }

  approveIssue(id: string): Workspace {
    const issue = this.state.issues.find((entry) => entry.id === id);
    if (!issue) throw new DemoError("Không tìm thấy phiếu xuất.");
    if (issue.status === "approved") return this.snapshot();
    if (issue.status !== "pending") throw new DemoError("Chỉ duyệt được phiếu đang chờ duyệt.");
    const posting = issue.lines.map((line) => {
      const item = itemById(this.state.items, line.itemId);
      if (line.quantity > item.stock)
        throw new DemoError(`${item.name} không đủ tồn kho. Vui lòng bổ sung trước khi duyệt.`);
      return { itemId: item.id, before: item.stock, after: item.stock - line.quantity };
    });
    this.state = {
      ...this.state,
      items: this.state.items.map((item) => ({
        ...item,
        stock: posting.find((entry) => entry.itemId === item.id)?.after ?? item.stock,
      })),
      issues: this.state.issues.map((entry) =>
        entry.id === id ? { ...entry, status: "approved", posting } : entry,
      ),
    };
    return this.snapshot();
  }

  rejectIssue(id: string, reason: string): Workspace {
    const issue = this.state.issues.find((entry) => entry.id === id);
    if (!issue || issue.status !== "pending")
      throw new DemoError("Chỉ từ chối được phiếu đang chờ duyệt.");
    if (!reason.trim()) throw new DemoError("Vui lòng nhập lý do từ chối.");
    this.state = {
      ...this.state,
      issues: this.state.issues.map((entry) =>
        entry.id === id ? { ...entry, status: "rejected", reason: reason.trim() } : entry,
      ),
    };
    return this.snapshot();
  }
}
