import { useEffect, useState } from "react";
import "../components/dashboard/dashboard.css";
import "../components/ui/ui.css";
import AppHeader from "../components/layout/AppHeader";
import WorkflowSteps from "../components/layout/WorkflowSteps";
import type { WorkflowStep } from "../components/layout/WorkflowSteps";
import StatusBadge from "../components/StatusBadge";
import ResumeUpload from "../components/ResumeUpload";
import JobDescriptionInput from "../components/JobDescriptionInput";
import MatchSection from "../components/MatchSection";
import { getHealth } from "../services/healthService";
import type { ParsedResume } from "../types/resume";
import type { ParsedJobDescription } from "../types/jobDescription";
import type { ResumeMatchResponse } from "../types/match";

function HomePage() {
  const [status, setStatus] = useState<string>("checking...");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [parsedJobDescription, setParsedJobDescription] = useState<ParsedJobDescription | null>(
    null,
  );
  const [matchResult, setMatchResult] = useState<ResumeMatchResponse | null>(null);
  const [resetCount, setResetCount] = useState(0);

  useEffect(() => {
    getHealth()
      .then((health) => setStatus(health.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  function handleResumeParsed(resume: ParsedResume | null) {
    setParsedResume(resume);
    setMatchResult(null);
  }

  function handleJobDescriptionParsed(jobDescription: ParsedJobDescription | null) {
    setParsedJobDescription(jobDescription);
    setMatchResult(null);
  }

  function handleStartOver() {
    setParsedResume(null);
    setParsedJobDescription(null);
    setMatchResult(null);
    setResetCount((count) => count + 1);
  }

  const hasInputData = parsedResume !== null || parsedJobDescription !== null;

  const steps: WorkflowStep[] = [
    { label: "Upload Resume", status: parsedResume ? "complete" : "current" },
    {
      label: "Parse Resume",
      status: parsedResume ? "complete" : "current",
    },
    {
      label: "Add Job Description",
      status: parsedJobDescription ? "complete" : parsedResume ? "current" : "upcoming",
    },
    {
      label: "Analyze",
      status: matchResult ? "complete" : parsedResume && parsedJobDescription ? "current" : "upcoming",
    },
    { label: "View Results", status: matchResult ? "complete" : "upcoming" },
  ];

  return (
    <div className="app-shell">
      <AppHeader>
        {hasInputData && (
          <button className="ui-button ui-button-secondary" onClick={handleStartOver}>
            Start Over
          </button>
        )}
      </AppHeader>

      <main className="app-container">
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "1rem" }}>
          <StatusBadge status={status} />
          <WorkflowSteps steps={steps} />
        </div>

        <details className="dash-inputs-details" open={!matchResult}>
          <summary>{matchResult ? "Edit Resume & Job Description" : "Resume & Job Description"}</summary>
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <ResumeUpload key={`resume-${resetCount}`} onParsed={handleResumeParsed} />
            <JobDescriptionInput key={`jd-${resetCount}`} onParsed={handleJobDescriptionParsed} />
          </div>
        </details>

        {parsedResume && parsedJobDescription && (
          <MatchSection
            key={`match-${resetCount}`}
            resume={parsedResume}
            jobDescription={parsedJobDescription}
            onMatched={setMatchResult}
          />
        )}
      </main>
    </div>
  );
}

export default HomePage;
