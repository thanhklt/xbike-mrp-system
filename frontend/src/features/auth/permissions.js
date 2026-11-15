export const ROLE_HOME = { quan_tri_vien: "/admin", quan_ly: "/kho", nhan_vien: "/nv" };
// UC-01 Đăng nhập — Main 6; R3 (specs/use_cases/identity_access/UC-01.md)
export const homeFor = (role) => (Object.hasOwn(ROLE_HOME, role) ? ROLE_HOME[role] : "/403");
export const isAllowed = (role, allowed) => allowed.includes(role);
// UC-03 Xem danh sách tài khoản — R1, A3: chặn truy cập trang quản trị theo vai trò (specs/use_cases/identity_access/UC-03.md)
export function canAccessPath(role, pathname) {
  const home = homeFor(role);
  return (
    home !== "/403" &&
    (pathname === "/ho-so" || pathname === home || pathname.startsWith(`${home}/`))
  );
}
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
