import { useEffect, useState } from "react";
import StatusBadge from "../components/StatusBadge";
import ResumeUpload from "../components/ResumeUpload";
import JobDescriptionInput from "../components/JobDescriptionInput";
import MatchSection from "../components/MatchSection";
import { getHealth } from "../services/healthService";
import type { ParsedResume } from "../types/resume";
import type { ParsedJobDescription } from "../types/jobDescription";

function HomePage() {
  const [status, setStatus] = useState<string>("checking...");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [parsedJobDescription, setParsedJobDescription] = useState<ParsedJobDescription | null>(
    null,
  );

  useEffect(() => {
    getHealth()
      .then((health) => setStatus(health.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main>
      <h1>AI Resume Analyzer</h1>
      <StatusBadge status={status} />
      <ResumeUpload onParsed={setParsedResume} />
      <JobDescriptionInput onParsed={setParsedJobDescription} />
      {parsedResume && parsedJobDescription && (
        <MatchSection resume={parsedResume} jobDescription={parsedJobDescription} />
      )}
    </main>
  );
}

export default HomePage;
