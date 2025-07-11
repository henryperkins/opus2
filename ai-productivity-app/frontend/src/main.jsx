// React application entry point
import "./sentry";
import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider } from "./contexts/AuthContext";
import { KnowledgeProvider } from "./contexts/KnowledgeContext";
import { AIConfigProvider } from "./contexts/AIConfigContext";
import AppRouter from "./router";
import { ThemeProvider } from "./hooks/useTheme";
import { ToastContainer } from "./components/common/Toast";
import "./styles/globals.css";
import "./styles/dark-mode-emergency.css";
import ErrorBoundary from "./components/common/ErrorBoundary";

// React-Query
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./queryClient";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

// Mount React app
ReactDOM.createRoot(document.getElementById("root")).render(
  // <React.StrictMode>
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <AIConfigProvider>
            <KnowledgeProvider>
              <AppRouter />
              <ToastContainer />
            </KnowledgeProvider>
          </AIConfigProvider>
        </AuthProvider>
        {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
      </ThemeProvider>
    </QueryClientProvider>
  </ErrorBoundary>,
  // </React.StrictMode>
);
