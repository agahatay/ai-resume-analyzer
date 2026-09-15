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

export interface DeterministicMatchSummary {
  score: number;
  matched_skills: string[];
  missing_required_skills: string[];
  matched_preferred_skills: string[];
  missing_preferred_skills: string[];
  education_match: EducationMatchResult;
  experience_match: ExperienceMatchResult;
  certification_match: CertificationMatchResult;
  language_match: LanguageMatchResult;
}

export interface SemanticMatchItem {
  category: "skills" | "experience" | "projects" | "education" | "certifications";
  requirement: string;
  matched_resume_text: string | null;
  similarity: number;
  matched: boolean;
}

export interface SemanticMatchResult {
  semantic_score: number;
  semantic_matches: SemanticMatchItem[];
  model_name: string;
  similarity_threshold: number;
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
  deterministic_match: DeterministicMatchSummary;
  semantic_match: SemanticMatchResult;
  combined_match_score: number;
  combined_score_formula: string;
}
