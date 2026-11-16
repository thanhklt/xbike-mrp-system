import { ITEM_LABELS } from "../../lib/format.js";

export const REPORT_ITEM_TYPES = ["linh_kien", "thanh_pham"].map((value) => ({
  value,
  label: ITEM_LABELS[value],
}));

// UC-41 Xem báo cáo nhập-xuất-tồn — Main 2; R1 (specs/use_cases/reporting/UC-41.md)
export function defaultReportForm(now = new Date()) {
  return {
    ky: "thang",
    nam: now.getFullYear(),
    thang: now.getMonth() + 1,
    quy: Math.floor(now.getMonth() / 3) + 1,
    mat_hang_id: "",
    loai_mat_hang: "",
  };
}

// UC-41 Xem báo cáo nhập-xuất-tồn — Main 2; R1, R2 (specs/use_cases/reporting/UC-41.md)
export function reportQuery(form) {
  return {
    ky: form.ky,
    nam: Number(form.nam),
    ...(form.ky === "thang" ? { thang: Number(form.thang) } : {}),
    ...(form.ky === "quy" ? { quy: Number(form.quy) } : {}),
    ...(form.mat_hang_id ? { mat_hang_id: Number(form.mat_hang_id) } : {}),
    ...(form.loai_mat_hang ? { loai_mat_hang: form.loai_mat_hang } : {}),
  };
}

// UC-41 Xem báo cáo nhập-xuất-tồn — Main 4; R1 (specs/use_cases/reporting/UC-41.md)
export function periodLabel(form) {
  if (form.ky === "thang") return `Tháng ${form.thang}/${form.nam}`;
  if (form.ky === "quy") return `Quý ${form.quy}/${form.nam}`;
  return `Năm ${form.nam}`;
}
