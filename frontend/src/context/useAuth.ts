import { useContext } from "react";
import { AuthContext } from "./authContextValue";
import type { AuthContextValue } from "./authContextValue";

// Phase 10C: single source of truth for "is anyone logged in, and who".
// Every other part of the app (AuthGate, the header, protected API
// callers) reads/drives auth state through useAuth() instead of touching
// authToken.ts or authService.ts directly.
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
