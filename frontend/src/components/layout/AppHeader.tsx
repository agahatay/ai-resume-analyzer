import type { ReactNode } from "react";
import "./layout.css";

interface AppHeaderProps {
  children?: ReactNode;
}

function AppHeader({ children }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header-inner">
        <div>
          <h1 className="app-title">AI Resume Analyzer</h1>
          <p className="app-subtitle">
            Analyze how closely your resume matches a job description using deterministic and semantic
            matching.
          </p>
        </div>
        {children}
      </div>
    </header>
  );
}

export default AppHeader;
