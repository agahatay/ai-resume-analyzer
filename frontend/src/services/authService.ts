import { apiPostJson } from "./api";

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
