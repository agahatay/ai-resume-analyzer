export interface ResumeUploadResponse {
  filename: string;
  extracted_text: string;
  character_count: number;
  resume_id: string;
}

export interface EducationEntry {
  institution: string | null;
  degree: string | null;
  dates: string | null;
  raw_text: string;
}

export interface ExperienceEntry {
  title: string | null;
  organization: string | null;
  dates: string | null;
  raw_text: string;
}

export interface ProjectEntry {
  name: string | null;
  description: string | null;
  raw_text: string;
}

export interface ParsedResume {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  skills: string[];
  education: EducationEntry[];
  work_experience: ExperienceEntry[];
  projects: ProjectEntry[];
  certifications: string[];
  languages: string[];
  // Set once this resume has been persisted (see POST /api/resume/upload
  // and POST /api/resume/parse). Sent back on /api/resume/match so a
  // successful match can be linked to this same database record.
  resume_id?: string | null;
}
