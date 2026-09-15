import { apiPostForm, apiPostJson } from "./api";
import type { ParsedResume, ResumeUploadResponse } from "../types/resume";

export function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPostForm<ResumeUploadResponse>("/api/resume/upload", formData);
}

export function parseResume(text: string): Promise<ParsedResume> {
  return apiPostJson<ParsedResume>("/api/resume/parse", { text });
}
