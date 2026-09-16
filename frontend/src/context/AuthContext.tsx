import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { getCurrentUser, login as loginRequest, registerUser as registerRequest } from "../services/authService";
import type { UserResponse } from "../services/authService";
import { getAccessToken, setAccessToken, subscribeToUnauthorized } from "../services/authToken";

// Phase 10C: single source of truth for "is anyone logged in, and who".
// Every other part of the app (AuthGate, the header, protected API
// callers) reads/drives auth state through useAuth() instead of touching
// authToken.ts or authService.ts directly.
export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  isAuthenticated: boolean;
  user: UserResponse | null;
  /** True only when a previously-valid session just died (expired token,
   *  deactivated account, etc.) - never true for the initial, never-logged-in
   *  state. Drives the "Your session has expired" message. */
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserResponse | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Initial session restoration: a token sitting in localStorage is never
  // trusted by itself (it could be expired, forged-looking, or for a
  // deactivated account) - GET /api/auth/me is the only thing that
  // confirms it still represents a real, active session.
  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const token = getAccessToken();
      if (!token) {
        if (!cancelled) {
          setStatus("unauthenticated");
        }
        return;
      }
      try {
        const currentUser = await getCurrentUser();
        if (!cancelled) {
          setUser(currentUser);
          setStatus("authenticated");
        }
      } catch {
        // Invalid/expired token - api.ts already cleared it. This is the
        // startup case, not a live session dying, so no "session expired"
        // message here (requirement: don't show it for the initial
        // unauthenticated state).
        if (!cancelled) {
          setAccessToken(null);
          setUser(null);
          setStatus("unauthenticated");
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  // Fired by api.ts whenever an already-authenticated request comes back
  // 401 (token expired/invalidated mid-session). Only show the
  // session-expired message if we were actually authenticated at the
  // time - guards against stray events and prevents any redirect loop,
  // since this only ever transitions authenticated -> unauthenticated.
  useEffect(() => {
    return subscribeToUnauthorized(() => {
      setUser(null);
      setStatus((previousStatus) => {
        if (previousStatus === "authenticated") {
          setSessionExpired(true);
        }
        return "unauthenticated";
      });
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokenResponse = await loginRequest(email, password);
    setAccessToken(tokenResponse.access_token);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setSessionExpired(false);
      setStatus("authenticated");
    } catch (error) {
      setAccessToken(null);
      setUser(null);
      setStatus("unauthenticated");
      throw error;
    }
  }, []);

  const register = useCallback(
    async (email: string, password: string) => {
      await registerRequest(email, password);
      // Simpler than a separate "registered, now log in" screen and
      // matches this app's existing single-gate architecture; also
      // avoids a second, redundant credential submission from the user.
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setSessionExpired(false);
    setStatus("unauthenticated");
  }, []);

  const clearSessionExpired = useCallback(() => setSessionExpired(false), []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      isAuthenticated: status === "authenticated",
      user,
      sessionExpired,
      login,
      register,
      logout,
      clearSessionExpired,
    }),
    [status, user, sessionExpired, login, register, logout, clearSessionExpired],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
