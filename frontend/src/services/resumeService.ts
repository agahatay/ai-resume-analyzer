import { apiPostForm, apiPostJson } from "./api";
import type { ParsedResume, ResumeUploadResponse } from "../types/resume";

export function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPostForm<ResumeUploadResponse>("/api/resume/upload", formData);
}

// resumeId links this parse to a Resume row already created by a prior
// uploadResume() call, so the backend updates that same record instead of
// creating a new one. Omitted (or null) when there is no prior upload.
export function parseResume(text: string, resumeId?: string | null): Promise<ParsedResume> {
  return apiPostJson<ParsedResume>("/api/resume/parse", {
    text,
    ...(resumeId ? { resume_id: resumeId } : {}),
  });
}
