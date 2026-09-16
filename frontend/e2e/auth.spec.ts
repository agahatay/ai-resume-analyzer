import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

// Phase 10C: covers AuthContext/AuthGate's session handling on its own -
// registration, login, session restoration across a page refresh (via
// GET /api/auth/me), logout, an invalid stored token being cleared
// cleanly on startup, and a protected API call that 401s mid-session
// kicking the user back to the login screen with a clear message.
// Complements e2e/full-workflow.spec.ts, which drives the resume/JD/match
// workflow once already authenticated.
//
// Requires the backend (with PostgreSQL reachable) and the Vite dev
// server to already be running. Each test registers its own throwaway
// user (unique email per run), mirroring full-workflow.spec.ts.

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESUME_PDF_PATH = path.join(__dirname, "fixtures", "resume.pdf");
const TOKEN_STORAGE_KEY = "ai-resume-analyzer.access_token";

function uniqueCredentials() {
  return {
    email: `e2e-auth-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`,
    password: "s3cur3-password",
  };
}

async function registerAndLogIn(page: import("@playwright/test").Page, email: string, password: string) {
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Email").fill(email);
  await page.locator("#auth-password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();
}

test.describe("authentication", () => {
  test("registering a new user logs them in and shows the authenticated app", async ({ page }) => {
    const { email, password } = uniqueCredentials();
    await page.goto("/");

    await expect(page.getByRole("tab", { name: "Log In" })).toBeVisible();
    await registerAndLogIn(page, email, password);

    await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();

    // Requirement: no password or token ever appears anywhere in the
    // visible UI. The auth form itself is gone (unmounted) once
    // authenticated, so its password field can't be inspected at all;
    // check the raw page content too, for good measure.
    const html = await page.content();
    expect(html).not.toContain(password);
  });

  test("logging out returns to the login screen and logging back in works", async ({ page }) => {
    const { email, password } = uniqueCredentials();
    await page.goto("/");
    await registerAndLogIn(page, email, password);
    await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();

    await page.getByRole("button", { name: "Log Out" }).click();
    await expect(page.getByRole("tab", { name: "Log In" })).toBeVisible();
    // An explicit, user-initiated logout must never show the
    // session-expired message - that's only for a session dying
    // unexpectedly mid-use.
    await expect(page.getByText("Your session has expired")).toHaveCount(0);

    const storedToken = await page.evaluate((key) => localStorage.getItem(key), TOKEN_STORAGE_KEY);
    expect(storedToken).toBeNull();

    // AuthGate stays mounted across logout, so its mode still remembers
    // "Register" from registerAndLogIn() above - switch back to the
    // "Log In" tab explicitly before logging back in.
    await page.getByRole("tab", { name: "Log In" }).click();
    await page.getByLabel("Email").fill(email);
    await page.locator("#auth-password").fill(password);
    await page.getByRole("button", { name: "Log In", exact: true }).click();
    await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();
  });

  test("refreshing the page restores the session via GET /api/auth/me", async ({ page }) => {
    const { email, password } = uniqueCredentials();
    await page.goto("/");
    await registerAndLogIn(page, email, password);
    await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();

    await page.reload();

    await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();
  });

  test("an invalid stored token is rejected and the login screen returns cleanly, without trusting localStorage alone", async ({
    page,
  }) => {
    await page.goto("/");
    await page.evaluate((key) => localStorage.setItem(key, "not-a-real-jwt"), TOKEN_STORAGE_KEY);

    await page.reload();

    // Not stuck on the initial "checking your session" loading state,
    // and not shown as a "session expired" event (this is the initial
    // unauthenticated state, not a session that was live and then died).
    await expect(page.getByRole("tab", { name: "Log In" })).toBeVisible();
    await expect(page.getByText("Checking your session...")).toHaveCount(0);
    await expect(page.getByText("Your session has expired")).toHaveCount(0);

    const storedToken = await page.evaluate((key) => localStorage.getItem(key), TOKEN_STORAGE_KEY);
    expect(storedToken).toBeNull();
  });

  test("a protected API call that gets 401 mid-session clears auth and returns to the login screen with a message", async ({
    page,
  }) => {
    const { email, password } = uniqueCredentials();
    await page.goto("/");
    await registerAndLogIn(page, email, password);
    await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();

    // Simulate the token dying server-side mid-session (expiry,
    // deactivation, etc.) by forcing the next protected call to 401,
    // without needing to wait out the real token TTL.
    await page.route("**/api/resume/upload", (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Authentication token has expired." }),
      }),
    );

    await page.setInputFiles("#resume-file-input", RESUME_PDF_PATH);
    await page.getByRole("button", { name: "Upload" }).click();

    await expect(page.getByRole("tab", { name: "Log In" })).toBeVisible();
    await expect(page.getByText("Your session has expired. Please log in again.")).toBeVisible();

    const storedToken = await page.evaluate((key) => localStorage.getItem(key), TOKEN_STORAGE_KEY);
    expect(storedToken).toBeNull();
  });
});
