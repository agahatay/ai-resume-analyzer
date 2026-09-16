import { getAccessToken, setAccessToken } from "./authToken";

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface ValidationErrorDetail {
  msg?: string;
}

// Phase 10B: most endpoints now require a Bearer token (see
// GET/POST /api/auth/*, which don't - but sending a header they ignore is
// harmless). Centralized here so every service (resume/jobDescription/
// match) gets it automatically with no per-call changes.
function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function extractErrorMessage(response: Response, path: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | ValidationErrorDetail[] };
    if (typeof body.detail === "string" && body.detail) {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((item) => item.msg).filter(Boolean).join("; ");
    }
  } catch {
    // Response body was not JSON; fall back to the generic message below.
  }
  return `Request to ${path} failed with status ${response.status}`;
}

async function handleResponse<T>(response: Response, path: string): Promise<T> {
  if (response.status === 401) {
    // The stored token is missing/invalid/expired from the server's
    // point of view - drop it so the app's AuthGate shows the login
    // form again instead of repeating the same failed request.
    setAccessToken(null);
  }
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, path));
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: { ...authHeaders() } });
  return handleResponse<T>(response, path);
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: formData,
  });
  return handleResponse<T>(response, path);
}

export async function apiPostJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return handleResponse<T>(response, path);
}
