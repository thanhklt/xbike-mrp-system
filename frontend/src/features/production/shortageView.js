import { dateTime, employeeName, formatDate, itemName, number } from "../../lib/format.js";
import { CHECK_COLUMNS, REQUEST_TYPE_LABELS } from "./requestForm.js";

export const SHORTAGE_COLUMNS = CHECK_COLUMNS;
export const SUMMARY_COLUMNS = [
  ...CHECK_COLUMNS.slice(0, 3),
  { key: "tong_can", label: "Tổng cần", numeric: true },
  ...CHECK_COLUMNS.slice(4),
  { key: "so_yeu_cau", label: "Số yêu cầu", numeric: true },
];

// UC-27 Xem nhu cầu bổ sung linh kiện — Main 2–3 dựng dòng bảng với id linh kiện (specs/use_cases/production/UC-27.md)
export function shortageRows(lines) {
  return lines.map((line) => ({ ...line, id: line.mat_hang_id }));
}

// UC-27 Xem nhu cầu bổ sung linh kiện — Main 2; D5 thông tin yêu cầu đang chờ (specs/use_cases/production/UC-27.md)
export function shortageRequestEntries(record, items, employees) {
  return [
    ["Thành phẩm", itemName(items, record.mat_hang_id)],
    ["Loại yêu cầu", REQUEST_TYPE_LABELS[record.loai_yeu_cau]],
    ["Số cần sản xuất", number(record.so_luong_can_san_xuat)],
    ["Hạn hoàn thành", formatDate(record.han_hoan_thanh)],
    ["Nhân viên được giao", employeeName(employees, record.nhan_vien_duoc_giao_id)],
    ["Kiểm tra lần đầu lúc", dateTime(record.kiem_tra_lan_dau_at)],
  ];
}
