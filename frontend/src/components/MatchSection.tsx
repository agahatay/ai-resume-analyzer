import { useState } from "react";
import { matchResume } from "../services/matchService";
import type { ParsedResume } from "../types/resume";
import type { ParsedJobDescription } from "../types/jobDescription";
import type { ResumeMatchResponse } from "../types/match";
import AnalysisDashboard from "./dashboard/AnalysisDashboard";
import Card from "./ui/Card";
import Spinner from "./ui/Spinner";
import ErrorBanner from "./ui/ErrorBanner";
import EmptyState from "./ui/EmptyState";

type MatchState = "idle" | "loading" | "error";

interface MatchSectionProps {
  resume: ParsedResume;
  jobDescription: ParsedJobDescription;
  onMatched?: (result: ResumeMatchResponse | null) => void;
}

function MatchSection({ resume, jobDescription, onMatched }: MatchSectionProps) {
  const [state, setState] = useState<MatchState>("idle");
  const [matchResult, setMatchResult] = useState<ResumeMatchResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  async function handleMatch() {
    if (state === "loading") {
      // Guards against duplicate submissions (double-click / repeated Enter).
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const result = await matchResume(resume, jobDescription);
      setMatchResult(result);
      onMatched?.(result);
      setState("idle");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Matching failed.");
      setState("error");
    }
  }

  if (matchResult) {
    return (
      <AnalysisDashboard
        data={matchResult}
        resume={resume}
        jobDescription={jobDescription}
        onAnalyzeAgain={handleMatch}
        isAnalyzing={state === "loading"}
      />
    );
  }

  return (
    <Card title="5. Match Resume" titleLevel="h2">
      <button className="ui-button ui-button-primary" onClick={handleMatch} disabled={state === "loading"}>
        {state === "loading" ? <Spinner label="Matching..." /> : "Match Resume"}
      </button>

      {state === "error" && (
        <div style={{ marginTop: "0.75rem" }}>
          <ErrorBanner message={errorMessage} />
        </div>
      )}

      {state === "idle" && (
        <div style={{ marginTop: "0.75rem" }}>
          <EmptyState
            title="No analysis yet"
            message='Click "Match Resume" to compare your resume against the job description.'
          />
        </div>
      )}
    </Card>
  );
}

export default MatchSection;
