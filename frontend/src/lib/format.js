export const ROLE_LABELS = {
  quan_tri_vien: "Quản trị viên",
  quan_ly: "Quản lý kho",
  nhan_vien: "Nhân viên",
};
export const ITEM_LABELS = {
  nguyen_vat_lieu: "Nguyên vật liệu",
  linh_kien: "Linh kiện",
  ban_thanh_pham: "Bán thành phẩm",
  thanh_pham: "Thành phẩm",
};
export const STATUS_LABELS = {
  nhap: "Bản nháp",
  da_gui: "Đã giao",
  cho_duyet: "Chờ duyệt",
  dang_thuc_hien: "Đang thực hiện",
  hoan_thanh: "Hoàn thành",
  da_duyet: "Đã duyệt",
  tu_choi: "Từ chối",
  da_huy: "Đã hủy",
  cho_bo_sung_vat_tu: "Chờ bổ sung vật tư",
  da_xac_nhan: "Đã xác nhận",
  loi: "Lỗi",
  cho_xu_ly: "Chờ xử lý",
  dang_xu_ly: "Đang xử lý",
  da_xu_ly: "Đã xử lý",
  hoat_dong: "Hoạt động",
  bi_khoa: "Bị khóa",
};
export const number = (value) =>
  value === null || value === undefined ? "—" : new Intl.NumberFormat("vi-VN").format(value);
export const money = (value) =>
  value === null || value === undefined ? "Chưa chốt" : `${number(value)} ₫`;
export function dateTime(value) {
  if (!value) return "—";
  const instant = new Date(value);
  return Number.isNaN(instant.valueOf())
    ? "—"
    : new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(instant);
}
export function localDateTime(value = new Date()) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(new Date(value))
      .map((part) => [part.type, part.value]),
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}
export const today = () => localDateTime().slice(0, 10);
export const nullable = (value) => value?.trim() || null;
export const itemName = (items, id) =>
  items?.find((item) => item.id === Number(id))?.ten_mat_hang || `Mặt hàng #${id}`;
export const employeeName = (employees, id) =>
  id === null || id === undefined
    ? "Chưa giao"
    : employees?.find((employee) => employee.id === Number(id))?.ho_ten || `Nhân viên #${id}`;

export function initials(name = "") {
  return String(name)
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join("")
    .toUpperCase() || "NV";
}

export function formatDate(value) {
  if (!value) return "—";
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-");
    return `${day}/${month}/${year}`;
  }
  const instant = new Date(value);
  return Number.isNaN(instant.valueOf())
    ? "—"
    : new Intl.DateTimeFormat("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(instant);
}

export function formatCoefficient(value) {
  if (value === null || value === undefined || value === "") return "—";
  const parsed = Number(value);
  return Number.isNaN(parsed) ? String(value) : parsed.toFixed(2);
}

export function formatAuditTime(value) {
  if (!value) return "—";
  const instant = new Date(value);
  if (Number.isNaN(instant.valueOf())) return "—";
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(instant)
      .map((part) => [part.type, part.value]),
  );
  return `${parts.hour}:${parts.minute} - ${parts.day}/${parts.month}/${parts.year}`;
}
