export interface ParsedJobDescription {
  job_title: string | null;
  required_skills: string[];
  preferred_skills: string[];
  education_requirements: string[];
  experience_requirements: string[];
  certifications: string[];
  languages: string[];
}
