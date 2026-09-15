import { useState } from "react";
import type { ChangeEvent } from "react";
import { uploadResume } from "../services/resumeService";

type UploadState = "idle" | "loading" | "success" | "error";

function ResumeUpload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [extractedText, setExtractedText] = useState<string>("");
  const [characterCount, setCharacterCount] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string>("");

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setState("idle");
    setErrorMessage("");
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    setState("loading");
    setErrorMessage("");

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
        </div>
      )}
    </section>
  );
}

export default ResumeUpload;
