import { useState } from "react";
import { matchResume } from "../services/matchService";
import type { ParsedResume } from "../types/resume";
import type { ParsedJobDescription } from "../types/jobDescription";
import type { ResumeMatchResponse } from "../types/match";
import AnalysisDashboard from "./dashboard/AnalysisDashboard";

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

  return (
    <section>
      <h2>Match Resume</h2>

      {!matchResult && (
        <button onClick={handleMatch} disabled={state === "loading"}>
          {state === "loading" ? "Matching..." : "Match Resume"}
        </button>
      )}

      {state === "error" && <p role="alert">Error: {errorMessage}</p>}

      {!matchResult && state === "idle" && (
        <p>Click "Match Resume" to generate your analysis.</p>
      )}

      {matchResult && (
        <AnalysisDashboard
          data={matchResult}
          resume={resume}
          jobDescription={jobDescription}
          onAnalyzeAgain={handleMatch}
          isAnalyzing={state === "loading"}
        />
      )}
    </section>
  );
}

export default MatchSection;
