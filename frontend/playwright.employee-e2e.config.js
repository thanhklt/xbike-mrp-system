import { defineConfig } from "@playwright/test";
import fixtureConfig from "./playwright.config.js";

if (process.env.EMPLOYEE_E2E !== "1") {
  throw new Error("Set EMPLOYEE_E2E=1 only after preparing the isolated test backend on port 8002.");
}

export default defineConfig({
  ...fixtureConfig,
  testDir: "./tests/e2e",
  timeout: 120000,
  outputDir: "./test-results-employee-live",
  use: { ...fixtureConfig.use, baseURL: "http://127.0.0.1:5176" },
  webServer: {
    command: "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5176 --strictPort",
    url: "http://127.0.0.1:5176",
    env: { API_PROXY_TARGET: "http://127.0.0.1:8002" },
    reuseExistingServer: false,
  },
});
