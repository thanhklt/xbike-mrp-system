import { Ban, CircleCheck, Crown, Layers, Users } from "lucide-react";
import { ROLE_LABELS, STATUS_LABELS } from "../lib/format.js";

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

export function AdminRoleBadge({ role, children }) {
  const code = role || "nhan_vien";
  const tone =
    code === "quan_tri_vien" ? "amber" : code === "quan_ly" ? "blue" : "neutral";
  const Icon =
    code === "quan_tri_vien" ? Crown : code === "quan_ly" ? Layers : Users;
  return (
    <span className={`admin-pill admin-pill-${tone}`}>
      <Icon size={15} strokeWidth={2} aria-hidden="true" />
      <span>{children || ROLE_LABELS[code] || code}</span>
    </span>
  );
}

export function AdminStatusBadge({ status, children }) {
  const active = status === "hoat_dong";
  const Icon = active ? CircleCheck : Ban;
  return (
    <span className={`admin-pill admin-pill-${active ? "green" : "red"}`}>
      <Icon size={15} strokeWidth={2} aria-hidden="true" />
      <span>{children || STATUS_LABELS[status] || status}</span>
    </span>
  );
}
