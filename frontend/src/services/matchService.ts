import { apiPostJson } from "./api";
import type { ParsedResume } from "../types/resume";
import type { ParsedJobDescription } from "../types/jobDescription";
import type { ResumeMatchResponse } from "../types/match";

export function matchResume(
  resume: ParsedResume,
  jobDescription: ParsedJobDescription,
): Promise<ResumeMatchResponse> {
  return apiPostJson<ResumeMatchResponse>("/api/resume/match", {
    resume,
    job_description: jobDescription,
  });
}
