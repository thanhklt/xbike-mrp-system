import { STATUS_LABELS } from "../lib/format.js";
export function Badge({ status, children }) {
  const color = ["hoan_thanh", "da_duyet", "da_xac_nhan", "da_xu_ly", "hoat_dong"].includes(status)
    ? "green"
    : ["cho_duyet", "cho_bo_sung_vat_tu", "cho_xu_ly", "dang_xu_ly"].includes(status)
      ? "amber"
      : ["tu_choi", "loi", "bi_khoa", "da_huy"].includes(status)
        ? "red"
        : "blue";
  return (
    <span className={`badge badge-${color}`}>{children || STATUS_LABELS[status] || status}</span>
  );
}
