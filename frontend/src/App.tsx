import { useState } from "react";
import AuthGate from "./components/AuthGate";
import type { AppView } from "./components/layout/NavBar";
import { AuthProvider } from "./context/AuthContext";
import HomePage from "./pages/HomePage";
import DashboardPage from "./pages/DashboardPage";

function AuthenticatedApp() {
  const [view, setView] = useState<AppView>("analyze");

  return view === "analyze" ? (
    <HomePage activeView={view} onNavigate={setView} />
  ) : (
    <DashboardPage activeView={view} onNavigate={setView} />
  );
}

function App() {
  return (
    <AuthProvider>
      <AuthGate>
        <AuthenticatedApp />
      </AuthGate>
    </AuthProvider>
  );
}

export default App;
