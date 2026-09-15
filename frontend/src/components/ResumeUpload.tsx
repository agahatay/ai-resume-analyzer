import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { parseResume, uploadResume } from "../services/resumeService";
import type { ParsedResume } from "../types/resume";
import ParsedResumeView from "./ParsedResumeView";
import Card from "./ui/Card";
import Spinner from "./ui/Spinner";
import ErrorBanner from "./ui/ErrorBanner";
import "./ui/ui.css";

type UploadState = "idle" | "loading" | "success" | "error";
type ParseState = "idle" | "loading" | "success" | "error";

interface ResumeUploadProps {
  onParsed?: (resume: ParsedResume | null) => void;
}

function isPdfFile(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ResumeUpload({ onParsed }: ResumeUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileValidationError, setFileValidationError] = useState<string>("");
  const [isDragActive, setIsDragActive] = useState(false);
  const [state, setState] = useState<UploadState>("idle");
  const [extractedText, setExtractedText] = useState<string>("");
  const [characterCount, setCharacterCount] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const [parseState, setParseState] = useState<ParseState>("idle");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);
  const [parseErrorMessage, setParseErrorMessage] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetResultState() {
    setState("idle");
    setErrorMessage("");
    setParseState("idle");
    setParsedResume(null);
    setParseErrorMessage("");
    onParsed?.(null);
  }

  function applyFile(file: File | null) {
    resetResultState();
    if (!file) {
      setSelectedFile(null);
      setFileValidationError("");
      return;
    }
    if (!isPdfFile(file)) {
      setSelectedFile(null);
      setFileValidationError(`"${file.name}" is not a PDF file. Please select a .pdf file.`);
      return;
    }
    setSelectedFile(file);
    setFileValidationError("");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    applyFile(event.target.files?.[0] ?? null);
  }

  function handleRemoveFile() {
    applyFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragActive(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragActive(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragActive(false);
    applyFile(event.dataTransfer.files?.[0] ?? null);
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
    if (parseState === "loading") {
      return;
    }

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
    <Card title="1. Upload Resume" titleLevel="h2">
      <label
        htmlFor="resume-file-input"
        className="ui-dropzone"
        data-active={isDragActive || undefined}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          id="resume-file-input"
          ref={fileInputRef}
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          className="ui-visually-hidden"
        />
        <span className="ui-dropzone-text">
          <strong>Click to choose a PDF</strong> or drag and drop it here
        </span>
        <span className="ui-field-hint">PDF only, up to 5 MB</span>
      </label>

      {fileValidationError && <ErrorBanner message={fileValidationError} />}

      {selectedFile && (
        <div className="ui-selected-file">
          <span>
            📄 {selectedFile.name} <span className="ui-field-hint">({formatFileSize(selectedFile.size)})</span>
          </span>
          <button type="button" className="ui-button ui-button-ghost" onClick={handleRemoveFile}>
            Remove
          </button>
        </div>
      )}

      <div style={{ marginTop: "0.75rem" }}>
        <button
          className="ui-button ui-button-primary"
          onClick={handleUpload}
          disabled={!selectedFile || state === "loading"}
        >
          {state === "loading" ? <Spinner label="Uploading..." /> : "Upload"}
        </button>
      </div>

      {state === "error" && <ErrorBanner message={errorMessage} />}

      {state === "success" && (
        <div style={{ marginTop: "1rem" }}>
          <p className="ui-field-hint">Extracted {characterCount} characters from the PDF.</p>
          <textarea
            readOnly
            value={extractedText}
            rows={10}
            style={{ width: "100%" }}
            aria-label="Extracted resume text"
          />

          <div style={{ marginTop: "0.75rem" }}>
            <button
              className="ui-button ui-button-primary"
              onClick={handleParse}
              disabled={parseState === "loading"}
            >
              {parseState === "loading" ? <Spinner label="Parsing..." /> : "2. Parse Resume"}
            </button>
          </div>

          {parseState === "error" && <ErrorBanner message={parseErrorMessage} />}

          {parseState === "success" && parsedResume && (
            <div style={{ marginTop: "1rem" }}>
              <ParsedResumeView data={parsedResume} />
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default ResumeUpload;
