export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function extractErrorMessage(response: Response, path: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) {
      return body.detail;
    }
  } catch {
    // Response body was not JSON; fall back to the generic message below.
  }
  return `Request to ${path} failed with status ${response.status}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, path));
  }
  return response.json() as Promise<T>;
}

export async function apiPostForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response, path));
  }
  return response.json() as Promise<T>;
}
