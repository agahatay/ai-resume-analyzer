import { apiPostJson } from "./api";
import type { ParsedJobDescription } from "../types/jobDescription";

// jobDescriptionId links this parse to a JobDescription row already
// created by a prior call, so the backend replaces that record's
// requirements instead of creating a new row. Omitted (or null) for a
// first-time parse.
export function parseJobDescription(
  text: string,
  jobDescriptionId?: string | null,
): Promise<ParsedJobDescription> {
  return apiPostJson<ParsedJobDescription>("/api/job-description/parse", {
    text,
    ...(jobDescriptionId ? { job_description_id: jobDescriptionId } : {}),
  });
}
