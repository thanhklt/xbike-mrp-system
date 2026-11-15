import { createContext, useContext, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { API } from "../../lib/api/endpoints.js";
import { readResource, TOKEN_KEY, writeResource } from "../../lib/api/client.js";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import { clearSession } from "./session.js";
const AuthContext = createContext(null);
// UC-02 Đăng xuất — Main 1–3, R1: cung cấp phiên và thao tác đăng xuất (specs/use_cases/identity_access/UC-02.md)
export const useAuth = () => useContext(AuthContext);

// UC-02 Đăng xuất — Main 2, A2: quản lý và kết thúc phiên phía client (specs/use_cases/identity_access/UC-02.md)
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const { notify, dismissConfirmation } = useFeedback();
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const session = useQuery({
    queryKey: ["session"],
    queryFn: ({ signal }) => readResource(API.me, {}, signal),
    enabled: Boolean(token),
    retry: false,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
  // UC-02 Đăng xuất — Main 2, A2: kết thúc phiên kể cả khi đã hết hiệu lực (specs/use_cases/identity_access/UC-02.md)
  function logout(message) {
    dismissConfirmation();
    clearSession({ storage: localStorage, queryClient });
    setToken(null);
    if (message) notify(message);
  }
  useEffect(() => {
    // UC-02 Đăng xuất — A2: kết thúc phiên khi API từ chối xác thực (specs/use_cases/identity_access/UC-02.md)
    const end = (event) => logout(event.detail);
    // UC-02 Đăng xuất — R1, A1: đồng bộ phiên thay đổi ở tab khác (specs/use_cases/identity_access/UC-02.md)
    const synchronize = (event) => {
      if (event.key === TOKEN_KEY) {
        dismissConfirmation();
        queryClient.cancelQueries();
        queryClient.removeQueries();
        setToken(event.newValue);
      }
    };
    window.addEventListener("xbike:session-ended", end);
    window.addEventListener("storage", synchronize);
    return () => {
      window.removeEventListener("xbike:session-ended", end);
      window.removeEventListener("storage", synchronize);
    };
  });
  async function login(credentials) {
    const result = await writeResource({ path: API.login, body: credentials, versioned: false });
    queryClient.removeQueries();
    localStorage.setItem(TOKEN_KEY, result.data.access_token);
    setToken(result.data.access_token);
    // /auth/me remains the source of role and account state after login.
    const currentSession = await queryClient.fetchQuery({
      queryKey: ["session"],
      queryFn: ({ signal }) => readResource(API.me, {}, signal),
    });
    return currentSession.data;
  }
  const user = token ? session.data?.data : null;
  return (
    <AuthContext.Provider value={{ token, user, session, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
