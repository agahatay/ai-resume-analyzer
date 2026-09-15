import { apiPostJson } from "./api";
import type { ParsedJobDescription } from "../types/jobDescription";

export function parseJobDescription(text: string): Promise<ParsedJobDescription> {
  return apiPostJson<ParsedJobDescription>("/api/job-description/parse", { text });
}
