import { useState } from "react";
import type { ChangeEvent } from "react";
import { parseResume, uploadResume } from "../services/resumeService";
import type { ParsedResume } from "../types/resume";
import ParsedResumeView from "./ParsedResumeView";

type UploadState = "idle" | "loading" | "success" | "error";
type ParseState = "idle" | "loading" | "success" | "error";

interface ResumeUploadProps {
  onParsed?: (resume: ParsedResume | null) => void;
}

function ResumeUpload({ onParsed }: ResumeUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [extractedText, setExtractedText] = useState<string>("");
  const [characterCount, setCharacterCount] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const [parseState, setParseState] = useState<ParseState>("idle");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [parseErrorMessage, setParseErrorMessage] = useState<string>("");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setState("idle");
    setErrorMessage("");
    setParseState("idle");
    setParsedResume(null);
    setParseErrorMessage("");
    onParsed?.(null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    setState("loading");
    setErrorMessage("");
    setParseState("idle");
    setParsedResume(null);
    setParseErrorMessage("");
    onParsed?.(null);

    try {
      const result = await uploadResume(selectedFile);
      setExtractedText(result.extracted_text);
      setCharacterCount(result.character_count);
      setState("success");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Upload failed.");
      setState("error");
    }
  }

  async function handleParse() {
    setParseState("loading");
    setParseErrorMessage("");
    onParsed?.(null);

    try {
      const result = await parseResume(extractedText);
      setParsedResume(result);
      setParseState("success");
      onParsed?.(result);
    } catch (error) {
      setParseErrorMessage(error instanceof Error ? error.message : "Parsing failed.");
      setParseState("error");
    }
  }

  return (
    <section>
      <h2>Upload Resume</h2>
      <input type="file" accept="application/pdf" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={!selectedFile || state === "loading"}>
        {state === "loading" ? "Uploading..." : "Upload"}
      </button>

      {state === "error" && <p role="alert">Error: {errorMessage}</p>}

      {state === "success" && (
        <div>
          <p>Extracted {characterCount} characters.</p>
          <textarea readOnly value={extractedText} rows={20} style={{ width: "100%" }} />

          <div>
            <button onClick={handleParse} disabled={parseState === "loading"}>
              {parseState === "loading" ? "Parsing..." : "Parse Resume"}
            </button>
          </div>

          {parseState === "error" && <p role="alert">Error: {parseErrorMessage}</p>}

          {parseState === "success" && parsedResume && <ParsedResumeView data={parsedResume} />}
        </div>
      )}
    </section>
  );
}

export default ResumeUpload;
