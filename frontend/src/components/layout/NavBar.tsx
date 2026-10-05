import { useAuth } from "../../context/useAuth";
import "./layout.css";

export type AppView = "analyze" | "history";

interface NavBarProps {
  active: AppView;
  onNavigate: (view: AppView) => void;
}

/**
 * Phase 11: the simple authenticated navigation (Analyze Resume /
 * Analysis History / Logout) shared by HomePage and DashboardPage. No
 * router involved - `active`/`onNavigate` are plain state lifted to
 * App.tsx, matching this app's existing no-router architecture.
 */
function NavBar({ active, onNavigate }: NavBarProps) {
  const { user, logout } = useAuth();

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
      {user && (
        <span className="ui-field-hint" style={{ marginRight: "0.2rem" }}>
          {user.full_name ?? user.email}
        </span>
      )}
      <button
        type="button"
        className={`ui-button ${active === "analyze" ? "ui-button-primary" : "ui-button-secondary"}`}
        onClick={() => onNavigate("analyze")}
        aria-current={active === "analyze" || undefined}
      >
        Analyze Resume
      </button>
      <button
        type="button"
        className={`ui-button ${active === "history" ? "ui-button-primary" : "ui-button-secondary"}`}
        onClick={() => onNavigate("history")}
        aria-current={active === "history" || undefined}
      >
        Analysis History
      </button>
      <button type="button" className="ui-button ui-button-ghost" onClick={logout}>
        Log Out
      </button>
    </div>
  );
}

export default NavBar;
