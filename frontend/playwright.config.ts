import { defineConfig } from "@playwright/test";

// Phase 9D: minimal Playwright config for the one full-workflow smoke
// test in e2e/full-workflow.spec.ts. The frontend (Vite) and backend
// (FastAPI + PostgreSQL) dev servers are started manually before running
// this - not via Playwright's webServer option - since the backend isn't
// a single npm-invokable command and already has its own start/stop
// lifecycle used throughout Phase 9A-9D's verification.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:5173",
    screenshot: "only-on-failure",
  },
});
