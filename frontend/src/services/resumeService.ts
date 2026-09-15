import { apiPostForm } from "./api";
import type { ResumeUploadResponse } from "../types/resume";

export function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiPostForm<ResumeUploadResponse>("/api/resume/upload", formData);
}
