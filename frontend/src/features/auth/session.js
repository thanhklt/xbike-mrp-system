import { TOKEN_KEY } from "../../lib/api/client.js";

// UC-02 Đăng xuất — Main 2, A2: xóa token, hủy truy vấn và xóa cache (specs/use_cases/identity_access/UC-02.md)
export function clearSession({ storage, queryClient }) {
  storage.removeItem(TOKEN_KEY);
  queryClient.cancelQueries();
  queryClient.removeQueries();
}

// UC-02 Đăng xuất — R1, A1, A2: xác định quyền vào trang theo phiên hiện tại (specs/use_cases/identity_access/UC-02.md)
export function sessionGate({ token, user, isPending, isError }) {
  if (!token) return "login";
  if (!user && isPending) return "checking";
  if (isError) return "error";
  return user ? "allow" : "login";
}
