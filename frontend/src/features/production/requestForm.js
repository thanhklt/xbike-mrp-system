import { dateFilters } from "../../components/filterFields.js";
import {
  dateTime,
  employeeDisplayName,
  employeeName,
  formatDate,
  itemName,
  number,
  STATUS_LABELS,
  unitLabel,
} from "../../lib/format.js";

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

export const REQUEST_WORK_STATUSES = [
  { value: "da_giao", label: "Đã giao", tone: "work-assigned" },
  { value: "cho_duyet_xuat_linh_kien", label: "Chờ duyệt phiếu xuất linh kiện", tone: "work-issue" },
  { value: "san_sang_san_xuat", label: "Sẵn sàng sản xuất", tone: "work-production" },
  { value: "dang_san_xuat", label: "Đang sản xuất", tone: "work-production" },
  { value: "cho_duyet_hoan_thanh", label: "Chờ duyệt chứng từ hoàn thành", tone: "work-completion" },
  { value: "cho_lap_phieu_xuat", label: "Chờ lập phiếu xuất", tone: "work-issue" },
  { value: "cho_duyet_phieu_xuat", label: "Chờ duyệt phiếu xuất", tone: "work-issue" },
  { value: "hoan_thanh", label: "Hoàn thành", tone: "work-completed" },
  { value: "da_huy", label: "Đã hủy", tone: "work-cancelled" },
];

export function requestWorkStatus(record) {
  return REQUEST_WORK_STATUSES.find(({ value }) => value === record?.trang_thai_cong_viec);
}

// UC-25 Xem danh sách yêu cầu sản xuất — Main 2–3; A1, A3 (specs/use_cases/production/UC-25.md)
export function requestListFilters(manager) {
  const statuses = [
    "nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy",
  ].filter((status) => manager || status !== "nhap");
  return [
    {
      name: manager ? "trang_thai" : "trang_thai_cong_viec",
      label: "Trạng thái",
      as: "select",
      options: [
        { value: "", label: "Tất cả" },
        ...(manager ? statuses.map((value) => ({ value, label: STATUS_LABELS[value] }))
          : REQUEST_WORK_STATUSES.map(({ value, label }) => ({ value, label }))),
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
    ["Đơn vị tính", unitLabel(item?.don_vi_tinh)],
    ["Hạn hoàn thành", formatDate(values.han_hoan_thanh)],
    ["Nhân viên được giao", employeeName(employees, values.nhan_vien_duoc_giao_id)],
  ];
}

// UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — Main 2 thông tin chỉ đọc (specs/use_cases/production/UC-24.md)
// UC-28 Hủy yêu cầu sản xuất — D5 thông tin hủy trong chi tiết (specs/use_cases/production/UC-28.md)
export function requestDetailEntries(record, items, employees, currentUser = null) {
  const current = currentUser || employees?.find((e) => e?.isCurrentUser);
  const isEmployee = Boolean(current);
  const item = items.find((entry) => entry.id === Number(record.mat_hang_id));
  const productText =
    isEmployee && item?.ma_mat_hang
      ? `${item.ten_mat_hang} — ${item.ma_mat_hang}`
      : itemName(items, record.mat_hang_id);
  const assignedText = isEmployee
    ? employeeDisplayName(employees, record.nhan_vien_duoc_giao_id, "Chưa giao", current)
    : employeeName(employees, record.nhan_vien_duoc_giao_id);
  const creator = employees?.find((employee) => Number(employee.id) === Number(record.nhan_vien_id));
  const creatorText = employeeDisplayName([{
    id: record.nhan_vien_id,
    ho_ten: record.nguoi_lap_ho_ten || creator?.ho_ten,
    ma_nhan_vien: record.nguoi_lap_ma_nhan_vien || creator?.ma_nhan_vien,
  }], record.nhan_vien_id, "—");
  return [
    ["Loại yêu cầu", REQUEST_TYPE_LABELS[record.loai_yeu_cau]],
    ["Thành phẩm", productText],
    ["Số lượng cần", number(record.so_luong)],
    ["Đơn vị tính", unitLabel(item?.don_vi_tinh)],
    ["Hạn hoàn thành", formatDate(record.han_hoan_thanh)],
    ["Nhân viên được giao", assignedText],
    ["Người lập", creatorText],
    ["Tạo lúc", dateTime(record.created_at)],
    ["Gửi lúc", dateTime(record.gui_at)],
    ...(record.kiem_tra_lan_dau_at ? [
      ...(record.loai_yeu_cau === "xuat_giao"
        ? [["Thành phẩm dùng từ kho", number(record.so_luong_dung_thanh_pham)]] : []),
      ["Số cần sản xuất", number(record.so_luong_can_san_xuat)],
      ["Kiểm tra lần đầu lúc", dateTime(record.kiem_tra_lan_dau_at)],
    ] : []),
    // UC-29 Bắt đầu sản xuất — Main 5 hiển thị thời điểm đã ghi (specs/use_cases/production/UC-29.md)
    ...(record.started_at ? [["Bắt đầu sản xuất lúc", dateTime(record.started_at)]] : []),
    ["Hoàn thành lúc", dateTime(record.completed_at)],
    ...(record.trang_thai === "da_huy" ? [
      ["Hủy lúc", dateTime(record.huy_at)],
      ["Người hủy", employeeName(employees, record.nguoi_huy_id)],
      ["Lý do hủy", record.ly_do_huy],
    ] : []),
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

export function canCheckRequest(record, manager, userId) {
  return Boolean(!manager && record && record.nhan_vien_duoc_giao_id === Number(userId)
    && ["da_gui", "cho_bo_sung_linh_kien"].includes(record.trang_thai));
}

// UC-29 Bắt đầu sản xuất — Main 1–2; D5 chỉ NV được giao và chưa bắt đầu (specs/use_cases/production/UC-29.md)
export function canStartProduction(record, manager, userId) {
  return Boolean(!manager && record && record.nhan_vien_duoc_giao_id === Number(userId)
    && record.trang_thai === "dang_thuc_hien" && record.so_luong_can_san_xuat > 0
    && record.trang_thai_cong_viec === "san_sang_san_xuat"
    && !record.started_at);
}

export const unitCell = (row) => unitLabel(row.don_vi_tinh);

export const CANCEL_HOLD_COLUMNS = [
  { key: "ma_mat_hang", label: "Mã" },
  { key: "ten_mat_hang", label: "Tên" },
  { key: "don_vi_tinh", label: "Đơn vị tính", render: unitCell },
  { key: "loai_giu", label: "Loại giữ" },
  { key: "so_luong", label: "Số lượng", numeric: true },
];

export const CANCEL_ISSUE_COLUMNS = [
  { key: "ma_phieu_xuat", label: "Mã phiếu" },
  { key: "loai_phieu", label: "Loại phiếu" },
  { key: "trang_thai", label: "Trạng thái" },
  { key: "xu_ly", label: "Xử lý" },
];

// UC-28 Hủy yêu cầu sản xuất — Main 4; D4 nội dung xác nhận hàng trả và phiếu bị ảnh hưởng (specs/use_cases/production/UC-28.md)
export function cancelConfirmEntries(preview) {
  const holdLabels = {
    thanh_pham_co_san: "Thành phẩm có sẵn",
    linh_kien: "Linh kiện",
    thanh_pham_san_xuat: "Thành phẩm sản xuất",
  };
  const issueLabels = {
    xuat_linh_kien: "Xuất linh kiện",
    xuat_thanh_pham: "Xuất thành phẩm",
  };
  return {
    hang_tra: preview.hang_tra.map((line) => ({
      ...line, loai_giu: holdLabels[line.loai_giu], so_luong: number(line.so_luong),
    })),
    phieu_xuat: preview.phieu_xuat.map((line) => ({
      ...line, loai_phieu: issueLabels[line.loai_phieu], trang_thai: STATUS_LABELS[line.trang_thai],
      xu_ly: line.xu_ly === "bo" ? "Bỏ phiếu nháp" : "Từ chối: Yêu cầu đã hủy",
    })),
  };
}

// UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 4; A7 thông tin xác nhận (specs/use_cases/production/UC-26.md)
export function checkConfirmEntries(ketQua, loai) {
  return [
    ...(loai === "xuat_giao"
      ? [["Thành phẩm dùng từ kho", number(ketQua.so_luong_dung_thanh_pham)]] : []),
    ["Số cần sản xuất", number(ketQua.so_luong_can_san_xuat)],
    ["Linh kiện", ketQua.du_linh_kien ? "Đủ" : "Thiếu"],
  ];
}

export const CHECK_COLUMNS = [
  { key: "ma_mat_hang", label: "Mã" },
  { key: "ten_mat_hang", label: "Tên" },
  { key: "don_vi_tinh", label: "Đơn vị tính", render: unitCell },
  { key: "so_luong_can", label: "Cần", numeric: true },
  { key: "so_luong_con_dung", label: "Còn dùng được", numeric: true },
  { key: "so_luong_thieu", label: "Thiếu", numeric: true },
];

// UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 4, 8; A2 báo thiếu R10 (specs/use_cases/production/UC-26.md)
export function checkLines(ketQua) {
  return ketQua.linh_kien.map((line) => ({ ...line, id: line.mat_hang_id }));
}
