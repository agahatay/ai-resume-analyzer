import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useAuth } from "../context/useAuth";
import Card from "./ui/Card";
import ErrorBanner from "./ui/ErrorBanner";
import Spinner from "./ui/Spinner";
import "./ui/ui.css";

type Mode = "login" | "register";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;

function validateEmail(value: string): string | null {
  if (!value.trim()) {
    return "Email is required.";
  }
  if (!EMAIL_PATTERN.test(value)) {
    return "Enter a valid email address.";
  }
  return null;
}

function validatePassword(value: string): string | null {
  if (!value) {
    return "Password is required.";
  }
  if (!value.trim()) {
    return "Password must not be blank.";
  }
  if (value.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  return null;
}

// Turns whatever error a failed login/register call throws into a safe,
// user-facing string. Backend `detail` messages that make it this far
// (see api.ts's extractErrorMessage) are already written to be safe to
// show verbatim (e.g. "Incorrect email or password." never reveals
// whether the email exists). A raw network/runtime failure - which is
// not a backend message - is replaced with a plain, non-technical one
// instead of ever letting a stack trace or fetch internals reach the UI.
function describeAuthError(error: unknown, mode: Mode): string {
  if (error instanceof Error && error.message) {
    if (/^(failed to fetch|networkerror|load failed|typeerror)/i.test(error.message)) {
      return "Unable to reach the server. Please try again.";
    }
    return error.message;
  }
  return mode === "register" ? "Registration failed. Please try again." : "Login failed. Please try again.";
}

interface AuthGateProps {
  children: ReactNode;
}

/**
 * Phase 10C: the app's login/register gate, backed by AuthContext.
 * Shows a full-page loading state while the initial session is being
 * restored, the auth form (with clear Login/Register tabs, client-side
 * validation, and a session-expired notice) while unauthenticated, and
 * `children` once authenticated.
 */
function AuthGate({ children }: AuthGateProps) {
  const { status, sessionExpired, login, register, clearSessionExpired } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  if (status === "loading") {
    return (
      <div className="app-shell">
        <main className="app-container" style={{ alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
          <Spinner label="Checking your session..." />
        </main>
      </div>
    );
  }

  if (status === "authenticated") {
    return <>{children}</>;
  }

  function switchMode(nextMode: Mode) {
    if (isSubmitting) {
      return;
    }
    setMode(nextMode);
    setErrorMessage("");
    // A session-expired notice only makes sense while the user hasn't
    // yet tried to act on it; once they start a fresh attempt, drop it
    // so it doesn't linger after they've re-authenticated.
    clearSessionExpired();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) {
      // Guards against a double-click/double-submit firing two requests.
      return;
    }

    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    if (emailError || passwordError) {
      setErrorMessage(emailError ?? passwordError ?? "");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");
    clearSessionExpired();
    try {
      if (mode === "register") {
        await register(email, password);
      } else {
        await login(email, password);
      }
      // Success: AuthContext flips status to "authenticated" and this
      // component unmounts in favor of `children`, but clear the
      // password out of local state regardless so it never lingers.
    } catch (error) {
      setErrorMessage(describeAuthError(error, mode));
    } finally {
      // Never keep a submitted password in frontend state longer than
      // the request itself needs it, whether it succeeded or failed.
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="app-shell">
      <main className="app-container" style={{ maxWidth: "420px", margin: "4rem auto" }}>
        <Card titleLevel="h2">
          <div className="ui-tabs" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={`ui-tab ${mode === "login" ? "ui-tab-active" : ""}`.trim()}
              onClick={() => switchMode("login")}
            >
              Log In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={`ui-tab ${mode === "register" ? "ui-tab-active" : ""}`.trim()}
              onClick={() => switchMode("register")}
            >
              Register
            </button>
          </div>

          {sessionExpired && (
            <div style={{ marginBottom: "0.75rem" }}>
              <ErrorBanner message="Your session has expired. Please log in again." />
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }} noValidate>
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
              disabled={isSubmitting}
              style={{ width: "100%" }}
            />

            <label className="ui-field-label" htmlFor="auth-password">
              Password
              <span className="ui-field-hint"> (min. {MIN_PASSWORD_LENGTH} characters)</span>
            </label>
            <input
              id="auth-password"
              type="password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isSubmitting}
              style={{ width: "100%" }}
            />

            <button className="ui-button ui-button-primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <Spinner label={mode === "login" ? "Logging in..." : "Creating account..."} />
              ) : mode === "login" ? (
                "Log In"
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          {errorMessage && (
            <div style={{ marginTop: "0.75rem" }}>
              <ErrorBanner message={errorMessage} />
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}

export default AuthGate;
