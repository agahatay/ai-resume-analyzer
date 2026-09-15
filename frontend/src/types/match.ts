export interface EducationMatchResult {
  status: "matched" | "partial" | "not_matched" | "not_specified";
  details: string;
}

export interface ExperienceMatchResult {
  status: "matched" | "partial" | "not_matched" | "unknown" | "not_specified";
  details: string;
  required_years: number | null;
  resume_years: number | null;
}

export interface CertificationMatchResult {
  matched: string[];
  missing: string[];
}

export interface LanguageMatchResult {
  matched: string[];
  missing: string[];
}

export interface ResumeMatchResponse {
  overall_match_score: number;
  matched_skills: string[];
  missing_required_skills: string[];
  matched_preferred_skills: string[];
  missing_preferred_skills: string[];
  education_match: EducationMatchResult;
  experience_match: ExperienceMatchResult;
  certification_match: CertificationMatchResult;
  language_match: LanguageMatchResult;
  summary: string;
}
