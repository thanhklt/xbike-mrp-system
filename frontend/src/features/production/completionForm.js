import { dateTime, itemName, number } from "../../lib/format.js";

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
    ["Đơn vị tính", item?.don_vi_tinh || "—"],
  ];
}
