import { initialWorkspace } from "./demo-data.ts";
import { calculatePlan, issueApprovalProblem, itemById, materialDemand } from "./planning.ts";
import { currentManager } from "./types.ts";
import type {
  DocumentLine,
  ProductionPlan,
  ProductionRequest,
  Receipt,
  ReceiptInput,
  RequestInput,
  RequestPreview,
  WorkOrder,
  Workspace,
} from "./types.ts";

export class DemoError extends Error {}
function requireQuantity(quantity: number): void {
  if (!Number.isSafeInteger(quantity) || quantity <= 0 || quantity > 1000000)
    throw new DemoError("Số lượng phải là số nguyên từ 1 đến 1.000.000.");
}
function requireDate(date: string): void {
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    !Number.isFinite(Date.parse(date)) ||
    new Date(date).toISOString().slice(0, 10) !== date
  )
    throw new DemoError("Ngày nhập không hợp lệ.");
}
function code(prefix: string, sequence: number, at: Date): string {
  const month = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(at);
  return `${prefix}-${month.find((part) => part.type === "year")?.value}${month.find((part) => part.type === "month")?.value}-${sequence.toString().padStart(6, "0")}`;
}
function hasShortage(state: Workspace, requestId: string): boolean {
  const needed = new Map<string, number>();
  for (const order of state.orders.filter(
    (entry) => entry.requestId === requestId && !["hoan_thanh", "da_huy"].includes(entry.status),
  )) {
    for (const line of order.demand) {
      const supplied = state.issues
        .filter((issue) => issue.orderId === order.id && issue.status === "da_duyet")
        .flatMap((issue) => issue.lines)
        .filter((entry) => entry.itemId === line.itemId)
        .reduce((sum, entry) => sum + entry.quantity, 0);
      needed.set(
        line.itemId,
        (needed.get(line.itemId) ?? 0) + Math.max(0, line.required - supplied),
      );
    }
  }
  return [...needed].some(([id, quantity]) => itemById(state.items, id).stock < quantity);
}
function planShortage(plan: ProductionPlan): boolean {
  // The child order makes missing wheel assemblies; do not count that output as a raw-material shortage.
  return [
    ...plan.bikeMaterials.filter((line) => line.itemId !== "wheel"),
    ...plan.wheelMaterials,
  ].some((line) => line.missing > 0);
}

export class DemoEngine {
  private state: Workspace;
  private previews = new Map<
    string,
    { requestId: string; fingerprint: string; expiresAt: number }
  >();
  private readonly clock: () => Date;
  constructor(initial: Workspace = initialWorkspace(), clock: () => Date = () => new Date()) {
    this.state = structuredClone(initial);
    this.clock = clock;
  }
  snapshot(): Workspace {
    return structuredClone(this.state);
  }
  reset(): Workspace {
    this.state = initialWorkspace();
    this.previews.clear();
    return this.snapshot();
  }
  private worker(id: string | null, required = false): void {
    if (id === null && !required) return;
    if (
      !this.state.employees.some(
        (entry) => entry.id === id && entry.active && entry.role === "nhan_vien",
      )
    )
      throw new DemoError("Người được giao phải là nhân viên đang hoạt động.");
  }
  private validateLines(lines: readonly DocumentLine[]): void {
    if (!lines.length) throw new DemoError("Cần ít nhất một dòng nguyên vật liệu hoặc linh kiện.");
    if (new Set(lines.map((line) => line.itemId)).size !== lines.length)
      throw new DemoError("Mỗi mặt hàng chỉ được chọn một lần.");
    for (const line of lines) {
      requireQuantity(line.quantity);
      if (!Number.isSafeInteger(line.price) || line.price < 0 || line.price > 1000000000)
        throw new DemoError("Đơn giá phải là số nguyên không âm, tối đa 1 tỷ đồng.");
      const item = itemById(this.state.items, line.itemId);
      if (!item.active) throw new DemoError("Mặt hàng đã ngừng hoạt động.");
      if (!["nguyen_vat_lieu", "linh_kien"].includes(item.kind))
        throw new DemoError("Phiếu nhập chỉ nhận nguyên vật liệu và linh kiện.");
      if (
        !Number.isSafeInteger(item.stock + line.quantity) ||
        item.stock + line.quantity > 2147483647
      )
        throw new DemoError("Số lượng tồn vượt giới hạn cho phép.");
    }
    if (!Number.isSafeInteger(lines.reduce((sum, line) => sum + line.price * line.quantity, 0)))
      throw new DemoError("Tổng tiền vượt giới hạn cho phép.");
  }
  private receiptRecord(input: ReceiptInput): Receipt {
    this.validateLines(input.lines);
    if (!this.state.suppliers.some((entry) => entry.id === input.supplierId))
      throw new DemoError("Vui lòng chọn nhà cung cấp.");
    requireDate(input.date);
    const previous = input.id
      ? this.state.receipts.find((entry) => entry.id === input.id)
      : undefined;
    if (input.id && !previous) throw new DemoError("Không tìm thấy phiếu nhập.");
    const at = this.clock();
    return {
      ...structuredClone(input),
      id: previous?.id ?? `receipt-${this.state.receipts.length + 31}`,
      code: previous?.code ?? code("PN", this.state.receipts.length + 31, at),
      creatorId: previous?.creatorId ?? currentManager.id,
      createdAt: previous?.createdAt ?? at.toISOString(),
      status: previous?.status ?? "nhap",
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
    if (receipt.status === "hoan_thanh") throw new DemoError("Phiếu đã hoàn thành không thể sửa.");
    this.storeReceipt(receipt);
    return structuredClone(receipt);
  }
  confirmReceipt(input: ReceiptInput): Receipt {
    const previous = this.state.receipts.find((entry) => entry.id === input.id);
    if (previous?.status === "hoan_thanh") return structuredClone(previous);
    const draft = this.receiptRecord(input);
    const at = this.clock().toISOString();
    const posting = draft.lines.map((line) => {
      const before = itemById(this.state.items, line.itemId).stock;
      return { itemId: line.itemId, before, after: before + line.quantity };
    });
    const receipt: Receipt = { ...draft, status: "hoan_thanh", posting };
    let next: Workspace = {
      ...this.state,
      items: this.state.items.map((item) => {
        const changed = posting.find((entry) => entry.itemId === item.id);
        return changed ? { ...item, stock: changed.after, stockUpdatedAt: at } : item;
      }),
      receipts: [...this.state.receipts.filter((entry) => entry.id !== receipt.id), receipt],
    };
    next = {
      ...next,
      requests: next.requests.map((request) =>
        request.status === "cho_bo_sung_vat_tu" && !hasShortage(next, request.id)
          ? {
              ...request,
              status: next.orders.some(
                (order) => order.requestId === request.id && order.status === "dang_thuc_hien",
              )
                ? "dang_thuc_hien"
                : "da_gui",
            }
          : request,
      ),
    };
    this.state = next;
    return structuredClone(receipt);
  }
  private validateRequest(input: RequestInput): void {
    requireQuantity(input.quantity);
    const item = itemById(this.state.items, input.productId);
    if (item.kind !== "thanh_pham" || !item.active)
      throw new DemoError("Vui lòng chọn thành phẩm đang hoạt động.");
    this.worker(input.assigneeId);
  }
  createRequest(input: RequestInput): ProductionRequest {
    this.validateRequest(input);
    const at = this.clock();
    const sequence = this.state.requests.length + 48;
    const request: ProductionRequest = {
      ...structuredClone(input),
      id: `request-${sequence}`,
      code: code("YCSX", sequence, at),
      creatorId: currentManager.id,
      createdAt: at.toISOString(),
      status: "nhap",
      plan: null,
    };
    this.state = { ...this.state, requests: [...this.state.requests, request] };
    return structuredClone(request);
  }
  updateRequest(id: string, input: RequestInput): ProductionRequest {
    const previous = this.state.requests.find((entry) => entry.id === id);
    if (!previous || previous.status !== "nhap") throw new DemoError("Chỉ sửa được yêu cầu nháp.");
    this.validateRequest(input);
    const request = { ...previous, ...structuredClone(input), plan: null };
    this.state = {
      ...this.state,
      requests: this.state.requests.map((entry) => (entry.id === id ? request : entry)),
    };
    for (const [token, preview] of this.previews)
      if (preview.requestId === id) this.previews.delete(token);
    return structuredClone(request);
  }
  private previewFingerprint(request: ProductionRequest, plan: ProductionPlan): string {
    return JSON.stringify({
      requestId: request.id,
      assigneeId: request.assigneeId,
      productId: request.productId,
      plan,
    });
  }
  private validatePlanItems(plan: ProductionPlan): void {
    const ids = [...plan.bikeMaterials, ...plan.wheelMaterials].map((line) => line.itemId);
    if (ids.some((id) => !itemById(this.state.items, id).active))
      throw new DemoError("Kế hoạch chứa mặt hàng đã ngừng hoạt động.");
  }
  previewRequest(id: string): RequestPreview {
    const request = this.state.requests.find((entry) => entry.id === id);
    if (!request || request.status !== "nhap")
      throw new DemoError("Chỉ tính kế hoạch cho yêu cầu nháp.");
    const plan = calculatePlan(
      this.state.items,
      request.productId,
      request.quantity,
      this.state.boms,
    );
    this.validatePlanItems(plan);
    const at = this.clock();
    const token = crypto.randomUUID();
    this.previews.set(token, {
      requestId: id,
      fingerprint: this.previewFingerprint(request, plan),
      expiresAt: at.getTime() + 600000,
    });
    return { requestId: id, plan, token, createdAt: at.toISOString() };
  }
  sendRequest(id: string, token: string): ProductionRequest {
    const request = this.state.requests.find((entry) => entry.id === id);
    if (!request || request.status !== "nhap") throw new DemoError("Chỉ gửi được yêu cầu nháp.");
    this.worker(request.assigneeId, true);
    const plan = calculatePlan(
      this.state.items,
      request.productId,
      request.quantity,
      this.state.boms,
    );
    this.validatePlanItems(plan);
    const preview = this.previews.get(token);
    if (
      !preview ||
      preview.requestId !== id ||
      preview.expiresAt <= this.clock().getTime() ||
      preview.fingerprint !== this.previewFingerprint(request, plan)
    )
      throw new DemoError("Kế hoạch đã thay đổi hoặc hết hạn. Vui lòng tính lại trước khi gửi.");
    const at = this.clock();
    const generated: WorkOrder[] = [];
    const addOrder = (
      outputId: string,
      quantity: number,
      bomId: string,
      parentOrderId: string | null,
    ): WorkOrder => {
      const bom = this.state.boms.find((entry) => entry.id === bomId);
      if (!bom || !bom.active) throw new DemoError("BOM đã thay đổi. Vui lòng tính lại kế hoạch.");
      const sequence = this.state.orders.length + generated.length + 110;
      const order: WorkOrder = {
        id: `order-${sequence}`,
        code: code("LSX", sequence, at),
        requestId: id,
        kind: outputId === "wheel" ? "wheel" : "bike",
        quantity,
        assigneeId: null,
        bomId,
        parentOrderId,
        outputId,
        createdAt: at.toISOString(),
        status: "nhap",
        demand: materialDemand(this.state.items, bom, quantity).map(
          ({ itemId, perUnit, required }) => ({ itemId, perUnit, required }),
        ),
      };
      generated.push(order);
      return order;
    };
    if (plan.bikesToMake > 0 && plan.bikeBomId) {
      const parent = addOrder(request.productId, plan.bikesToMake, plan.bikeBomId, null);
      if (plan.wheelsToMake > 0 && plan.wheelBomId)
        addOrder("wheel", plan.wheelsToMake, plan.wheelBomId, parent.id);
    }
    const sent: ProductionRequest = {
      ...request,
      plan,
      status: planShortage(plan) ? "cho_bo_sung_vat_tu" : "da_gui",
    };
    this.state = {
      ...this.state,
      requests: this.state.requests.map((entry) => (entry.id === id ? sent : entry)),
      orders: [...this.state.orders, ...generated],
    };
    this.previews.delete(token);
    return structuredClone(sent);
  }
  assignOrder(id: string, assigneeId: string | null): WorkOrder {
    const order = this.state.orders.find((entry) => entry.id === id);
    if (!order || order.status !== "nhap") throw new DemoError("Chỉ phân công được lệnh nháp.");
    this.worker(assigneeId);
    const updated = { ...order, assigneeId };
    this.state = {
      ...this.state,
      orders: this.state.orders.map((entry) => (entry.id === id ? updated : entry)),
    };
    return structuredClone(updated);
  }
  sendOrder(id: string): WorkOrder {
    const order = this.state.orders.find((entry) => entry.id === id);
    if (!order || order.status !== "nhap") throw new DemoError("Chỉ gửi được lệnh nháp.");
    this.worker(order.assigneeId, true);
    const request = this.state.requests.find((entry) => entry.id === order.requestId);
    if (!request || !["da_gui", "cho_bo_sung_vat_tu", "dang_thuc_hien"].includes(request.status))
      throw new DemoError("Yêu cầu nguồn không cho phép gửi lệnh.");
    const updated: WorkOrder = { ...order, status: "da_gui" };
    this.state = {
      ...this.state,
      orders: this.state.orders.map((entry) => (entry.id === id ? updated : entry)),
    };
    return structuredClone(updated);
  }
  approveIssue(id: string): Workspace {
    const issue = this.state.issues.find((entry) => entry.id === id);
    if (!issue) throw new DemoError("Không tìm thấy phiếu xuất.");
    if (issue.status === "da_duyet") return this.snapshot();
    const problem = issueApprovalProblem(this.state, issue);
    if (problem) throw new DemoError(problem);
    const at = this.clock().toISOString();
    const lines = issue.lines.map((line) => {
      const price = itemById(this.state.items, line.itemId).price;
      if (!Number.isSafeInteger(price) || price < 0)
        throw new DemoError("Đơn giá danh mục phải là integer VND không âm.");
      return { ...line, price };
    });
    if (!Number.isSafeInteger(lines.reduce((sum, line) => sum + line.quantity * line.price, 0)))
      throw new DemoError("Tổng tiền vượt giới hạn cho phép.");
    const posting = issue.lines.map((line) => {
      const before = itemById(this.state.items, line.itemId).stock;
      return { itemId: line.itemId, before, after: before - line.quantity };
    });
    const issues = this.state.issues.map((entry) =>
      entry.id === id ? { ...entry, status: "da_duyet" as const, lines, posting } : entry,
    );
    const requests = this.state.requests.map((request) => {
      if (request.id !== issue.requestId) return request;
      const supplied = issues
        .filter((entry) => entry.requestId === request.id && entry.status === "da_duyet")
        .flatMap((entry) => entry.lines)
        .reduce((sum, line) => sum + line.quantity, 0);
      return {
        ...request,
        status:
          supplied >= request.quantity ? ("hoan_thanh" as const) : ("dang_thuc_hien" as const),
      };
    });
    this.state = {
      ...this.state,
      items: this.state.items.map((item) => {
        const changed = posting.find((entry) => entry.itemId === item.id);
        return changed ? { ...item, stock: changed.after, stockUpdatedAt: at } : item;
      }),
      issues,
      requests,
    };
    return this.snapshot();
  }
  rejectIssue(id: string, reason: string): Workspace {
    const issue = this.state.issues.find((entry) => entry.id === id);
    if (!issue || issue.status !== "cho_duyet")
      throw new DemoError("Chỉ từ chối được phiếu đang chờ duyệt.");
    if (!reason.trim()) throw new DemoError("Vui lòng nhập lý do từ chối.");
    this.state = {
      ...this.state,
      issues: this.state.issues.map((entry) =>
        entry.id === id ? { ...entry, status: "tu_choi", reason: reason.trim() } : entry,
      ),
    };
    return this.snapshot();
  }
}
