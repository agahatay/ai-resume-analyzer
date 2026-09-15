import { useEffect, useState } from "react";
import "../components/dashboard/dashboard.css";
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

  return (
    <main>
      <div className="dash-header">
        <h1 style={{ margin: 0 }}>AI Resume Analyzer</h1>
        {hasInputData && (
          <button className="dash-button-secondary" onClick={handleStartOver}>
            Start Over
          </button>
        )}
      </div>
      <StatusBadge status={status} />

      <details className="dash-inputs-details" open={!matchResult}>
        <summary>{matchResult ? "Edit Resume & Job Description" : "Resume & Job Description"}</summary>
        <ResumeUpload key={`resume-${resetCount}`} onParsed={handleResumeParsed} />
        <JobDescriptionInput key={`jd-${resetCount}`} onParsed={handleJobDescriptionParsed} />
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
  );
}

export default HomePage;
