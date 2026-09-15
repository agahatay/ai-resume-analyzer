import { useState } from "react";
import type { ChangeEvent } from "react";
import { parseJobDescription } from "../services/jobDescriptionService";
import type { ParsedJobDescription } from "../types/jobDescription";
import ParsedJobDescriptionView from "./ParsedJobDescriptionView";

type AnalyzeState = "idle" | "loading" | "success" | "error";

interface JobDescriptionInputProps {
  onParsed?: (jobDescription: ParsedJobDescription | null) => void;
}

function JobDescriptionInput({ onParsed }: JobDescriptionInputProps) {
  const [text, setText] = useState<string>("");
  const [state, setState] = useState<AnalyzeState>("idle");
  const [parsedJobDescription, setParsedJobDescription] = useState<ParsedJobDescription | null>(
    null,
  );
  const [errorMessage, setErrorMessage] = useState<string>("");

  function handleTextChange(event: ChangeEvent<HTMLTextAreaElement>) {
    setText(event.target.value);
    setParsedJobDescription(null);
    onParsed?.(null);
  }

  async function handleAnalyze() {
    setState("loading");
    setErrorMessage("");
    onParsed?.(null);

    try {
      const result = await parseJobDescription(text);
      setParsedJobDescription(result);
      setState("success");
      onParsed?.(result);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Analysis failed.");
      setState("error");
    }
  }

  return (
    <section>
      <h2>Job Description</h2>
      <textarea
        value={text}
        onChange={handleTextChange}
        rows={12}
        style={{ width: "100%" }}
        placeholder="Paste a job description here..."
      />
      <div>
        <button onClick={handleAnalyze} disabled={!text.trim() || state === "loading"}>
          {state === "loading" ? "Analyzing..." : "Analyze Job Description"}
        </button>
      </div>

      {state === "error" && <p role="alert">Error: {errorMessage}</p>}

      {state === "success" && parsedJobDescription && (
        <ParsedJobDescriptionView data={parsedJobDescription} />
      )}
    </section>
  );
}

export default JobDescriptionInput;
