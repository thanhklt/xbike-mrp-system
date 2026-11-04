import seed from "./seed.json";

export type Role = "Q" | "N" | "A";
export type Page = "mathang" | "lenhsanxuat" | "giaodichkho" | "dieuchinhkho";
export type ItemType = "nguyen_vat_lieu" | "linh_kien" | "ban_thanh_pham" | "thanh_pham";
export type OrderState = "nhap" | "da_gui" | "dang_thuc_hien" | "hoan_thanh" | "da_huy";
export type LedgerType =
  | "nhap_vat_tu"
  | "xuat_vat_tu"
  | "nhap_san_pham_san_xuat"
  | "xuat_thanh_pham"
  | "dieu_chinh_ton_kho";
export interface Item {
  id: number;
  ma_mat_hang: string;
  sku: string;
  ten_mat_hang: string;
  loai_mat_hang: ItemType;
  don_vi_tinh: string;
  don_gia: number;
  mau_sac: string;
  mo_ta: string;
  is_active: boolean;
}
export interface Ledger {
  id: number;
  mat_hang_id: number;
  so_luong_bien_dong: number;
  loai_giao_dich: LedgerType;
  source: string;
  source_id: number;
  nhan_vien_id: number;
  posted_at: string;
}
export interface Order {
  id: number;
  ma_lenh_san_xuat: string;
  mat_hang_id: number;
  so_luong: number;
  nhan_vien_id: number | null;
  trang_thai: OrderState;
  so_luong_da_hoan_thanh: number;
  lenh_san_xuat_cha_id: number | null;
  yeu_cau_san_xuat_id: number;
  bom_id: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  ly_do_huy?: string;
  vat_tu: { mat_hang_id: number; so_luong_can: number; so_luong_da_cap: number }[];
}
export interface AdjustmentLine {
  mat_hang_id: number;
  giao_dich_goc_id: number;
  so_luong_hieu_luc_truoc: number;
  so_luong_dung: number;
  so_luong_bien_dong: number;
}
export interface Adjustment {
  id: number;
  ma_phieu: string;
  phieu_nhap_id: number;
  nhan_vien_id: number;
  trang_thai: "nhap" | "da_xac_nhan" | "loi";
  ly_do: string;
  created_at: string;
  confirmed_at: string | null;
  ticket_id?: number;
  chi_tiet: AdjustmentLine[];
}
export interface Database {
  nextAdjustmentId: number;
  nextTicketId: number;
  items: Item[];
  ledger: Ledger[];
  orders: Order[];
  adjustments: Adjustment[];
  names: Record<string, string>;
  tickets: {
    id: number;
    ma_ticket: string;
    phieu_nhap_id: number;
    trang_thai: string;
    mo_ta_loi: string;
    created_at: string;
    chi_tiet?: AdjustmentLine[];
  }[];
}
// These fixtures model the approved prototype, not an API response or authentication source.
export const initial = seed as Database;
export const labels: Record<string, string> = {
  nguyen_vat_lieu: "Nguyên vật liệu",
  linh_kien: "Linh kiện",
  ban_thanh_pham: "Bán thành phẩm",
  thanh_pham: "Thành phẩm",
  nhap: "Nháp",
  da_gui: "Đã gửi",
  dang_thuc_hien: "Đang thực hiện",
  hoan_thanh: "Hoàn thành",
  da_huy: "Đã hủy",
  da_xac_nhan: "Đã xác nhận",
  loi: "Lỗi",
  active: "Hoạt động",
  inactive: "Ngừng hoạt động",
  nhap_vat_tu: "Nhập vật tư",
  xuat_vat_tu: "Xuất vật tư",
  nhap_san_pham_san_xuat: "Nhập đầu ra sản xuất",
  xuat_thanh_pham: "Xuất thành phẩm",
  dieu_chinh_ton_kho: "Điều chỉnh tồn kho",
  cay: "cây",
  cai: "cái",
  bo: "bộ",
  chiec: "chiếc",
  kg: "kg",
  den: "Đen",
  bac: "Bạc",
  trang: "Trắng",
  xanh_navy: "Xanh navy",
};
export const label = (value: string) => labels[value] || value;
export const fmt = (value: number) => new Intl.NumberFormat("vi-VN").format(value);
export const date = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(new Date(value))
    : "—";
export const localDay = (value: string) =>
  new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(new Date(value));
export const stock = (db: Database, id: number) =>
  db.ledger.filter((x) => x.mat_hang_id === id).reduce((sum, x) => sum + x.so_luong_bien_dong, 0);
export function effective(db: Database, id: number) {
  const source = db.ledger.find((x) => x.id === id);
  if (!source || source.loai_giao_dich !== "nhap_vat_tu")
    throw new Error("Giao dịch nguồn phải là nhập vật tư.");
  return (
    source.so_luong_bien_dong +
    db.adjustments
      .filter((x) => x.trang_thai === "da_xac_nhan")
      .flatMap((x) => x.chi_tiet)
      .filter((x) => x.giao_dich_goc_id === id)
      .reduce((sum, x) => sum + x.so_luong_bien_dong, 0)
  );
}
export const referenced = (db: Database, id: number) =>
  db.ledger.some((x) => x.mat_hang_id === id) ||
  db.orders.some((x) => x.mat_hang_id === id || x.vat_tu.some((v) => v.mat_hang_id === id));
export function saveItem(db: Database, role: Role, item: Item) {
  if (role !== "Q") throw new Error("Chỉ quản lý được sửa danh mục.");
  if (
    !/^MH-(?!000000)\d{6}$/.test(item.ma_mat_hang) ||
    !item.sku.trim() ||
    !item.ten_mat_hang.trim()
  )
    throw new Error("Nhập mã MH-NNNNNN khác 000000, SKU và tên mặt hàng.");
  if (
    !["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"].includes(item.loai_mat_hang)
  )
    throw new Error("Loại mặt hàng không hợp lệ.");
  if (
    !/^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(item.don_vi_tinh) ||
    (item.mau_sac && !/^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(item.mau_sac))
  )
    throw new Error("Đơn vị và màu sắc dùng snake_case không dấu.");
  if (!Number.isSafeInteger(item.don_gia) || item.don_gia < 0)
    throw new Error("Đơn giá phải là số nguyên không âm.");
  if (
    db.items.some(
      (x) => x.id !== item.id && (x.ma_mat_hang === item.ma_mat_hang || x.sku === item.sku),
    )
  )
    throw new Error("Mã hoặc SKU đã tồn tại, kể cả mặt hàng ngừng hoạt động.");
  const old = db.items.find((x) => x.id === item.id);
  if (
    old &&
    referenced(db, old.id) &&
    ["ma_mat_hang", "sku", "loai_mat_hang", "don_vi_tinh"].some(
      (k) => old[k as keyof Item] !== item[k as keyof Item],
    )
  )
    throw new Error("Mặt hàng đã được tham chiếu: không thể đổi mã, SKU, loại hoặc đơn vị.");
  if (old) Object.assign(old, item);
  else db.items.unshift(item);
}
export function adjustmentLines(
  db: Database,
  values: { source: number; quantity: number }[],
  receipt: number,
): AdjustmentLine[] {
  if (!values.length) throw new Error("Chọn ít nhất một dòng cần điều chỉnh.");
  if (new Set(values.map((x) => x.source)).size !== values.length)
    throw new Error("Không chọn trùng giao dịch gốc.");
  return values.map(({ source, quantity }) => {
    const entry = db.ledger.find(
      (x) => x.id === source && x.source_id === receipt && x.loai_giao_dich === "nhap_vat_tu",
    );
    if (!entry) throw new Error("Giao dịch không thuộc phiếu nhập nguồn.");
    if (!Number.isSafeInteger(quantity) || quantity < 0)
      throw new Error("Số lượng đúng phải là số nguyên không âm.");
    if (!db.items.find((x) => x.id === entry.mat_hang_id)?.is_active)
      throw new Error("Mặt hàng đã ngừng hoạt động.");
    const before = effective(db, source);
    if (quantity === before) throw new Error("Bỏ chọn dòng không có chênh lệch.");
    return {
      mat_hang_id: entry.mat_hang_id,
      giao_dich_goc_id: source,
      so_luong_hieu_luc_truoc: before,
      so_luong_dung: quantity,
      so_luong_bien_dong: quantity - before,
    };
  });
}
export function confirmAdjustment(db: Database, role: Role, id: number) {
  const entry = db.adjustments.find((x) => x.id === id);
  if (role !== "Q" || !entry || entry.trang_thai !== "nhap")
    throw new Error("Chỉ quản lý được xác nhận phiếu nháp.");
  const lines = adjustmentLines(
    db,
    entry.chi_tiet.map((x) => ({ source: x.giao_dich_goc_id, quantity: x.so_luong_dung })),
    entry.phieu_nhap_id,
  );
  const totals = new Map<number, number>();
  lines.forEach((x) =>
    totals.set(x.mat_hang_id, (totals.get(x.mat_hang_id) || 0) + x.so_luong_bien_dong),
  );
  entry.chi_tiet = lines;
  if ([...totals].some(([item, delta]) => stock(db, item) + delta < 0)) {
    entry.trang_thai = "loi";
    const ticket = db.nextTicketId++;
    entry.ticket_id = ticket;
    db.tickets.push({
      id: ticket,
      ma_ticket: `TKDC-202611-${String(ticket - 400).padStart(6, "0")}`,
      phieu_nhap_id: entry.phieu_nhap_id,
      trang_thai: "cho_xu_ly",
      mo_ta_loi: "Không đủ tồn để điều chỉnh giảm. Toàn bộ phiếu chưa ghi sổ.",
      created_at: new Date().toISOString(),
      chi_tiet: structuredClone(lines),
    });
    return "Điều chỉnh thất bại. Đã lưu ticket demo; tồn kho giữ nguyên.";
  }
  entry.trang_thai = "da_xac_nhan";
  entry.confirmed_at = new Date().toISOString();
  lines.forEach((x) =>
    db.ledger.push({
      id: Math.max(500, ...db.ledger.map((l) => l.id)) + 1,
      mat_hang_id: x.mat_hang_id,
      so_luong_bien_dong: x.so_luong_bien_dong,
      loai_giao_dich: "dieu_chinh_ton_kho",
      source: entry.ma_phieu,
      source_id: entry.id,
      nhan_vien_id: 10,
      posted_at: entry.confirmed_at!,
    }),
  );
  return "Đã xác nhận và ghi sổ toàn bộ chênh lệch.";
}
export type OrderAction = "assign" | "send" | "start" | "cancel";
export function orderBlock(db: Database, role: Role, order: Order, action: OrderAction): string {
  if (action === "start")
    return role !== "N" || order.nhan_vien_id !== 21
      ? "Chỉ nhân viên được giao mới được bắt đầu."
      : order.trang_thai !== "da_gui"
        ? "Chỉ bắt đầu lệnh đã gửi."
        : order.vat_tu.some((x) => x.so_luong_da_cap < x.so_luong_can)
          ? "Chưa được cấp đủ vật tư."
          : "";
  if (role !== "Q") return "Thao tác dành cho quản lý.";
  if (action === "assign" || action === "send") {
    if (order.trang_thai !== "nhap") return "Chỉ thao tác khi lệnh còn nháp.";
    if (action === "send" && !order.nhan_vien_id) return "Cần giao người thực hiện trước khi gửi.";
    if (action === "send" && !db.items.find((x) => x.id === order.mat_hang_id)?.is_active)
      return "Mặt hàng đầu ra đã ngừng hoạt động.";
    return "";
  }
  if (["hoan_thanh", "da_huy"].includes(order.trang_thai)) return "Lệnh đã kết thúc.";
  if (order.so_luong_da_hoan_thanh || order.vat_tu.some((x) => x.so_luong_da_cap > 0))
    return "Không thể hủy: đã có vật tư hoặc đầu ra ghi sổ.";
  if (
    db.orders.some(
      (x) =>
        x.lenh_san_xuat_cha_id === order.id && !["hoan_thanh", "da_huy"].includes(x.trang_thai),
    )
  )
    return "Không thể hủy: còn lệnh con hoạt động.";
  return "";
}
export function changeOrder(
  db: Database,
  role: Role,
  id: number,
  action: OrderAction,
  value: string,
) {
  const order = db.orders.find((x) => x.id === id);
  if (!order) throw new Error("Không tìm thấy lệnh.");
  const reason = orderBlock(db, role, order, action);
  if (reason) throw new Error(reason);
  if (action === "assign") {
    if (value && !["21", "22", "23"].includes(value))
      throw new Error("Người thực hiện không hợp lệ.");
    order.nhan_vien_id = value ? Number(value) : null;
  } else if (action === "send") order.trang_thai = "da_gui";
  else if (action === "start") {
    order.trang_thai = "dang_thuc_hien";
    order.started_at = new Date().toISOString();
  } else {
    if (!value.trim()) throw new Error("Nhập lý do hủy.");
    order.trang_thai = "da_huy";
    order.ly_do_huy = value.trim();
  }
}
