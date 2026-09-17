import { useState } from "react";
import AppHeader from "../components/layout/AppHeader";
import NavBar from "../components/layout/NavBar";
import type { AppView } from "../components/layout/NavBar";
import { useAuth } from "../context/AuthContext";
import AnalysisHistory from "../components/history/AnalysisHistory";
import AnalysisDetails from "../components/history/AnalysisDetails";
import "../components/dashboard/dashboard.css";
import "../components/ui/ui.css";
import "../components/history/history.css";

interface DashboardPageProps {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
}

function DashboardPage({ activeView, onNavigate }: DashboardPageProps) {
  const { user } = useAuth();
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);

  return (
    <div className="app-shell">
      <AppHeader>
        <NavBar active={activeView} onNavigate={onNavigate} />
      </AppHeader>

      <main className="app-container">
        {selectedAnalysisId ? (
          <AnalysisDetails analysisId={selectedAnalysisId} onBack={() => setSelectedAnalysisId(null)} />
        ) : (
          <>
            <h2 style={{ margin: 0 }}>Welcome back, {user?.full_name ?? user?.email ?? "there"}.</h2>
            <AnalysisHistory
              onViewDetails={setSelectedAnalysisId}
              onAnalyzeResume={() => onNavigate("analyze")}
            />
          </>
        )}
      </main>
    </div>
  );
}

export default DashboardPage;
