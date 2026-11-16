import { dateFilters } from "../../components/filterFields.js";
import { dateTime, employeeName, formatDate, itemName, number, STATUS_LABELS } from "../../lib/format.js";

export const REQUEST_TYPES = [
  { value: "xuat_giao", label: "Sản xuất để xuất giao" },
  { value: "nhap_kho", label: "Sản xuất nhập kho" },
];
export const REQUEST_TYPE_LABELS = Object.fromEntries(
  REQUEST_TYPES.map(({ value, label }) => [value, label]),
);

export const REQUEST_SORT_OPTIONS = [
  { value: "", label: "Mặc định" },
  { value: "han_hoan_thanh", label: "Hạn hoàn thành gần nhất" },
  { value: "-han_hoan_thanh", label: "Hạn hoàn thành xa nhất" },
  { value: "-created_at", label: "Mới nhất trước" },
  { value: "created_at", label: "Cũ nhất trước" },
];

// UC-25 Xem danh sách yêu cầu sản xuất — Main 2–3; A1, A3 (specs/use_cases/production/UC-25.md)
export function requestListFilters(manager) {
  const statuses = [
    "nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy",
  ].filter((status) => manager || status !== "nhap");
  return [
    {
      name: "trang_thai",
      label: "Trạng thái",
      as: "select",
      options: [
        { value: "", label: "Tất cả" },
        ...statuses.map((value) => ({ value, label: STATUS_LABELS[value] })),
      ],
    },
    {
      name: "loai_yeu_cau",
      label: "Loại yêu cầu",
      as: "select",
      options: [{ value: "", label: "Tất cả" }, ...REQUEST_TYPES],
    },
    { name: "sort", label: "Sắp xếp", as: "select", options: REQUEST_SORT_OPTIONS },
    ...dateFilters,
  ];
}

// UC-23 Lập và gửi yêu cầu sản xuất — Main 1–3 (specs/use_cases/production/UC-23.md)
export function initialRequestValues(record) {
  return {
    loai_yeu_cau: record?.loai_yeu_cau ?? "xuat_giao",
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
