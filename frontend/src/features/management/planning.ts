import type { Bom, Item, MaterialDemand, ProductionPlan, Issue, Workspace } from "./types.ts";

export function itemById(items: readonly Item[], id: string): Item {
  const item = items.find((entry) => entry.id === id);
  if (!item) throw new Error("Không tìm thấy mặt hàng.");
  return item;
}
export function activeBom(boms: readonly Bom[], outputId: string): Bom {
  const bom = boms.find((entry) => entry.outputId === outputId && entry.active);
  if (!bom) throw new Error("Mặt hàng chưa có BOM hiện hành.");
  return bom;
}
export function materialDemand(
  items: readonly Item[],
  bom: Bom,
  quantity: number,
): MaterialDemand[] {
  return bom.lines.map(({ itemId, quantity: perUnit }) => {
    const available = itemById(items, itemId).stock;
    const required = perUnit * quantity;
    return { itemId, perUnit, required, available, missing: Math.max(0, required - available) };
  });
}
export function calculatePlan(
  items: readonly Item[],
  productId: string,
  quantity: number,
  boms: readonly Bom[],
): ProductionPlan {
  const availableProducts = itemById(items, productId).stock;
  const useProducts = Math.min(quantity, availableProducts);
  const bikesToMake = Math.max(0, quantity - useProducts);
  const bikeBom = bikesToMake > 0 ? activeBom(boms, productId) : null;
  const wheelsRequired =
    bikesToMake * (bikeBom?.lines.find((line) => line.itemId === "wheel")?.quantity ?? 0);
  const useWheels = Math.min(wheelsRequired, itemById(items, "wheel").stock);
  const wheelsToMake = wheelsRequired - useWheels;
  const wheelBom = wheelsToMake > 0 ? activeBom(boms, "wheel") : null;
  return {
    requested: quantity,
    availableProducts,
    useProducts,
    bikesToMake,
    wheelsRequired,
    useWheels,
    wheelsToMake,
    bikeMaterials: bikeBom ? materialDemand(items, bikeBom, bikesToMake) : [],
    wheelMaterials: wheelBom ? materialDemand(items, wheelBom, wheelsToMake) : [],
    bikeBomId: bikeBom?.id ?? null,
    wheelBomId: wheelBom?.id ?? null,
  };
}
export function issueApprovalProblem(workspace: Workspace, issue: Issue): string | null {
  if (issue.status !== "cho_duyet") return "Chỉ duyệt được phiếu đang chờ duyệt.";
  if (
    !issue.lines.length ||
    new Set(issue.lines.map((line) => line.itemId)).size !== issue.lines.length
  )
    return "Chi tiết phiếu xuất không hợp lệ.";
  if (issue.kind === "xuat_vat_tu") {
    const order = workspace.orders.find((entry) => entry.id === issue.orderId);
    if (!order || issue.requestId !== null)
      return "Phiếu xuất vật tư phải gắn đúng một lệnh sản xuất.";
    if (!["da_gui", "dang_thuc_hien"].includes(order.status))
      return "Lệnh nguồn chưa gửi hoặc đã đóng.";
    for (const line of issue.lines) {
      const needed = order.demand.find((entry) => entry.itemId === line.itemId)?.required;
      const supplied = workspace.issues
        .filter(
          (entry) =>
            entry.id !== issue.id && entry.orderId === order.id && entry.status === "da_duyet",
        )
        .flatMap((entry) => entry.lines)
        .filter((entry) => entry.itemId === line.itemId)
        .reduce((sum, entry) => sum + entry.quantity, 0);
      if (needed === undefined || line.quantity > needed - supplied)
        return "Số lượng xuất vượt phần nhu cầu trực tiếp chưa cấp của lệnh.";
    }
  } else {
    const request = workspace.requests.find((entry) => entry.id === issue.requestId);
    if (!request || issue.orderId !== null)
      return "Phiếu xuất thành phẩm phải gắn đúng một yêu cầu.";
    if (request.status === "cho_bo_sung_vat_tu")
      return "Yêu cầu đang chờ bổ sung vật tư, chưa được xuất thành phẩm.";
    if (!["da_gui", "dang_thuc_hien"].includes(request.status))
      return "Yêu cầu nguồn chưa gửi hoặc đã đóng.";
    const supplied = workspace.issues
      .filter(
        (entry) =>
          entry.id !== issue.id && entry.requestId === request.id && entry.status === "da_duyet",
      )
      .flatMap((entry) => entry.lines)
      .reduce((sum, entry) => sum + entry.quantity, 0);
    if (
      issue.lines.some((line) => line.itemId !== request.productId) ||
      issue.lines.reduce((sum, line) => sum + line.quantity, 0) > request.quantity - supplied
    )
      return "Số lượng thành phẩm vượt phần yêu cầu chưa xuất.";
  }
  for (const line of issue.lines) {
    const item = workspace.items.find((entry) => entry.id === line.itemId);
    if (!item || !item.active) return "Mặt hàng không tồn tại hoặc đã ngừng hoạt động.";
    if (!Number.isSafeInteger(line.quantity) || line.quantity <= 0)
      return "Số lượng xuất phải là số nguyên dương.";
    if (line.quantity > item.stock)
      return `${item.name} không đủ tồn kho. Vui lòng bổ sung trước khi duyệt.`;
  }
  return null;
}
export const number = (value: number) => new Intl.NumberFormat("vi-VN").format(value);
export const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
export function documentTotal(lines: readonly { quantity: number; price: number }[]): number;
export function documentTotal(
  lines: readonly { quantity: number; price: number | null }[],
): number | null;
export function documentTotal(
  lines: readonly { quantity: number; price: number | null }[],
): number | null {
  return lines.some((line) => line.price === null)
    ? null
    : lines.reduce((sum, line) => sum + line.quantity * (line.price ?? 0), 0);
}
export const today = () => {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const part = (type: string) => parts.find((entry) => entry.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
};
