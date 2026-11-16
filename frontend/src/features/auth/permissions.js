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
export function documentPermissions(kind, role, document, userId, assignedId = document?.nhan_vien_id) {
  const manager = role === "quan_ly";
  const ownCompletion =
    kind === "completion" && role === "nhan_vien" && document?.nhan_vien_id === userId;
  const writer = kind === "issue" ? role === "nhan_vien" && assignedId === userId : ownCompletion;
  return {
    create: role === "nhan_vien",
    edit: false,
    send: writer && ["nhap", "tu_choi"].includes(document?.trang_thai),
    approve: manager && document?.trang_thai === "cho_duyet",
    reject: manager && document?.trang_thai === "cho_duyet",
    returnDraft: false,
  };
}
