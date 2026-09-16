import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { login, registerUser } from "../services/authService";
import { getAccessToken, setAccessToken, subscribeToAccessToken } from "../services/authToken";
import Card from "./ui/Card";
import ErrorBanner from "./ui/ErrorBanner";
import Spinner from "./ui/Spinner";
import "./ui/ui.css";

type Mode = "login" | "register";

function useAccessToken(): string | null {
  const [token, setToken] = useState<string | null>(getAccessToken());
  useEffect(() => subscribeToAccessToken(() => setToken(getAccessToken())), []);
  return token;
}

interface AuthGateProps {
  children: ReactNode;
}

/**
 * Phase 10B: a minimal, real login/register gate - not a dev-only
 * bypass. Every resume/job-description/match endpoint now requires a
 * Bearer token, so the app needs *some* way to obtain one; this is
 * intentionally the smallest working version (no password reset, no
 * profile management, no separate routes) rather than the full auth UI,
 * which is explicitly out of scope for this phase.
 */
function AuthGate({ children }: AuthGateProps) {
  const token = useAccessToken();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  if (token) {
    return <>{children}</>;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    setErrorMessage("");
    try {
      if (mode === "register") {
        await registerUser(email, password);
      }
      const tokenResponse = await login(email, password);
      setAccessToken(tokenResponse.access_token);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <main className="app-container" style={{ maxWidth: "420px", margin: "4rem auto" }}>
        <Card title={mode === "login" ? "Log In" : "Create Account"} titleLevel="h2">
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <label className="ui-field-label" htmlFor="auth-email">
              Email
            </label>
            <input
              id="auth-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              style={{ width: "100%" }}
            />

            <label className="ui-field-label" htmlFor="auth-password">
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              required
              minLength={8}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              style={{ width: "100%" }}
            />

            <button className="ui-button ui-button-primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <Spinner label="Please wait..." />
              ) : mode === "login" ? (
                "Log In"
              ) : (
                "Register & Log In"
              )}
            </button>
          </form>

          {errorMessage && (
            <div style={{ marginTop: "0.75rem" }}>
              <ErrorBanner message={errorMessage} />
            </div>
          )}

          <button
            type="button"
            className="ui-button ui-button-ghost"
            style={{ marginTop: "0.75rem" }}
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setErrorMessage("");
            }}
          >
            {mode === "login" ? "Need an account? Register" : "Already have an account? Log in"}
          </button>
        </Card>
      </main>
    </div>
  );
}

export default AuthGate;
