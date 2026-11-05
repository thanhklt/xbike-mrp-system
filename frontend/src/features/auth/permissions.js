export const ROLE_HOME = { quan_tri_vien: "/admin", quan_ly: "/kho", nhan_vien: "/nv" };
export const homeFor = (role) => ROLE_HOME[role] || "/403";
export const isAllowed = (role, allowed) => allowed.includes(role);
export function documentPermissions(kind, role, document, userId) {
  const manager = role === "quan_ly";
  const ownCompletion =
    kind === "completion" && role === "nhan_vien" && document?.nhan_vien_id === userId;
  const writer = kind === "issue" ? manager : ownCompletion;
  return {
    create: kind === "issue" ? manager : role === "nhan_vien",
    edit: writer && document?.trang_thai === "nhap",
    send: writer && document?.trang_thai === "nhap",
    approve: manager && document?.trang_thai === "cho_duyet",
    reject: manager && document?.trang_thai === "cho_duyet",
    returnDraft: writer && document?.trang_thai === "tu_choi",
  };
}
