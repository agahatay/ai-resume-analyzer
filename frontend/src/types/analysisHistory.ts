import type { SemanticMatchItem } from "./match";
import type { ParsedResume } from "./resume";
import type { ParsedJobDescription } from "./jobDescription";

export interface AnalysisListItem {
  analysis_id: string;
  resume_id: string;
  job_description_id: string;
  deterministic_score: number;
  semantic_score: number;
  combined_score: number;
  created_at: string;
}

export interface AnalysisListResponse {
  items: AnalysisListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface AnalysisRecommendations {
  missing_required_skills: string[];
  missing_preferred_skills: string[];
  missing_certifications: string[];
  missing_languages: string[];
}

// Phase 11: what GET /api/analyses/{analysis_id} returns - everything
// persisted for one historical analysis, reconstructed from the database
// only (the backend never reruns the matcher for this endpoint).
export interface AnalysisDetailResponse {
  analysis_id: string;
  resume_id: string;
  job_description_id: string;
  created_at: string;
  deterministic_score: number;
  semantic_score: number;
  combined_score: number;
  combined_score_formula: string;
  semantic_matches: SemanticMatchItem[];
  semantic_model_name: string;
  semantic_similarity_threshold: number;
  summary: string;
  recommendations: AnalysisRecommendations;
  resume: ParsedResume;
  job_description: ParsedJobDescription;
}
