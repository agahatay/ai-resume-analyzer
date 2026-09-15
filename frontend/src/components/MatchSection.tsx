import { useState } from "react";
import { matchResume } from "../services/matchService";
import type { ParsedResume } from "../types/resume";
import type { ParsedJobDescription } from "../types/jobDescription";
import type { ResumeMatchResponse } from "../types/match";
import MatchResult from "./MatchResult";

type MatchState = "idle" | "loading" | "success" | "error";

interface MatchSectionProps {
  resume: ParsedResume;
  jobDescription: ParsedJobDescription;
}

function MatchSection({ resume, jobDescription }: MatchSectionProps) {
  const [state, setState] = useState<MatchState>("idle");
  const [matchResult, setMatchResult] = useState<ResumeMatchResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");

  async function handleMatch() {
    setState("loading");
    setErrorMessage("");

    try {
      const result = await matchResume(resume, jobDescription);
      setMatchResult(result);
      setState("success");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Matching failed.");
      setState("error");
    }
  }

  return (
    <section>
      <h2>Match Resume</h2>
      <button onClick={handleMatch} disabled={state === "loading"}>
        {state === "loading" ? "Matching..." : "Match Resume"}
      </button>

      {state === "error" && <p role="alert">Error: {errorMessage}</p>}

      {state === "success" && matchResult && <MatchResult data={matchResult} />}
    </section>
  );
}

export default MatchSection;
