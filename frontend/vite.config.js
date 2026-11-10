import { realpathSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, process.cwd(), "");
  return {
    // Use the config's canonical path so d:\ and D:\ do not create separate module URLs.
    root: realpathSync.native(fileURLToPath(new URL(".", import.meta.url))),
    plugins: [react()],
    // Keep the login logo and slide assets as versioned files in production.
    build: { assetsInlineLimit: 0 },
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
    server: {
      port: 5173,
      host: true,
      // Same-origin requests also make ETag readable without changing backend CORS.
      proxy: {
        "/api": {
          target: environment.API_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
