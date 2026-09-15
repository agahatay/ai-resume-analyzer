import { useState } from "react";
import type { ChangeEvent } from "react";
import { parseJobDescription } from "../services/jobDescriptionService";
import type { ParsedJobDescription } from "../types/jobDescription";
import ParsedJobDescriptionView from "./ParsedJobDescriptionView";
import Card from "./ui/Card";
import Spinner from "./ui/Spinner";
import ErrorBanner from "./ui/ErrorBanner";
import "./ui/ui.css";

type AnalyzeState = "idle" | "loading" | "success" | "error";

const MAX_LENGTH = 20_000;

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

  function handleClear() {
    setText("");
    setParsedJobDescription(null);
    setState("idle");
    setErrorMessage("");
    onParsed?.(null);
  }

  async function handleAnalyze() {
    if (state === "loading") {
      return;
    }

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

  const isOverLimit = text.length > MAX_LENGTH;

  return (
    <Card title="3. Add Job Description" titleLevel="h2">
      <label htmlFor="job-description-textarea" className="ui-field-label">
        Job description text
      </label>
      <textarea
        id="job-description-textarea"
        value={text}
        onChange={handleTextChange}
        rows={10}
        style={{ width: "100%" }}
        placeholder="Paste a job description here..."
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "0.35rem",
        }}
      >
        <span className={isOverLimit ? "ui-error-banner-icon" : "ui-field-hint"}>
          {text.length.toLocaleString("en-US")} / {MAX_LENGTH.toLocaleString("en-US")} characters
        </span>
      </div>

      <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.5rem" }}>
        <button
          className="ui-button ui-button-primary"
          onClick={handleAnalyze}
          disabled={!text.trim() || isOverLimit || state === "loading"}
        >
          {state === "loading" ? <Spinner label="Analyzing..." /> : "4. Analyze Job Description"}
        </button>
        {text && (
          <button type="button" className="ui-button ui-button-ghost" onClick={handleClear}>
            Clear
          </button>
        )}
      </div>

      {state === "error" && <ErrorBanner message={errorMessage} />}

      {state === "success" && parsedJobDescription && (
        <div style={{ marginTop: "1rem" }}>
          <ParsedJobDescriptionView data={parsedJobDescription} />
        </div>
      )}
    </Card>
  );
}

export default JobDescriptionInput;
