import { useEffect, useState } from "react";
import "../components/dashboard/dashboard.css";
import "../components/ui/ui.css";
import AppHeader from "../components/layout/AppHeader";
import NavBar from "../components/layout/NavBar";
import type { AppView } from "../components/layout/NavBar";
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

interface HomePageProps {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
}

function HomePage({ activeView, onNavigate }: HomePageProps) {
  const [status, setStatus] = useState<string>("checking...");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [parsedJobDescription, setParsedJobDescription] = useState<ParsedJobDescription | null>(
    null,
  );
  const [matchResult, setMatchResult] = useState<ResumeMatchResponse | null>(null);
  const [resetCount, setResetCount] = useState(0);

  // Phase 9D: the database ids that carry this workflow's identity from
  // upload/parse through to matching. Derived from (and kept in sync
  // with) the parsed/match response objects above, which already embed
  // these same ids - tracked explicitly here so the app has one clear,
  // named place holding "what resume/JD/analysis is this session on."
  // Not persisted to localStorage/sessionStorage.
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [jobDescriptionId, setJobDescriptionId] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((health) => setStatus(health.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  function handleResumeParsed(resume: ParsedResume | null) {
    setParsedResume(resume);
    setResumeId(resume?.resume_id ?? null);
    setMatchResult(null);
    setAnalysisId(null);
  }

  function handleJobDescriptionParsed(jobDescription: ParsedJobDescription | null) {
    setParsedJobDescription(jobDescription);
    setJobDescriptionId(jobDescription?.job_description_id ?? null);
    setMatchResult(null);
    setAnalysisId(null);
  }

  function handleMatched(result: ResumeMatchResponse | null) {
    setMatchResult(result);
    setAnalysisId(result?.analysis_id ?? null);
  }

  function handleStartOver() {
    setParsedResume(null);
    setParsedJobDescription(null);
    setMatchResult(null);
    setResumeId(null);
    setJobDescriptionId(null);
    setAnalysisId(null);
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
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
          {hasInputData && (
            <button className="ui-button ui-button-secondary" onClick={handleStartOver}>
              Start Over
            </button>
          )}
          <NavBar active={activeView} onNavigate={onNavigate} />
        </div>
      </AppHeader>

      <main
        className="app-container"
        // Not shown in the UI (invisible data attributes) - exposes the
        // ids this session currently holds, for automated flow testing.
        data-resume-id={resumeId ?? undefined}
        data-job-description-id={jobDescriptionId ?? undefined}
        data-analysis-id={analysisId ?? undefined}
      >
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
            onMatched={handleMatched}
          />
        )}
      </main>
    </div>
  );
}

export default HomePage;
