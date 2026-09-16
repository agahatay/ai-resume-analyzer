import { apiGet, apiPostJson } from "./api";

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export function registerUser(email: string, password: string): Promise<UserResponse> {
  return apiPostJson<UserResponse>("/api/auth/register", { email, password });
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiPostJson<TokenResponse>("/api/auth/login", { email, password });
}

// Used both to restore a session on startup (see AuthContext) and as the
// general "who am I" check - a 200 here is the only thing that proves a
// stored token still represents a valid, active session.
export function getCurrentUser(): Promise<UserResponse> {
  return apiGet<UserResponse>("/api/auth/me");
}
