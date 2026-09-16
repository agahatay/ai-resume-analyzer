export interface ParsedJobDescription {
  job_title: string | null;
  required_skills: string[];
  preferred_skills: string[];
  education_requirements: string[];
  experience_requirements: string[];
  certifications: string[];
  languages: string[];
  // Set once this job description has been persisted (see
  // POST /api/job-description/parse). Sent back on /api/resume/match so a
  // successful match can be linked to this same database record.
  job_description_id?: string | null;
}
