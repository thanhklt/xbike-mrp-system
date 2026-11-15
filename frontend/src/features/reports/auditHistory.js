import { dateTime } from "../../lib/format.js";
import { auditActionLabel, auditObjectLabel } from "../dashboard/auditFormat.js";

// UC-43 Xem lịch sử thao tác — Main 3–4; R5: chọn thao tác (specs/use_cases/audit/UC-43.md)
export const AUDIT_ACTION_OPTIONS = [
  "dang_nhap",
  "tao",
  "sua",
  "xoa_nhap",
  "gui",
  "gui_lai",
  "kiem_tra",
  "bat_dau",
  "duyet",
  "tu_choi",
  "hoan_tat",
  "huy",
  "khoa",
  "mo_khoa",
  "doi_vai_tro",
  "doi_mat_khau",
  "ngung",
  "dung_lai",
  "tao_phien_ban",
  "dung_lai_phien_ban",
].map((value) => ({ value, label: auditActionLabel(value) }));

// UC-43 Xem lịch sử thao tác — Main 3–4; R5: chọn loại đối tượng (specs/use_cases/audit/UC-43.md)
export const AUDIT_OBJECT_OPTIONS = [
  "nhan_vien",
  "mat_hang",
  "nha_cung_cap",
  "cong_thuc",
  "phieu_nhap",
  "phieu_xuat",
  "yeu_cau_san_xuat",
  "chung_tu_hoan_thanh_san_xuat",
].map((value) => ({ value, label: auditObjectLabel(value) }));

// UC-43 Xem lịch sử thao tác — Main 2–4: sắp xếp danh sách (specs/use_cases/audit/UC-43.md)
export const AUDIT_SORT_OPTIONS = [
  { value: "-created_at", label: "Mới nhất" },
  { value: "created_at", label: "Cũ nhất" },
  { value: "-id", label: "ID giảm dần" },
  { value: "id", label: "ID tăng dần" },
];

// ResourceFields.jsx contains JSX; keep equivalent date filters importable by node --test.
const dateFilters = [
  { name: "tu_ngay", label: "Từ ngày", type: "date" },
  { name: "den_ngay", label: "Đến ngày", type: "date" },
];

// UC-43 Xem lịch sử thao tác — Main 3–4; R5: kết hợp bộ lọc (specs/use_cases/audit/UC-43.md)
export function auditFilters(employees = []) {
  return [
    {
      name: "loai_doi_tuong",
      label: "Loại đối tượng",
      as: "select",
      options: [{ value: "", label: "Tất cả" }, ...AUDIT_OBJECT_OPTIONS],
    },
    { name: "doi_tuong_id", label: "ID đối tượng", type: "number", min: 1, step: 1 },
    {
      name: "nhan_vien_id",
      label: "Người thực hiện",
      as: "select",
      options: [
        { value: "", label: "Tất cả" },
        ...employees.map((employee) => ({
          value: employee.id,
          label: auditActorLabel(employees, employee.id),
        })),
      ],
    },
    {
      name: "thao_tac",
      label: "Thao tác",
      as: "select",
      options: [{ value: "", label: "Tất cả" }, ...AUDIT_ACTION_OPTIONS],
    },
    ...dateFilters,
    { name: "sort", label: "Sắp xếp", as: "select", options: AUDIT_SORT_OPTIONS },
  ];
}

// UC-43 Xem lịch sử thao tác — Main 2, 6: nhãn người thực hiện (specs/use_cases/audit/UC-43.md)
export function auditActorLabel(employees, id) {
  const employee = employees.find((person) => person.id === Number(id));
  return employee
    ? `${employee.ma_nhan_vien} · ${employee.ho_ten || "Chưa có họ tên"}`
    : `Nhân viên #${id}`;
}

// UC-43 Xem lịch sử thao tác — Main 5–6; R2, R3, R6: thông tin bản ghi (specs/use_cases/audit/UC-43.md)
export function auditDetailEntries(record, employees = []) {
  return [
    ["Thời gian", dateTime(record.created_at)],
    ["Người thực hiện", auditActorLabel(employees, record.nhan_vien_id)],
    ["Đối tượng", `${auditObjectLabel(record.loai_doi_tuong)} #${record.doi_tuong_id}`],
    ["Thao tác", auditActionLabel(record.thao_tac)],
    ["Trạng thái trước", record.trang_thai_truoc],
    ["Trạng thái sau", record.trang_thai_sau],
    ["Lý do", record.ly_do],
  ];
}

// UC-43 Xem lịch sử thao tác — Main 6; R4: danh sách thiếu đã lưu (specs/use_cases/audit/UC-43.md)
export function auditShortageRows(record) {
  const rows = record.du_lieu_sau?.danh_sach_thieu;
  return Array.isArray(rows) ? rows : [];
}
