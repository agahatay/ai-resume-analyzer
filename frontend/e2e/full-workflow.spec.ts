import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

// Phase 9D/10B: drives the real UI through registering + logging in
// (Phase 10B added the AuthGate this now goes through first, since every
// resume/JD/match endpoint requires authentication), then the whole
// upload -> parse resume -> analyze job description -> match flow,
// exactly as a user would, and checks that:
// - the database ids (resume/JD/analysis) actually reach the page state
//   (exposed as invisible data-* attributes on the main container - see
//   HomePage.tsx - purely for this kind of assertion, not rendered),
// - the "Analysis saved" badge appears once matching succeeds,
// - nothing logs a console error and no network request fails.
//
// Requires the backend (with PostgreSQL reachable) and the Vite dev
// server to already be running - see the Phase 9D/10B reports for exact
// commands. This suite creates a real user + database rows; the report
// documents the manual cleanup performed after the run.

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESUME_PDF_PATH = path.join(__dirname, "fixtures", "resume.pdf");

const JOB_DESCRIPTION_TEXT = `We are hiring a Backend Engineer.

Required Skills:
Python, SQL, FastAPI

Preferred Skills:
Docker

Education:
Bachelor's degree in Computer Science

Experience:
2+ years of experience
`;

test("full upload -> parse -> analyze -> match workflow carries ids and saves the analysis", async ({ page }) => {
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("requestfailed", (request) => {
    failedRequests.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 500) {
      failedRequests.push(`${response.request().method()} ${response.url()} -> ${response.status()}`);
    }
  });

  await page.goto("/");

  // --- 0. Register + log in (Phase 10B/10C's AuthGate) ---
  const testEmail = `e2e-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
  const testPassword = "s3cur3-password";
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Email").fill(testEmail);
  await page.locator("#auth-password").fill(testPassword);
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();

  // --- 1. Upload the resume PDF ---
  // resume_id is captured inside ResumeUpload's own state right after
  // upload (and threaded into the parse call below); it only reaches
  // HomePage's top-level state - and this data attribute - once parsing
  // reports back via onParsed, so that's checked after step 2 instead.
  await page.setInputFiles("#resume-file-input", RESUME_PDF_PATH);
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByText(/Extracted \d+ characters/)).toBeVisible();

  // --- 2. Parse the resume ---
  await page.getByRole("button", { name: "2. Parse Resume" }).click();
  await expect(page.getByText("alex.rivera@example.com")).toBeVisible();
  await expect(page.locator("main.app-container")).toHaveAttribute("data-resume-id", /.+/);

  // --- 3. Analyze the job description ---
  await page.getByLabel("Job description text").fill(JOB_DESCRIPTION_TEXT);
  await page.getByRole("button", { name: "4. Analyze Job Description" }).click();
  await expect(page.getByRole("heading", { name: "Job Title" })).toBeVisible();
  await expect(page.locator("main.app-container")).toHaveAttribute("data-job-description-id", /.+/);

  // --- 4. Match ---
  await page.getByRole("button", { name: "Match Resume" }).click();
  await expect(page.getByTestId("analysis-saved-badge")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("main.app-container")).toHaveAttribute("data-analysis-id", /.+/);

  // --- 5. No console errors, no failed/5xx requests ---
  expect(consoleErrors, `Console errors: ${consoleErrors.join("; ")}`).toHaveLength(0);
  expect(failedRequests, `Failed requests: ${failedRequests.join("; ")}`).toHaveLength(0);
});
