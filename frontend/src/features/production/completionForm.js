import { dateTime, employeeLabel, itemName, number, unitLabel } from "../../lib/format.js";
import { dateFilters } from "../../components/filterFields.js";
import { REQUEST_TYPES, REQUEST_TYPE_LABELS } from "./requestForm.js";

// UC-33 Xem danh sách chứng từ hoàn thành sản xuất — Main 3–4; R2 lọc loại, thành phẩm, nhân viên và ngày (specs/use_cases/production/UC-33.md)
export function completionListFilters(items, employees) {
  return [
    {
      name: "loai_yeu_cau", label: "Loại yêu cầu", as: "select",
      options: [{ value: "", label: "Tất cả" }, ...REQUEST_TYPES],
    },
    {
      name: "mat_hang_id", label: "Thành phẩm", as: "select",
      options: [{ value: "", label: "Tất cả" }, ...items
        .filter((item) => item.loai_mat_hang === "thanh_pham")
        .map((item) => ({ value: String(item.id), label: itemName(items, item.id) }))],
    },
    {
      name: "nhan_vien_id", label: "Nhân viên", as: "select",
      options: [{ value: "", label: "Tất cả" }, ...employees
        .map((employee) => ({ value: String(employee.id), label: employeeLabel(employee) }))],
    },
    ...dateFilters,
  ];
}

export function canCreateCompletion(record, completion, manager, userId) {
  return Boolean(record && !completion && !manager
    && Number(record.nhan_vien_duoc_giao_id) === Number(userId)
    && record.trang_thai === "dang_thuc_hien" && record.started_at
    && record.so_luong_can_san_xuat > 0);
}

export function canSendCompletion(record, completion, manager, userId) {
  return Boolean(record && completion && !manager
    && Number(record.nhan_vien_duoc_giao_id) === Number(userId)
    && record.trang_thai === "dang_thuc_hien"
    && ["nhap", "tu_choi"].includes(completion.trang_thai));
}

export function completionSendLabel(completion) {
  return completion.trang_thai === "tu_choi" ? "Gửi lại" : "Gửi";
}

export function completionEntries(completion) {
  return [
    ["Mã chứng từ", completion.ma_phieu],
    ["Trạng thái", completion.trang_thai],
    ["Số lượng hoàn thành", number(completion.so_luong_hoan_thanh)],
    ["Thời điểm hoàn thành", dateTime(completion.finish_time)],
    ...(completion.ly_do_tu_choi ? [["Lý do từ chối", completion.ly_do_tu_choi]] : []),
  ];
}

// UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 7; A3 nội dung xác nhận (specs/use_cases/production/UC-30.md)
export function completionConfirmEntries(completion, record, items) {
  const item = items.find((entry) => Number(entry.id) === Number(record.mat_hang_id));
  return [
    ["Mã chứng từ", completion.ma_phieu],
    ["Thành phẩm", itemName(items, record.mat_hang_id)],
    ["Số lượng hoàn thành", number(completion.so_luong_hoan_thanh)],
    ["Đơn vị tính", unitLabel(item?.don_vi_tinh || null)],
  ];
}

export function canApproveCompletion(completion, record, manager) {
  return Boolean(manager && completion?.trang_thai === "cho_duyet"
    && record?.trang_thai === "dang_thuc_hien");
}

// UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 3 năm dòng xác nhận (specs/use_cases/production/UC-31.md)
export function approveConfirmEntries(completion, record, items) {
  const [document, ...details] = completionConfirmEntries(completion, record, items);
  return [document, ["Loại yêu cầu", REQUEST_TYPE_LABELS[record.loai_yeu_cau]], ...details];
}

// UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 3 tác động tồn và giữ theo loại yêu cầu (specs/use_cases/production/UC-31.md)
export function approveImpact(completion, record) {
  const quantity = number(completion.so_luong_hoan_thanh);
  return record.loai_yeu_cau === "xuat_giao"
    ? `Tồn thành phẩm tăng ${quantity}; ${quantity} xe được giữ cho yêu cầu này.`
    : `Tồn thành phẩm tăng ${quantity}; ${quantity} xe còn dùng được; yêu cầu chuyển Hoàn thành.`;
}
