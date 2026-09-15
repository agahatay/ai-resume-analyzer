export interface ResumeUploadResponse {
  filename: string;
  extracted_text: string;
  character_count: number;
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
}
