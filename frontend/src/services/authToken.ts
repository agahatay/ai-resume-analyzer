// Phase 10B/10C: minimal in-memory + localStorage-backed access token store.
//
// localStorage here holds the JWT access token only - never a database
// id (Phase 9D's "don't store database IDs in local/session storage yet"
// is about resumeId/jobDescriptionId/analysisId, a separate concern) and
// never the plaintext password. Persisting the token this way is a real,
// standard SPA pattern (not a dev-only workaround) so a page refresh
// doesn't force the user to log in again every time.
//
// Known limitation (Phase 10C): an access token in localStorage is
// readable by any JavaScript running on this origin, so it is vulnerable
// to theft if the app ever has an XSS vulnerability. This phase does not
// change that - no server-side session or HttpOnly refresh-cookie
// architecture is introduced here. GET /api/auth/me is instead used
// (see AuthContext) to verify the stored token is still valid before
// trusting it, so localStorage's mere *presence* of a token is never
// treated as proof of authentication on its own.
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
}

// Fired only when an *authenticated* request (one that carried a real
// token) comes back 401, i.e. an active session just died server-side
// (expiry, deactivation, etc.). AuthContext listens for this
// specifically to show "Your session has expired" - a plain logout, or a
// login/register attempt with no token yet, must never trigger it.
const unauthorizedListeners = new Set<() => void>();

export function notifyUnauthorized(): void {
  unauthorizedListeners.forEach((listener) => listener());
}

export function subscribeToUnauthorized(listener: () => void): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}
