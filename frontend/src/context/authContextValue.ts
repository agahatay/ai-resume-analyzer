import { createContext } from "react";
import type { UserResponse } from "../services/authService";

// Kept apart from AuthContext.tsx (the provider component) and useAuth.ts
// (the hook) so that AuthContext.tsx exports only a component. The
// react-refresh/only-export-components rule - and with it fast refresh -
// breaks if a file that exports components also exports a context object
// or a hook.
export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
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

export const AuthContext = createContext<AuthContextValue | null>(null);
