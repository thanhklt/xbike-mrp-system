import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { queryClient } from "../lib/query-client.js";
import { AuthProvider } from "../features/auth/AuthProvider.jsx";
import { FeedbackProvider } from "../components/FeedbackProvider.jsx";
import { AppRoutes } from "../routes/index.jsx";
import "./App.css";
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <FeedbackProvider>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </FeedbackProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
