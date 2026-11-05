import { createContext, useContext, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { API } from "../../lib/api/endpoints.js";
import { readResource, TOKEN_KEY, writeResource } from "../../lib/api/client.js";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

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
  function logout(message) {
    dismissConfirmation();
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    queryClient.cancelQueries();
    queryClient.removeQueries();
    if (message) notify(message);
  }
  useEffect(() => {
    const end = (event) => logout(event.detail);
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
