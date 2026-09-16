// Phase 10B: minimal in-memory + localStorage-backed access token store.
//
// localStorage here holds the JWT access token only - never a database
// id (Phase 9D's "don't store database IDs in local/session storage yet"
// is about resumeId/jobDescriptionId/analysisId, a separate concern).
// Persisting the token this way is a real, standard SPA pattern (not a
// dev-only workaround) so a page refresh doesn't force the user to log
// in again every time.
const STORAGE_KEY = "ai-resume-analyzer.access_token";

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    // localStorage can throw (private browsing, disabled storage, etc.);
    // fail safe by just not persisting a token in that case.
    return null;
  }
}

let currentToken: string | null = readStoredToken();
const listeners = new Set<() => void>();

export function getAccessToken(): string | null {
  return currentToken;
}

export function setAccessToken(token: string | null): void {
  currentToken = token;
  try {
    if (token) {
      localStorage.setItem(STORAGE_KEY, token);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors - the in-memory token is still authoritative
    // for the current page session either way.
  }
  listeners.forEach((listener) => listener());
}

// Lets React components (see AuthGate) re-render on login/logout without
// pulling in a state-management library the rest of this app doesn't use.
export function subscribeToAccessToken(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
