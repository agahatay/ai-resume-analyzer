import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";

// Phase 11: covers the authenticated analysis-history dashboard end to
// end - performing a real match, seeing it in history, opening its
// persisted detail view, confirming a second user is blocked from it,
// confirming the empty-history state for a user with no analyses, and
// logout. Complements e2e/full-workflow.spec.ts (the live match flow)
// and e2e/auth.spec.ts (session handling).
//
// Requires the backend (with PostgreSQL reachable) and the Vite dev
// server to already be running.

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESUME_PDF_PATH = path.join(__dirname, "fixtures", "resume.pdf");
const TOKEN_STORAGE_KEY = "ai-resume-analyzer.access_token";

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

function uniqueCredentials() {
  return {
    email: `e2e-history-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`,
    password: "s3cur3-password",
  };
}

async function registerAndLogIn(page: Page, email: string, password: string) {
  await page.getByRole("tab", { name: "Register" }).click();
  await page.getByLabel("Email").fill(email);
  await page.locator("#auth-password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByRole("heading", { name: "1. Upload Resume" })).toBeVisible();
}

async function performAnalysis(page: Page): Promise<string> {
  await page.setInputFiles("#resume-file-input", RESUME_PDF_PATH);
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByText(/Extracted \d+ characters/)).toBeVisible();

  await page.getByRole("button", { name: "2. Parse Resume" }).click();
  await expect(page.getByText("alex.rivera@example.com")).toBeVisible();

  await page.getByLabel("Job description text").fill(JOB_DESCRIPTION_TEXT);
  await page.getByRole("button", { name: "4. Analyze Job Description" }).click();
  await expect(page.getByRole("heading", { name: "Job Title" })).toBeVisible();

  await page.getByRole("button", { name: "Match Resume" }).click();
  await expect(page.getByTestId("analysis-saved-badge")).toBeVisible({ timeout: 15_000 });

  const analysisId = await page.locator("main.app-container").getAttribute("data-analysis-id");
  expect(analysisId).toBeTruthy();
  return analysisId as string;
}

test("analyze, view in history, open details, second user blocked, empty state, logout", async ({ page }) => {
  const matchRequestUrls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/resume/match")) {
      matchRequestUrls.push(request.url());
    }
  });

  const { email, password } = uniqueCredentials();
  await page.goto("/");

  // --- 1. Register/login ---
  await registerAndLogIn(page, email, password);

  // --- 2. Perform an analysis ---
  const analysisId = await performAnalysis(page);
  expect(matchRequestUrls).toHaveLength(1);

  // Capture the score labels shown on the live match dashboard, to
  // compare against the history detail view later (step 6).
  const liveCombined = await page.getByRole("img", { name: /^Combined Match:/ }).getAttribute("aria-label");
  const liveDeterministic = await page
    .getByRole("img", { name: /^Deterministic Match:/ })
    .getAttribute("aria-label");
  const liveSemantic = await page.getByRole("img", { name: /^Semantic Match:/ }).getAttribute("aria-label");

  // --- 3. Navigate to history ---
  await page.getByRole("button", { name: "Analysis History" }).click();
  await expect(page.getByRole("heading", { name: "Recent Analyses" })).toBeVisible();

  // --- 4. Verify the analysis appears ---
  await expect(page.getByText("1 total analysis")).toBeVisible();
  const card = page.locator(".history-card").first();
  await expect(card).toBeVisible();

  // --- 5. Open analysis details ---
  await card.getByRole("button", { name: "View Details" }).click();
  await expect(page.getByRole("heading", { name: "Analysis Details" })).toBeVisible();

  // --- 6. Verify scores/details match the original analysis ---
  await expect(page.getByRole("img", { name: /^Combined Match:/ })).toHaveAttribute("aria-label", liveCombined!);
  await expect(page.getByRole("img", { name: /^Deterministic Match:/ })).toHaveAttribute(
    "aria-label",
    liveDeterministic!,
  );
  await expect(page.getByRole("img", { name: /^Semantic Match:/ })).toHaveAttribute("aria-label", liveSemantic!);

  // --- 7. Verify page load did NOT trigger another /api/resume/match ---
  // (viewing history and opening detail must both read persisted data only)
  expect(matchRequestUrls).toHaveLength(1);

  await page.getByRole("button", { name: "Back to History" }).click();

  // --- 8. Verify a second user cannot access the first user's analysis ---
  await page.getByRole("button", { name: "Log Out" }).click();
  await expect(page.getByRole("tab", { name: "Log In" })).toBeVisible();

  const { email: email2, password: password2 } = uniqueCredentials();
  await registerAndLogIn(page, email2, password2);

  const foreignAccessStatus = await page.evaluate(
    async ({ id, tokenKey }) => {
      const token = localStorage.getItem(tokenKey);
      const response = await fetch(`http://localhost:8000/api/analyses/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      return response.status;
    },
    { id: analysisId, tokenKey: TOKEN_STORAGE_KEY },
  );
  expect(foreignAccessStatus).toBe(404);

  // --- 9. Empty history state for the second (fresh) user ---
  await page.getByRole("button", { name: "Analysis History" }).click();
  await expect(page.getByText("No analyses yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Analyze a Resume" })).toBeVisible();

  // --- 10. Logout ---
  await page.getByRole("button", { name: "Log Out" }).click();
  await expect(page.getByRole("tab", { name: "Log In" })).toBeVisible();
});
