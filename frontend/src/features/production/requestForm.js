import { dateTime, employeeName, formatDate, itemName, number } from "../../lib/format.js";

export const REQUEST_TYPES = [
  { value: "dap_ung", label: "Đáp ứng yêu cầu" },
  { value: "cho_kho", label: "Sản xuất cho kho" },
];
export const REQUEST_TYPE_LABELS = Object.fromEntries(
  REQUEST_TYPES.map(({ value, label }) => [value, label]),
);

// UC-23 Lập và gửi yêu cầu sản xuất — Main 1–3 (specs/use_cases/production/UC-23.md)
export function initialRequestValues(record) {
  return {
    loai_yeu_cau: record?.loai_yeu_cau ?? "dap_ung",
    mat_hang_id: String(record?.mat_hang_id ?? ""),
    so_luong: String(record?.so_luong ?? ""),
    han_hoan_thanh: record?.han_hoan_thanh ?? "",
    nhan_vien_duoc_giao_id: String(record?.nhan_vien_duoc_giao_id ?? ""),
  };
}

// UC-23 Lập và gửi yêu cầu sản xuất — Main 5; A1 (specs/use_cases/production/UC-23.md)
export function missingRequestFields(values) {
  return [
    "loai_yeu_cau",
    "mat_hang_id",
    "so_luong",
    "han_hoan_thanh",
    "nhan_vien_duoc_giao_id",
  ].filter(
    (name) =>
      values[name] === null || values[name] === undefined || String(values[name]).trim() === "",
  );
}

// UC-23 Lập và gửi yêu cầu sản xuất — Main 4–5 (specs/use_cases/production/UC-23.md)
export function requestCreateBody(values) {
  return {
    loai_yeu_cau: values.loai_yeu_cau,
    mat_hang_id: Number(values.mat_hang_id),
    so_luong: Number(values.so_luong),
    han_hoan_thanh: values.han_hoan_thanh,
    nhan_vien_duoc_giao_id: Number(values.nhan_vien_duoc_giao_id),
  };
}

// UC-23 Lập và gửi yêu cầu sản xuất — Main 6; R6 (specs/use_cases/production/UC-23.md)
export function sendConfirmEntries(values, items, employees) {
  const item = items.find((entry) => entry.id === Number(values.mat_hang_id));
  return [
    ["Loại yêu cầu", REQUEST_TYPE_LABELS[values.loai_yeu_cau]],
    ["Thành phẩm", itemName(items, values.mat_hang_id)],
    ["Số lượng cần", number(values.so_luong)],
    ["Đơn vị tính", item?.don_vi_tinh ?? "—"],
    ["Hạn hoàn thành", formatDate(values.han_hoan_thanh)],
    ["Nhân viên được giao", employeeName(employees, values.nhan_vien_duoc_giao_id)],
  ];
}

// UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — Main 2 thông tin chỉ đọc (specs/use_cases/production/UC-24.md)
export function requestDetailEntries(record, items, employees) {
  return [
    ...sendConfirmEntries(record, items, employees),
    ["Người lập", employeeName(employees, record.nhan_vien_id)],
    ["Tạo lúc", dateTime(record.created_at)],
    ["Gửi lúc", dateTime(record.gui_at)],
    ["Đã xuất / yêu cầu", `${number(record.so_luong_da_xuat)} / ${number(record.so_luong)}`],
    ["Còn phải xuất", number(record.so_luong_con_phai_xuat)],
    ["Hoàn thành lúc", dateTime(record.completed_at)],
  ];
}

// UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — R1, R8 quyền thao tác Nháp (specs/use_cases/production/UC-24.md)
export function canEditRequest(record, manager) {
  return Boolean(manager && record?.trang_thai === "nhap");
}

// UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — R4 Nháp chỉ xóa, không hủy (specs/use_cases/production/UC-24.md)
export function canCancelRequest(record, manager) {
  return Boolean(manager && record && !["nhap", "hoan_thanh", "da_huy"].includes(record.trang_thai));
}
